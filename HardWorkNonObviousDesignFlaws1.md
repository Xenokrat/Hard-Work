## Пример 1

Пример до:
	Имеется программа, которая читает .yaml конфигурационный файл и затем выполняет
	команды.
	После прочтения файла, в классе который содержит прочитанные настройки может содержаться некорректная информация (например при опечатке). 
	Ошибка отлавливается дальше в классе-фабрике при помощи `try-except`.
	Структура конфига никак при этом не проверяется.
	
```python
class ConfigParserYAML:
    def __init__(self, config_file: str = "config.yaml") -> None:
        config_file_path = os.path.abspath(config_file)
        log.info(config_file_path)
        try:
            with open(config_file_path, "r") as configfile:
                parsed_yaml = yaml.safe_load(configfile)
        except FileNotFoundError:
            log.error("Config file not found")
            sys.exit(-1)

        self.config = parsed_yaml

class TaskFabric:
    def __init__(self, tasks: List[str]) -> None:
        task_match = {
            "task1": Task1,
            "task2": Task2,
			...
        }
		# Защита здесь
		try:
	        self.task_obj = [
	            task_match[task]() for task in tasks  # type: ignore
	        ]
		except KeyError:
			log.error("Malformed task literal")
```

Исправляем:
Добавим Enum класс для того, чтобы все задачи принадлежали только к этому классу.
Вероятно, чтобы ошибка не "висела" в процессе от парсинга до попытки создания объектов Задач. Можно использовать библиотеку `Pydantic` которая позволяет верифицировать полученные json-данные.

Пример после:
```python
from enum import Enum
from pydantic import BaseModel 

# Новые классы для верификации структуры конфига.
class TaskEnum(str, Enum):
	task1 = 'task1'
	task2 = 'task2'

class TaskConfig(BaseModel): 
	stage: str
	tasks: list[TaskEnum]

class TasksConfig(BaseModel): 
	stages: list[TaskConfig]


class ConfigParserYAML:
    def __init__(self, config_file: str = "config.yaml") -> None:
        config_file_path = os.path.abspath(config_file)
        log.info(config_file_path)
        try:
            with open(config_file_path, "r") as configfile:
                parsed_yaml = yaml.safe_load(configfile)
        except FileNotFoundError:
            log.error("Config file not found")
            sys.exit(-1)
            
		# Изменение здесь
        self.config = TasksConfig(**data)

class TaskFabric:
    def __init__(self, tasks: List[str]) -> None:
        task_match = {
            "task1": Task1,
            "task2": Task2,
			...
        }
		# Более не нуждаемся в блоке try-except
		self.task_obj = [
			task_match[task]() for task in tasks  # type: ignore
		]
```
Выводы:
Внесенные изменения не позволяют попасть в программу некорректным json-данным на самом раннем этапе работы программы. Кроме того это избавляет нас от необходимости в дальнейших проверках корректности данных в коде.

## Пример 2

Пример до:
Имеется функция, возвращающая корректную строку для подключения в БД.
Отдельно проверяется, что значение порта представляет собой целое число.
Что плохо:
	- Проверка через if
	- Проверяется только то что db_port это число, но число может быть любым.
```python
def get_async_dsn(
    db_user: str = "default",
    db_pass: str = "",
    db_host: str = "localhost",
    db_port: int | str = 9000,
    db_name: str = "default",
) -> str:
	if not (ininstance(db_port, int) or db_port.isdigit()):
		raise Exception("Некорректный порт")
    return (
        f"clickhouse+asynch://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        f"?secure=True&verify=False"
    )
```

Исправляем:
На самом деле у БД Clickhouse в данном случае будет ограниченный набор пригодных портов. В этом случае достаточно проверить что аргумент принадлежит предустановленному множеству значений.

