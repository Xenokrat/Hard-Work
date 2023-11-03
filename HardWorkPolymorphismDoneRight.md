# Hard Work - Пишем правильный полиморфный код

## Пример 1

В классе, передающем параметры для выболнения запросов к БД есть вспомогательная функция `get_daterange` которая возвращает список с днями в `datetime` в промежутке между указанными датами.

**Было**:

```python
@staticmethod
def get_daterange(date1: datetime, date2: datetime) -> list[datetime]:
    return [
        date1 + timedelta(days=x)
        for x in range((date2 - date1).days + 1)
    ]
```

Теоретически, может понадобиться диапазон с любым шагом, не только в днях.

**Стало**:

Попробуем преобразовать функцию выше таким образом, чтобы можно было получать диапазон с любым шагом

```python
@staticmethod
def get_daterange(date1: datetime, date2: datetime, step: str) -> list[datetime]:
    # проверим, что такой шаг времени возможет
    assert hasattr(timedelta, step), "No such step is possible with timedelta"
    return [
        date1 + timedelta(**{step: x})
        for x in range(getattr((date2 - date1), step) + 1)
    ]
```

Получаем функцию, которая дает диапазон с любым заданным шагом

## Пример 2

Что если взять предыдущий пример, и пойти дальше?
В запросах могут использоваться помимо временных значений еще ряды целых чисел или чисел с плавающей точкой (последнее наверное редко).
Возможно ли сделать данную функцию более универсальной?

**Было**:

```python
@staticmethod
def get_daterange(date1: datetime, date2: datetime, step: str) -> list[datetime]:
    # проверим, что такой шаг времени возможет
    assert hasattr(timedelta, step), "No such step is possible with timedelta"
    return [
        date1 + timedelta(**{step: x})
        for x in range(getattr((date2 - date1), step) + 1)
    ]
```

**Стало**:

Добавим переменную типов.
Увы, диапазон дат требует использования timedelta, более красивого варианта, чем проверка на тип не могу придумать.

```python
from typing import TypeVar
from datetime import datetime, timedelta
from math import ceil


T = TypeVar('T')

def get_value_range(start: T, end: T, step: str | int | float) -> list[T]:
    # Если дата
    if all([
        isinstance(start, datetime),
        isinstance(end, datetime),
        isinstance(step, str),
    ]):
        assert hasattr(timedelta, step), "No such step is possible with timedelta"
        return [
            start + timedelta(**{step: x})
            for x in range(getattr((end - start), step) + 1)
        ]
    # Int / Float / Other
    try:
        return [
            start + step * x
            for x in range(ceil((end - start) / step))
        ]
    except Exception as e:
        log.error(e)

```

## Пример 3

Имеем довольно конкретную функцию для отправки электронного письма под конкретного клиента, в которой внутри указывается эндпоинт и структура данных, которую нужно отправить.
Таким образом, эта функция не очень универсальная

**Было**:

```python
async def sidetask_send_email_to_client(params: ParametersDataclass) -> None:
    dt = params.date
    email_list = params.client_email_list
    url = 'https://endpoint/path'
    data = {
        "message_header": "data",
        "message": f"Сформированы данные за {dt}",
        "emails": email_list,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            response_data = await response.json()
    assert response_data["answer"]
    log.info("EMAIL: sent emails to Client1")
```

Попробуем приспособить данную функцию для более общего случая:

**Стало**:

```python
@dataclass
class EndpointStruct:
    url: str
    _header: str
    _message: str
    _email_list: list[str]

    def format_message(self, info_to_send):
        return self._message.format(*info_to_send)

    def get_json_data(self, info_to_send):
        return {
            "header": self._header,
            "message": self.format_message(info_to_send),
            "email_list": self._email_list,
        }


async def sidetask_send_email_to_client(
    email_info: list[str],
    endpoint: EndpointStruct,
    params: ParametersDataclass,
    response_message: str = "answer",
) -> None:

    # Получаем инф. для отправки письма из параметров
    info_to_send = [getattr(params, inf) for inf in email_info]

    # Струкрута данных для отправки
    url = endpoint.url
    data = endopoint.get_json_data(info_to_send)

    # Отправляем письмо
    client = params.current_client
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            response_data = await response.json()
    assert response_data[repsonse_message]
    log.info(f"EMAIL: sent emails to {client}")
```

Таким образом за струкруту отправляемых данных теперь отвечает внешний класс, а функция поддерживает больше способов взаимодействия с пользователем.

## Пример 4

Функция для рекурсивного поиска файла по названию.

**Было**:
В целом имеем 2 потенциальные проблемы с этой функцией:

- В ней внутри конкретно указано, что она для `.sql` файлов
- Корневая папка также указана внутри функции

```python
def find_file_by_name(file_name: str) -> str:
    file_name += ".sql"
    root_dir = pathlib.Path(__file__).absolute().parent.parent
    for file_path in root_dir.glob("**/*"):
        if file_path.name == file_name:
            return str(file_path)
    raise Exception(f"No such file {file_name} in {root_dir}")
```

**Стало**:

Попробуем сделать функцию более универсальной, чтобы ее можно было использовать для поиска пути файлов нужного формата из любого места внутри проекта:

