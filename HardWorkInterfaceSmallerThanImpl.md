## Примеры призрачного состояния

### 1. Переменная определяет графический размер ячеек.
Пример с классом для GUI, внутри которого определяется размер ячейки.
Данная переменная не включена в конструктор класса, другие методы также никак не влияют на нее.
Однако переменная используется для определения размера отрисовки графического элемента.
```python
class TuringMachineGUI(QMainWindow):
    open_requested = pyqtSignal()

    def __init__(self, machine: TuringMachineApp) -> None:
        super().__init__()
        self.setWindowTitle("Turing Machine Array")
        self.setGeometry(100, 100, 800, 600)

        # Состояние внутри конструктора для ячейки не доступно "снаружи"
        # неочевидно, как им можно управлять
        self.cell_size = 150

        self.machine = machine
        self.worker = Worker(self.machine)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.create_ui()
        ...
```
Возможным решением будет включение ее в конструктор класса
(не очень оптимально, так как класс создается другим меню, где не предусмотрено определение размера ячейки)
или внесением методов, которые связаны с пользовательским UI, которые могут управлять этим параметром.

### 2. Маппинг для парсинга комманд указан внутри функции.
Имеется функция, которая читает значение таблицы (как строку), и возвращает кортеж значений комманды для симуляции.
Переменная `move_list` в данном случае определена внутри функции (не в сигнатуре функции и не используется как атрибут класса).
Данное место кода потенциально "хрупкое", так как уязвимо к внесению изменений в определение комманды.
```python
def __parse_command(self, command: str) -> tuple[str, int, int]:
    # Вероятно, проблемное место
    move_list = {"L": -1, "S": 0, "R": 1}
    raw_val, raw_move, raw_next = command.split(" ")
    val = self.tape[self.current_tape_cell] if raw_val == "N" else raw_val
    move = move_list[raw_move]
    next = int(raw_next[1:])
    return val, move, next
```
Возможные варианты исправления:
- Передача данного значения как аттрибута класса через `self.move_list`
- Передача в качестве параметра функции как `parse_command(self, command: str, move_list: dict[str, int])`

## Примеры сужения логики кода

### 1. Изменение размера ленты для отрисовки GUI Машины Тьюринга
Для примера GUI фактический размер ленты был ограничен 30 ячейками, и не предполагалось, что это поле можно будет изменять.
Однако по правильному было бы расширять ленту каждый раз когда это необходимо, так как по логике эта лента должна быть бесконечной.
Однако бесконечное расширение размер может привести к неприятным последствиям, поэтому верхнюю планку также желательно ограничить.
```python
@dataclass
class TuringMachineApp:
	...
    table_data: list[list[str]] = field(default_factory=list)
    tape: list[str] = field(default_factory=lambda: ["_"] * 30)
	...
```

Лучшее что придумал для решения этой проблемы, добавить сеттер для значения, через который ограничивается 
```python
@dataclass
class TuringMachineApp:
	...
    table_data: list[list[str]] = field(default_factory=list)
    __tape: list[str] = field(default_factory=lambda: ["_"] * 30)

	@property
	def tape(self):
		return self.__tape

	@tape.setter
	def tape(self, value):
		if len(value) > 999:
			raise Exception("Tape is too long")
		self.__table = value

	...
	def check_tape_expantion(self) -> None:
        if self.current_tape_cell + 1 >= len(self.tape):
            self.tape = self.tape + ["_"] * 10
        elif self.current_tape_cell <= 0:
            self.tape = ["_"] * 10 + self.tape
            self.current_tape_cell += 10
	...
```

