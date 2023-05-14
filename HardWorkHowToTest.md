# Hard Work | How to write tests



## Мой небольшой проект -- Перенос из Clickhouse отчетов в Postgresql напрямую


### Общий чертеж дизайна проекта.
<details>
  <summary><b>Схема проекта под катом</b></summary>
### Схема

1. Создаем таблицу на движке Postgresql в Clickhouse (см. документацию clickhouse_sqlalchemy) 
2. Создаем запрос INSERT INTO с таблицей из 1.
3. Выполняем запрос 2.
4. Удаляем таблицу 1.


### Зависимости

- python3.11
- clickhouse_sqlalchemy
- psycopg2
- pytest


### Классы и функции

- Module: tmp_table_manager.py
- Создание и удаление таблиц (п1, п4)
```python
class TmpTableManager:
    def __init__(self, query_builder: TableQueryBuilder, engine_url: str) -> None:
        self.query_builder = query_builder
        self.engine = create_engine(engine_url)
        self.metadata = MetaData(bind=self.engine)

    def create_tmp_table(self) -> bool:
        pass

    def delete_tmp_table(self) -> bool:
        pass
```
- Создание SQLAlchemy таблицы из полученных параметров
- Module: table_query_builder.py
```python
@dataclass
class TableQueryBuilder(ABC):
    schema: str
    table_name: str
    fields: List[Dict[str, Any]] = [ # TODO: TypeDict?
        {
            "name": "day",
            "type": types.DateTime,
            "is_nullable": False,
        },
    ]

    @abstractmethod
    def build_table_query(self) -> ???:
            pass

@dataclass
class ClickhouseToPostgresEngine(TableQueryBuilder):
    postgres_db_host: str,
    postgres_db_port: str
    postgres_db_name: str
    postgres_db_user: str
    postgres_db_password: str,
    postgres_db_schema: str
    postgres_db_table: str

def build_table_query(self) -> ???:
    pass
```

- Module: insert_query_builder.py
- Из полученного config создает запрос
```python
class InsertQueryBuilder:

    # TODO: TypeDict для конфига
    def __init__(self, config) -> None:
        self.config = config

    def build_insert_query(self) -> Insert:
        pass
```
- Module: main.py
- Основной модуль
```python
class InsertQueryBuilder:

    # TODO: TypeDict для конфига
    def __init__(self, config, insert_query) -> None:
        self.config = config
        self.insert_query = insert_query

    def build_insert_query(self) -> Insert:
        pass
```
</details>

## Первая попытка

### 1. Этап разработки


Возьмем класс TmpTableManager, попробуем реализовать его.
Начнем с тестов.

1.1 Добавим класс пока без реализации.
```python
class TmpTableManager:
    """
     Назначение класса -- создание и удаление временных таблиц в БД для передачи данных.
     Принимает экземпляр класса TableQueryBuilder, который создержит созданную схему временной таблицы.
    """
    # TODO: реализация как контестного менеджера, чтобы при возникновении ошибок всегда срабатывало удаление таблицы.
    
    def __init__(self, query_builder: TableQueryBuilder, engine_url: str) -> None:
        self.query_builder = query_builder
        self.engine = create_engine(engine_url)
        self.metadata = MetaData()

    def create_tmp_table(self) -> bool:
        pass

    def delete_tmp_table(self) -> bool:
        pass
```
1.2 Добавим атрибут движка БД, мок для билдера табличного запроса.
```python
 class TestTmpTableManager:
     @pytest.fixture(autouse=True)
     def setup_class(self):
         self.engine_url = "sqlite:///" + tempfile.NamedTemporaryFile(suffix=".db").name
         self.table_query_builder = Mock()
         self.tmp_table_manager = TmpTableManager(
             self.table_query_builder, engine_url=self.engine_url
         )

     def test_create_tmp_table(self):
         self.tmp_table_manager.create_tmp_table()
```
Тестирование успешно проходит.
```bash
================================================================================== test session starts ==================================================================================
platform linux -- Python 3.10.11, pytest-7.3.1, pluggy-1.0.0
rootdir: /app/tests
collected 2 items

test_table_manager.py .                                                                                                                                                           [ 50%]

=================================================================================== 2 passed in 0.07s ===================================================================================
root@16080d885c64:/app/tests#
```
Делаем коммит.