Пример после:
```python
def get_async_dsn(
    db_user: str = "default",
    db_pass: str = "",
    db_host: str = "localhost",
    db_port: int | str = 9000,
    db_name: str = "default",
) -> str:
	assert int(db_port) in {8443, 9000, 9440}, "Некорректный порт"
    return (
        f"clickhouse+asynch://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
        f"?secure=True&verify=False"
    )
```
Выводы:
Мы заменили проверку через `if` на `assert` и внесли дополнительно бОльшее ограничение, чтобы убедиться в корректности работы подключения к БД.

## Пример 3

Пример до:
Функция получает данные из БД, и проверяет ряд условий, и в зависимости от условий,
возвращает ответ или пустую строчку.
Для валидации полученных из БД данных имеем `try-except` блок внутри цикла, что возможно не идеально плюс дополнительная проверка типов с `isinstance`.
```python
def eval_data(self, data) -> str:
	current_time = datetime.utcnow()
	alert_text = self.alert_text
	text_is_changed = False

	for row in data:
		try:
			platform, db_time = row
		except Exception as e:
			log.error(e)
		if not (isinstance(platform, str) and (isinstance(db_time, datetime))):
			log.error("Wrong data from DB")
			return ""

		time_delta = abs((current_time - db_time).total_seconds())

		is_platform_not_in_list = platform not in self.platfrom_check_delay
		is_alert_triggered = time_delta > ALERT_PERIOD_SECONDS
		is_alert_triggered_not_delayed = (
			current_time > self.platfrom_check_delay[platform] and
			is_alert_triggered
		)
		if any([
			is_platform_not_in_list,
			is_alert_triggered_not_delayed,
		]):
			self.platfrom_check_delay[platform] = current_time + \
				timedelta(seconds=self.alert_delay)
			self.alert_delay *= ALERT_TIME_INCREASE_MULTIPLIER
			alert_text += f' - *{platform}*,' \
			              f'last update _{db_time.strftime("%d.%m %H:%M")}_\n'
			text_is_changed = True

	if text_is_changed == False: log.debug(f"{self.__class__.__name__} is fine")
	return alert_text if text_is_changed else ""
```

Исправляем:
И снова `Pydantic` может помочь с валидацией данных, получаемых из БД.
Так как данные состоят из списка строк, создадим 2 класса для репрезентации.
Провалидируем получаемые данные внутри метода. Затем без дополнительных проверок можно просто получить нужные значения внутри цикла.

Пример после:
```python
class DatabaseRecord(BaseModel): 
	platform: str 
	db_time: datetime 
	
class DatabaseData(BaseModel): 
	data: list[DatabaseRecord]

...

def eval_data(self, data) -> str:
	current_time = datetime.utcnow()
	alert_text = self.alert_text
	text_is_changed = False
	validated_data = DatabaseData(**date)

	# После изменения заметно "чище"
	for row in validated_data.data:
		platform = row.platform
		db_time  = row.db_time 

		time_delta = abs((current_time - db_time).total_seconds())

		is_platform_not_in_list = platform not in self.platfrom_check_delay
		is_alert_triggered = time_delta > ALERT_PERIOD_SECONDS
		is_alert_triggered_not_delayed = (
			current_time > self.platfrom_check_delay[platform] and
			is_alert_triggered
		)
		if any([
			is_platform_not_in_list,
			is_alert_triggered_not_delayed,
		]):
			self.platfrom_check_delay[platform] = current_time + \
				timedelta(seconds=self.alert_delay)
			self.alert_delay *= ALERT_TIME_INCREASE_MULTIPLIER
			alert_text += f' - *{platform}*,' \
			              f'last update _{db_time.strftime("%d.%m %H:%M")}_\n'
			text_is_changed = True

	if text_is_changed == False: log.debug(f"{self.__class__.__name__} is fine")
	return alert_text if text_is_changed else ""
```

Выводы:
`Pydantic` позволяет легко проводить валидацию данных сложной структуры и позволяет писать более элегантный код без дополнительных проверок, так как библиотека берет на себя валидацию типов данных.