```python
from pathlib import Path


def find_file_by_name(
    file_name: str,
    file_ext: str,
    root_dir: Path,
) -> str:
    full_file_name = f"{file_name}.{file_ext}"
    for file_path in root_dir.glob("**/*"):
        if file_path.name == full_file_name:
            return str(file_path)
    raise Exception(f"No such file {file_name} in {str(root_dir)}")

... 
# Вызов функции
root_dir = Path(__file__).absolute().parent

find_file_by_name('
    "report_query",
    "sql",
    root_dir
)
```

## Пример 5

Имеем функцию для получения данных о состоянии парсинга информации из БД и отправки в мессенджер.

**Было**
Такие функции, если их немного, можно написать быстро, если сделать их очень конкретынми, под каждый выделенный случай:

```python
def get_raw_data() -> str:
    current_time = datetime.utcnow() + timedelta(hours=3)  # to Moscow
    alert_text = "\n=========*RAW DATA*=========\n"
    alert_text += "*ALERT*: The database time is: "
    alert_text += f"_{current_time.strftime('%d.%m %H:%M')}_\n"
    alert_text += "More than an hour without updates:\n"
    text_is_changed = False
    raw_data_query = """
        SELECT
            rdm.darkstore_platform as app,
            rdm.last_timestamp AS raw_last_timestamp
        FROM raw_data_monitoring rdm
    """
    try:
        raw_data_res = db_client.execute(raw_data_query)
    except ServerException as e:
        log.error(f"raw data exception {e}")

    platform_set = get_prod_default_apps(ttl_hash=get_ttl_hash())
    for row in raw_data_res:
        platform, db_time = row

        if platform not in platform_set:
            alert_text += f" - *{platform}*, NOT IN DATABASE!\n"
            text_is_changed = True
            
        time_delta = abs((current_time - db_time).total_seconds())
        if time_delta > ALERT_PERIOD_SECONDS:
            alert_text += f" - *{platform}*, last update "
            alert_text += f"_{db_time.strftime('%d.%m %H:%M')}_\n"
            text_is_changed = True

    return alert_text if text_is_changed else ""
```

Но с добавлением новых видов отчетности, когда их уже значительно больше одного, имеет смысл выделить общий принцип, чтобы сделать функцию более полиморфной.

**Стало**
Выделим следующие действия, которые необходимо выполнить функции:

- SQL запрос к БД
- Само обращение к БД
- Обработка инф для вывода сообщения
- Заголовок для выводимого сообщения

```python
def get_raw_data(raw_data_res) -> str:
    platform_set = get_prod_default_apps(ttl_hash=get_ttl_hash())
    alert_text = ""
    for row in raw_data_res:
        platform, db_time = row

        if platform not in platform_set:
            alert_text += f" - *{platform}*, NOT IN DATABASE!\n"
            
        time_delta = abs((current_time - db_time).total_seconds())
        if time_delta > ALERT_PERIOD_SECONDS:
            alert_text += f" - *{platform}*, last update "
            alert_text += f"_{db_time.strftime('%d.%m %H:%M')}_\n"
        return alert_text

   
def get_any_data(
    header: str,
    query: str,
    db_client: DB_client,
    data_formatter: Callable,
) -> str:
    current_time = datetime.utcnow() + timedelta(hours=3)  # to Moscow
    try:
        query_res = db_client.execute(query): 
    except ServerException as e:
        log.error(f"raw data exception {e}")

    alert_text = data_formatter(query_res)
    if alert_text:
        alert_text = f"""
            =========*{header}*=========
            *ALERT*: The database time is: _{current_time.strftime('%d.%m %H:%M')}_
         """ + alert_text
    return alert_text

...
# Пример вызова
get_any_data("RAW DATA", query=query, db_client=postgresql_client, data=formatter=get_raw_data)
```

Будем использовать отдельную функцию для форматирования данных в сообщении.
Остальные параметры передаем через атрибуты функции.

## Выводы

Во время работы над этим уроком я понял, что стремление к более полиморфному коду приводит к схожему результату,
что и все методы, которые созданые для получения слабо-связанного кода.
Ведь как раз использование интерфейсов / абстрактных классов является одним из основных способов сделать код менее связанным и конктерным,
и одновременно с этим оно же является способом сделать код более полиморфным.
Также попытки написания более полиморфных функций приводят к тому, что ты пытаешься вместо просто конкретной "детали" кода ухватить како-либо общий принцип.
Естественно, выделение такого общего принципа делает функцию гораздо более переиспользуемой, причем среди множества проектов.
Иногда это также приводит к мысли, что для конкретного случая наверняка уже есть готовая и оптимизированная библиотека, и лучше использовать ее :).
Но иногда попытки сделать функцию более полиморфной также приводят к довольно некрасивому и хуже-читемому коду,
например на `Python` часто уже приходится вводить проверки вроде `isinstance` (хотя во многих таких случаях наверняка есть более элегантное решение).
Тут, как и было отмечено в материале урока, есть две противоположные тенденции -- делая функцию более мономорфной мы также делаем ее более читабельной и, вероятно, более понятной для коллег.
С другой стороны, действительно, выделив общий принцип, который должен осуществять конкретный код, уже сложнее допустить ошибку в деталях реализации.