1.3 Нужно заменить table_query_builder на реальзую SQLAlchemy таблицу для тестирования.
Добавим проверку в тест, что после создания таблицы она реально появляется в тестовой базе.
```python
 class TestTmpTableManager:
     @pytest.fixture(autouse=True)
     def setup_class(self):
         self.engine_url = "sqlite:///" + tempfile.NamedTemporaryFile(suffix=".db").name
         self.test_table = Table(
             "test_table",
             MetaData(),
             Column("id", types.Int8, primary_key=True),
             Column("name", types.String),
         )

         self.table_query_builder = Mock()
         self.table_query_builder.table_query = self.test_table

         self.tmp_table_manager = TmpTableManager(
             self.table_query_builder, engine_url=self.engine_url
         )

     def test_create_tmp_table(self):
         assert self.tmp_table_manager.create_tmp_table() is True
         inspector = inspect(self.tmp_table_manager.engine)
         assert "test_table" in inspector.get_table_names()
```
1.4 Теперь у нас есть все что нужно, чтобы написать реализацию.
```python
 def create_tmp_table(self) -> bool:
     tmp_table = self.query_builder.table_query

     if tmp_table is None:
         # TODO: add logging instead of print
         print("Table query is empty")
         return False

     try:
         tmp_table.create(self.engine)
     except Exception as ex:
         # TODO: add logging instead of print
         print(f"Table creation failed with exception {ex}")
         return False
     return True
```
Тест не проходит :( (чуть позже понял: на самом деле проблема в том, что я тестирую поля из Кликхаусе в SQLite), возвращаемся к 1.4
```bash
======================================================================================= FAILURES ========================================================================================
_______________________________________________________________________ TestTmpTableManager.test_create_tmp_table _______________________________________________________________________

self = <tests.test_table_manager.TestTmpTableManager object at 0x7f4d95a59000>

def test_create_tmp_table(self):
self.tmp_table_manager.create_tmp_table()
inspector = inspect(self.tmp_table_manager.engine)
>       assert "test_table" in inspector.get_table_names()
E       AssertionError: assert 'test_table' in []
E        +  where [] = <bound method Inspector.get_table_names of <sqlalchemy.engine.reflection.Inspector object at 0x7f4d95aa89d0>>()
E        +    where <bound method Inspector.get_table_names of <sqlalchemy.engine.reflection.Inspector object at 0x7f4d95aa89d0>> = <sqlalchemy.engine.reflection.Inspector object at 0x7f4d95aa89d0>.get_table_names

test_table_manager.py:31: AssertionError
--------------------------------------------------------------------------------- Captured stdout call ----------------------------------------------------------------------------------
Table creation failed with exception (in table 'test_table', column 'id'): Compiler <sqlalchemy.dialects.sqlite.base.SQLiteTypeCompiler object at 0x7f4d95a5a080> can't render element of type Int8
================================================================================ short test summary info ================================================================================
FAILED test_table_manager.py::TestTmpTableManager::test_create_tmp_table - AssertionError: assert 'test_table' in []
=================================================================================== 1 failed in 0.18s ===================================================================================
```
1.5 После небольшой корректировки все хорошо, делаем коммит.
```python
 self.test_table = Table(
     "test_table",
     MetaData(),
     Column("id", types.Int, primary_key=True),
     Column("name", types.String),
 )
```
```bash
commit 2030a6c19f1ad758e269c52f2099538802ff12ee (HEAD -> main)
Author: Pavel <barabanovpv95@gmail.com>
Date:   Sun May 14 19:01:45 2023 +0300

feat: add implementation and complete test for TmpTableManager create_table
```


### 2. Анализ первой попытки.

Думаю, можно начать с еще более раннего этапа, и написать тест еще до создания класса.
1.1 Просто вызовем метод.
```python
import pytest

class TestTmpTableManager:
    def test_create_tmp_table(self):
        self.tmp_table_manager.create_tmp_table(self.table_name)
```
```bash
======================================================================================= FAILURES ========================================================================================
_______________________________________________________________________ TestTmpTableManager.test_create_tmp_table _______________________________________________________________________
self = <test_table_manager.TestTmpTableManager object at 0x7f019d375ae0>

def test_create_tmp_table(self):
>       self.tmp_table_manager.create_tmp_table(self.table_name)
E       AttributeError: 'TestTmpTableManager' object has no attribute 'tmp_table_manager'

test_table_manager.py:8: AttributeError
================================================================================ short test summary info ================================================================================
FAILED test_table_manager.py::TestTmpTableManager::test_create_tmp_table - AttributeError: 'TestTmpTableManager' object has no attribute 'tmp_table_manager'
============================================================================== 1 failed, 1 passed in 0.27s ==============================================================================
root@16080d885c64:/app/tests#
```
1.2 Начинаем сначала. Чтобы работало хоть как-то, добавим фальшивую реализацию.
```python
class TestTmpTableManager:
    @pytest.fixture(autouse=True)
    def setup_class(self):
        self.tmp_table_manager = Mock()
        self.table_query_builder = Mock()

    def test_create_tmp_table(self):
        self.tmp_table_manager.create_tmp_table()
```
```bash
================================================================================== test session starts ==================================================================================
platform linux -- Python 3.10.11, pytest-7.3.1, pluggy-1.0.0
rootdir: /app/tests
collected 2 items

test_table_manager.py .                                                                                                                                                           [ 50%]

=================================================================================== 2 passed in 0.07s ===================================================================================
root@16080d885c64:/app/tests#
```
1.3 Работает, значит коммитим.
```bash
commit 24782bd5c7629588a480424e99c79ad1475bf5f7 (HEAD -> main)
Author: Pavel <barabanovpv95@gmail.com>
Date:   Sun May 14 17:28:22 2023 +0300

feat: test for tmp_table_manager with fake implementation
```


### 3. Выводы

С одной стороны действительно ощущается что это максимально контролируемая разработка, в любой момент времени
понятно, на каком этапе мы находимся и нет опасаний, в любой момент можно сделать небольшой шаг назад без больших потерь.
C другой стороны потратил несколько часов на очень простенький код, который можно было написать за 15 минут :).
Иногда кажется, что слишком много доп.усилий уходит на то, чтобы двигаться так мелкими шажками.
Все же думаю, что с опытом можно научиться разрабатывать в таком ритме значительно быстрее.