## Пример 4
Пример до:
В примере кусочек метода, в котором из базы данных получается список стран по площадкам в приложении и сравнивается с установленным (хардкодом :)) заранее списком.
В целом, ситуация, при которой страны нет в БД, но она есть в `PLATFORMS_COUNTRIES` обрабатывается как раз данным методом далее.

Однако можно получить обратную ситуацию, при которой мы встретим какую-то "неожиданную" страну в БД, которой нет в предустановленном списке.
Кусочек кода ниже как раз при помощи цикла определяет такую ситуацию.
```python
currect_platform_coutries = defaultdict(set)
        for app, country in data:
            currect_platform_coutries[app].add(country)

for app in currect_platform_coutries:
	if app not in self.PLATFORMS_COUNTRIES:
		log.error(f"App {app} not in default platform list")
		raise Exception("Страна не присутствует в установленном списке")
```

Исправляем:
Вместо использования цикла + if + выведения логов и ошибки здесь можно обойтись предусловием, что сет стран из БД является подмножеством `PLATFORMS_COUNTRIES`.
В этом случае можно элегантно сократить код.

Пример после:
```python
assert currect_platform_coutries.issubset(PLATFORMS_COUNTRIES), \
	"Страна не присутствует в установленном списке"
```

Выводы:
Иногда `assert` позволяет относительно легко проводить проверку предусловий в `Python` вместо использования конструкций из `if-raise`

## Пример 5
Пример до:

Имеется метод для Django API, внутри которого проверяется доступ. Если пользователь - это суперпользователь, то доступ дается сразу. Если пользователь менеджер, то нужно проверить, обращается ли он к данным своего предприятия, или нет.
Проверка производится через серию условий `if`.
```python
@api_view(["GET"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def car_mileage_report(request, pk: int):
    if not (hasattr(request.user, "manager") or request.user.is_superuser):
        return Response({"detail": "Нет доступа"}, status=403)

    if (not request.user.is_superuser) and hasattr(request.user, "manager"):
        vehicle_enterpirse = Vehicle.objects.get(pk=pk).enterprise
        manager_enterprises = request.user.manager.enterprise.all()

        if vehicle_enterpirse not in manager_enterprises:
            return Response({"detail": "Нет доступа"}, status=403)

    car_mil_report_data = CarMileageReport.objects.get(pk=pk)

    serializer = CarMileageReportSerializer(car_mil_report_data)
    return Response(serializer.data)
```

Исправляем:
Попробуем вынести всю логику валидации доступа во внешнюю функцию.
Таким образом мы сможем использовать эту логику и в других функциях.

Пример после:
```python
def has_permission(self, request, view):
	if request.user.is_superuser:
		return True 
	if hasattr(request.user, "manager"):
		vehicle_enterprise = Vehicle.objects.get(pk=view.kwargs['pk']).enterprise
		manager_enterprises = request.user.manager.enterprise.all() 
		return vehicle_enterprise in manager_enterprises
	return False

@api_view(["GET"])
@authentication_classes([SessionAuthentication, BasicAuthentication])
@permission_classes([IsAuthenticated])
def car_mileage_report(request, pk: int):
	if not request.user.has_permission:
		return Response({"detail": "Нет доступа"}, status=403)    
	car_mil_report_data = CarMileageReport.objects.get(pk=pk)
    serializer = CarMileageReportSerializer(car_mil_report_data)
    return Response(serializer.data)
```

Выводы:
В целом да, я понимаю, что мы просто перенесли проверки в отдельную функцию, однако в целом это позволяет сделать логику API более компактной и пере использовать проверку авторизации в других участках программы.

## Выводы
В целом, как мне кажется, `Python` по дизайну как раз не очень `soundness` и дает очень много свободы в том, как писать код, любые ограничения выглядят довольно громоздко. По итогам, лучшие способы ограничить свободу использования питоновского кода, это введение большого количества `assertов` или использование внешних библиотек, таких как `Pydantic` или `Marshmallow`  для валидации данных.