### 2. Метод, который записывает значения отчета в Excel файл
Метод записывает значения  отчета.
В реализации отчета указано, что должно записывать 600000 значений.
Однако теоретически на лист Excel можно записать от 1 до 1 млн значений (лучше ограничить верхнюю планку, для производительности до 850 тыс.
В примере ниже также переменные `start` и `end` являются примером призрачного состояния.
```python
def prepare_xlsx_reports(self, platform, platform_df):
	"""
	Метод формирует отчеты в формате xlsx 
	и записывает их в self.writers_xlsx
	"""
	platform_df = platform_df.reset_index()
	# Количество строк в platform_df
	lines_df = platform_df.shape[0]
	log.debug(
		f'Количество строк датафрейма - {lines_df} по платформе {platform}'
	)
	start, end = 0, 600_000
	...
```

Исправив это, передав значения как параметры функции, убедимся соответствием с помощью `assert`
```python
def prepare_xlsx_reports(self, platform, platform_df, 
						 start_row: int = 0, end_row: int) -> None:
	"""
	Метод формирует отчеты в формате xlsx 
	и записывает их в self.writers_xlsx
	"""
	assert end_row > 0 and end_row < 850_000, "Некорректное значение строк"
	platform_df = platform_df.reset_index()
	# Количество строк в platform_df
	lines_df = platform_df.shape[0]
	log.debug(
		f'Количество строк датафрейма - {lines_df} по платформе {platform}'
	)
	start, end = 0, 600_000
	...
```

### 3. Передача в метод установленного списка площадок
```python
def get_data_from_db(self):
	platforms = (
		self.config['platforms'].copy()
		if self.config['platforms'] else None
	)
	platform_deliveries = (
		self.config['platform_deliveries'].copy() 
		if self.config['platform_deliveries'] else None
	)
	# Берем данные по иностранным площадкам
	if self.config['language'] == 'en':
		en_platforms = [
			'App1', 'App2', 'App3', 'App4', 'App5', 'App6'
		]
```

Импортируем константу, которая содержит список всех площадок.
Должно проверяться, что используемые в реализации площадки являются частью глобального списка площадок.

Также в свою очередь будем передавать площадки по параметру метода
```python
from config import APP_LIST
...
def get_data_from_db(self, 
					 en_platform_list: list[str],
					 ru_platform_list: list[str]):
	...
	# Берем данные по иностранным площадкам
	if self.config['language'] == 'en':
		platforms = en_platform_list.copy()
	assert set(platforms).issubset(set(APP_LIST))
```

## Примеры  когда интерфейс явно не должен быть проще реализации

### 1. Значение текущего состояния по таблице переходов
Также в машине Тьюринга имеем атрибут, отвечающий за состояние в таблицы переходов.
- `state_value: int` - используем как общее количество состояний в таблице переходов.
- `current_table_state: int = 1` - отвечает за указание на текущее состояние в данный момент.
В базовой версии в интерфейсе нет ограничений на то, что `current_table_state` может быть присвоено отрицательное значение или больше чем `state_value`.
```python
@dataclass
class TuringMachineApp:
    state_value: int
    current_table_state: int = 1

	# в методах потенциально может быть присвоено, 
	# например, отрицательное значение
	 def update_machine_state(
		 self, val: str, move: int, next: int) -> None:
			...
	        self.current_table_state = next
```
Решение также может быть представлено при помощи сеттеров.
Заодно, можно подумать о том, что `state_value` также сделать недоступным для изменения.
```python
@dataclass
class TuringMachineApp:
    __state_value: int
    __current_table_state: int = 1

	@property
	def current_table_state(self):
		return self.__current_table_state

	@current_table_state.setter
	def current_table_state(self, value):
		if value < 0 or value > self.state_value:
			raise Exception("Incorrect Table state")
		self.__table = value
```

### 2. Код в веб-приложениях (FastAPI) 
ИИ подсказывает этот пример :).
В большом количестве реализации эндпоинтов, этот эндпоинт состоит из реализации бизнес-логики, и той части кода, которая реализует всю остальную веб-логику.
```python
@router.post("/products/", response_model=schemas.FilterSKUs)
def post_filters_products(
        filters_list: schemas.FiltersBase,
        db: Session = Depends(deps.get_db),
) -> Any:
    items = crud.setup_filter.get_query(db=db, field="product_name")
    items = apply_filters(items, filters_list)
    items = [
        i[0] for i in items.limit(filters_list.limit).offset(filters_list.offset).all()
    ]
    return {"skus": items}
```
В таком случае, значительная часть именно интерфейса этого эндпоинта предоставляется фреймворком (в скрытом от программиста виде), в то время как реализация бизнес-логики может быть очень простой.

### 3. Атрибуты в классе для поиска названий Брендов внутри продукта
Класс сохраняет внутри атрибутов найденные значения, однако на базовом уровне нет подтверждения, что добавленные значения соответствуют хотя бы строковым значениям 
```python
class FindBrand:
    def __init__(self):
        self.products = []
        self.products_brand_list = []
```
В примере выше в `self.products = []` должны заноситься строковые значения.
В `self.products_brand_list = []` должны заноситься только экземпляры класса `Brand`

В питоне не так много способов форсировать добавление определенного типа в лист.
Самый прямолинейный способ, расширить интерфейс добавлением методов.
(Добавим также аннотации типов).
```python
class FindBrand:
    def __init__(self):
        self.__products: List[str] = []
        self.__products_brand_list: List[Brand] = []

	def add_to_products(self):
		if isinstance(value, str): 
			self.__products.append(value) 
		else:
			raise Exception("Wrong type for products list!")

	def add_to_brand_list(self):
		if isinstance(value, Brand): 
			self.__products_brand_list.append(value) 
		else:
			raise Exception("Wrong type for brand list!")
```

## Общие выводы
Как я теперь понимаю лучше, задание интерфейсов во много позволяет определить поведение программы в целом, ее границы и того, что вообще можно ждать от реализации. Перенос понимания на уровень интерфейса вместо реализации (как например удаление "призрачного состояния") сильно облегчает впоследствии размышление о программе. 
В то же время задание определенного корректного диапазона значений при поведении программы впоследствии облегчает ее модификаци.
Надо отметить, в целом, испытываю некоторые трудности при задании четко установленного интерфейса в таком языке с динамической типизацией, как Python :), приходится ограничиваться `assert`, `isinstance` и геттерами и сеттерами (которые, как мне кажется, выглядят довольно неловко).
Вероятно, поэтому о Python говорят часто как о языке для быстрого прототипирования, а впоследствии заменяют код языком со статической типизацией.