## Попытка 2.

### 1. Этап разработки.

2.1 Продолжим создание тестов для Менеджера Таблиц.
Создадим тест для удаления временной таблицы.
```python
def test_delete_tmp_table(self):
    pass
```
2.2 
- Вызовем создание таблицы.
- Вызовем метод удаления, метод должен завершаться без ошибок и возвращать True.
```python
def test_delete_tmp_table(self):
    self.tmp_table_manager.create_tmp_table()
    assert self.tmp_table_manager.delete_tmp_table() is True
```
- Создадим временную фальшивую имплементацию.
```python
def delete_tmp_table(self) -> bool:
    try:
        return True
    except Exception as ex:
        # TODO: add logging instead of print
        print(f"Table deletion failed with exception {ex}")
        return False
```
- Убедимся, что тесты все еще проходят.
```bash
================================================================================== test session starts ==================================================================================
platform linux -- Python 3.10.11, pytest-7.3.1, pluggy-1.0.0
rootdir: /app/tests
collected 2 items

test_table_manager.py ..                                                                                                                                                          [100%]

=================================================================================== 2 passed in 0.13s ===================================================================================
root@16080d885c64:/app/tests#

```
- Коммитим изменения.

2.3
- Очевидно, чтобы убедиться, что таблица действительно удаляется,
  После удаления мы больше не должны видеть таблицу в инспекторе.
  Добавим в тест, что сначала таблица была видна, а после удаления нет.
```python
def test_delete_tmp_table(self):
    self.tmp_table_manager.create_tmp_table()
    inspector = inspect(self.tmp_table_manager.engine)
    
    # Table in place here
    assert "test_table" in inspector.get_table_names()
    
    # After deletion there is no table
    assert self.tmp_table_manager.delete_tmp_table() is True
    inspector = inspect(self.tmp_table_manager.engine)
    assert "test_table" not in inspector.get_table_names()
```
- На текущий момент это естественно приводит к ошибке.
```bash
# After deletion there is no table
assert self.tmp_table_manager.delete_tmp_table() is True
inspector = inspect(self.tmp_table_manager.engine)
    assert "test_table" not in inspector.get_table_names()
    AssertionError: assert 'test_table' not in ['test_table']
     +  where ['test_table'] = <bound method Inspector.get_table_names of <sqlalchemy.engine.reflection.Inspector object at 0x7f06e4f3ded0>>()
     +    where <bound method Inspector.get_table_names of <sqlalchemy.engine.reflection.Inspector object at 0x7f06e4f3ded0>> = <sqlalchemy.engine.reflection.Inspector object at 0x7f06e4f3ded0>.get_table_names

test_table_manager.py:43: AssertionError
```
  2.4
- Имплементация очень простая после работы с прошлым методом.
```python
...
try:
    tmp_table.drop(self.engine)
    return True
...
```
- Тест проходит.
- Делаем коммит.

2.5
Подумаем, что будет, если а) Создается уже существующая таблица б) Удаляется не существующая таблица.
В идеале в этом случае нужно поднимать исключение.
Создадим тесты, что эти исключения действительно вызываются.
```python
def test_create_existing_table(self):
    self.tmp_table_manager.create_tmp_table()
    with pytest.raises(TableAlreadyExistsError):
        self.tmp_table_manager.create_tmp_table()


def test_delete_non_existing_table(self):
    with pytest.raises(TableDoesNotExistsError):
        self.tmp_table_manager.delete_tmp_table()
```
- Тесты не проходят, т.е. не существует таких исключений.
```bash
================================================================================ short test summary info ================================================================================
FAILED test_table_manager.py::TestTmpTableManager::test_create_existing_table - NameError: name 'TableAlreadyExistsError' is not defined
FAILED test_table_manager.py::TestTmpTableManager::test_delete_non_existing_table - NameError: name 'TableDoesNotExistsError' is not defined
============================================================================== 2 failed, 2 passed in 0.19s ==============================================================================
```
- Нужно:
    - Создать исключения.
    - Добавить исключения в методы класса TmpTableManager
```python
class TableAlreadyExistsError(Exception):
    pass


class TableDoesNotExistsError(Exception):
    pass
```
```python
def delete_tmp_table(self) -> bool:
    try:
        tmp_table = Table(
            self.query_builder.table_name,
            self.metadata,
            autoload_with=self.engine,
        )
        tmp_table.drop(self.engine)
        return True
    except NoSuchTableError:
        raise TableDoesNotExistsError(
            f"Trying to delete non existing {self.query_builder.table_name}"
        )
    except Exception as ex:
        # TODO: add logging instead of print
        print(f"Table deletion failed with exception {ex}")
        return False
```
```python
# здесь была ошибка в проверке что таблица уже существует
if self.engine.dialect.has_table(self.engine, self.query_builder.table_name):
    raise TableAlreadyExistsError(
        f"Table {self.query_builder.table_name} already exists"
    )
```
Получаем ошибку:
```bash
FAILED test_table_manager.py::TestTmpTableManager::test_create_existing_table - sqlalchemy.exc.ArgumentError:
The argument passed to Dialect.has_table() should be a <class 'sqlalchemy.engine.base.Connection'>,
got <class 'sqlalchemy.engine.base.Engine'>
```
Откатываемся назад к последнему коммиту.

Корректная реализация.
```python
with self.engine.connect() as connection:
    if self.engine.dialect.has_table(connection, self.query_builder.table_name):
        raise TableAlreadyExistsError(
            f"Table {self.query_builder.table_name} already exists"
        )
```
Теперь все тесты проходят.
```bash
================================================================================== test session starts ==================================================================================
platform linux -- Python 3.10.11, pytest-7.3.1, pluggy-1.0.0
rootdir: /app/tests
collected 4 items

test_table_manager.py ....                                                                                                                                                        [100%]

=================================================================================== 4 passed in 0.14s ===================================================================================
```


### 2. Анализ второй попытки.

2.5 В идеале создать тесты отдельно, и сделать отдельные коммиты под них.
- Тестируем создание уже существующей таблицы.
```python
def test_create_existing_table(self):
    self.tmp_table_manager.create_tmp_table()
    with pytest.raises(TableAlreadyExistsError):
        self.tmp_table_manager.create_tmp_table()
```
- Тест проходит -> коммит.

- Тестируем создание уже существующей таблицы.
```python
def test_delete_non_existing_table(self):
    with pytest.raises(TableDoesNotExistsError):
        self.tmp_table_manager.delete_tmp_table()
```
- Тест проходит -> коммит.

Также в 2.5 лучше сначала отдельно реализовать исключения -> проверить тесты.
Тогда тесты покажут ошибку отсутствия реализации в методах.
```bash
================================================================================ short test summary info ================================================================================
FAILED test_table_manager.py::TestTmpTableManager::test_delete_non_existing_table - Failed: DID NOT RAISE <class 'client_worker.tmp_table_manager.TableDoesNotExistsError'>
============================================================================== 1 failed, 2 passed in 0.20s ==============================================================================
```
Затем добавить исключения в методы -> проверить тесты -> сделать коммит.
P.S. На деле так и прозошло, пришлось откатиться к началу 2.5


### 3. Выводы.

Со второй попытки заметно проще, но все равно кажется медленно).
Особенно сложно бороться с искушением не откатываться назад после получения какой-нибудь глупой ошибки.
В итоге получилось 12 коммитов, в обычном случае у меня было бы 2-3 на подобную задачу.
Буду пытаться так работать, дает комфортное чувство надежности :) при разработке, хотя времени пока отнимает значительно больше.
