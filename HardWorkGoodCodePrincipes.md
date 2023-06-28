# Hard Work - Good Code Principles

## Создаем компактную подходящую абстракцию для типичных управленческих шаблонов

## Пример 1

- До
  
  Думаю классический пример это управление подключением в БД.
  В первые разы еще плохо понимал контекстные менеджеры (кроме самого простого примера с `with open('file', 'r') as f`).
  Использовал обычный `try-except`.

```python
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError

url = "postgresql://username:password@localhost/mydatabase"

def do_query(query):
    engine = None
    connection = None
    try:
        engine = sa.create_engine(url)
        connection = engine.connect()
        connection.execute(query)
        connection.commit()
    except SQLAlchemyError as e:
        connection.rollback()
        log.error(f'database error: {e}')
    finally:
        if connection is not None:
            connection.close()
        if engine is not None:
            engine.close()
```

- После

  Во-первых, во всех современных примерах sqlalchemy сейчас используются контекстые менеджеры.
  Во-вторых, также рекомендуется использовать сессии для выполнения ряда действий с базой данных.

```python
 import sqlalchemy as sa
 from sqlalchemy.orm import Session
 
 url = "postgresql://username:password@localhost/mydatabase"
 
 def do_query(query):
     engine = sa.create_engine(url)
     with Session(engine) as session:
         with session.begin():
             session.execute(query)
```

- Еще немного более элегантный пример из документации.

```python
 import sqlalchemy as sa
 from sqlalchemy.orm import Session
 
 url = "postgresql://username:password@localhost/mydatabase"
 
 def do_query(query):
     engine = sa.create_engine(url)
     with Session(engine) as session, session.begin():
         session.execute(query)
```

## Пример 2

- До
  
  Внутри класса по созданию отчетов имеем метод, который на основе датафрейма находит повторяющиеся строки.
  Если при записи результатов работы метода появляется новая площадка, необхдимо проверять, что в словаре
  нет такой записи и добавлять ее, иначе возможно получить `KeyError`. Встроенная библиотека `collections`
  предоставляет объект `defaultdict`, который позволяет не проводить проверку на наличие ключа, устанавливая значение по
  умолчанию (в данном случае при подсчете дубликатов начинаем с 0).
  
  Также в этом классе есть метод, `is_any_duplicates` который возвращает булевое значение наличия дубликатов в отчете, его также можно упростить.

```python
 class MainReport:
     def __init__(self, start_date, end_date, user, report_id, config):
         ...
         self.duplicate_rows_by_app = {}
         ...

     def count_dublicate_rows(self, report_df: DataFrame):
         ...
         # Расчет повторяющихся строк
         for app, count in results.to_numpy():
             if app not in self.duplicate_rows_by_app:
                 self.duplicate_rows_by_app[app] = 0
                 self.duplicate_rows_by_app[app] += count
             else:
                 self.duplicate_rows_by_app[app] += count

         ...
     def is_any_duplicates(self):
         if len(self.duplicate_rows_by_app) == 0:
             return False
         else:
             return True
```

- После внесенных изменений.

```python
from collections import defaultdict


 class MainReport:
     def __init__(self, start_date, end_date, user, report_id, config):
         ...
         self.duplicate_rows_by_app = defaultdict(int)
         ...

     def count_dublicate_rows(self, report_df: DataFrame):
         ...
         # Расчет повторяющихся строк
         for app, count in results.to_numpy():
             self.duplicate_rows_by_app[app] += count

         ...
    def is_any_duplicates(self) -> bool:
        return self.duplicate_rows_by_app
```

## Пример 3

- До
  
Ещё пример с контекстным менеджером, но с другой стороны. данном случае можно оптимизировать
Имеется класс, реализующий контекстный менеджер для парсинга конфигурационного файла в формате .yaml
В таком виде этот класс нужен только для реализации методов `__enter__` и `__exit__`, поэтому в итоге такое решение выглядит
довольно громоздко.

Библиотека `contextlib` позволяет создавать более компактные варианты для контекстных менеджеров.
В данном случае (т.к. не требуется сложная обработка исключений, или какое-то дополниттельное поведение, реализуемое классов)
мы можем полностью заменить класс на функцию `read_yaml_config_file` к которой применяется декоратор `@contextmanager`

```python
class ReadYAMLConfigFile:
    def __init__(self, file_path: str) -> None:
        self.file_path = file_path
        self.file_obj = None

    def __enter__(self):
        conf = open(file_path, "r")
        self.file_obj = yaml.safe_load(conf)
        return self.file_obj

    def __exit__(self, exc_type, exc_value, exc_tb) -> None:
        if self.file_obj:
            self.file_obj.close()
        if isinctance(exc_type, FileNotFoundError):
            log.error("Config file not found")
            sys.exit(-1)
 
```

- После переписывания получаем более компактный менеджер контекста.

```python
from contextlib import contextmanager


@contextmanager
def read_yaml_config_file(file_path: str):
     try:
         with open(file_path, "r") as configfile:
             yield yaml.safe_load(configfile)
     except FileNotFoundError:
         log.error("Config file not found")
         sys.exit(-1)
```

## Краткие выводы

В языке Python стандартная библиотека дает большой набор уже готовых абстракций (`functools`, `itertools`, `collections` и т.д)
которые позволяют значительно сократить размер кода и выразить его более читабельно и элегантно.
Если при работе есть ощущение, что проблема типовая, с большой долей вероятности в перечисленных библиотеках есть более подходящее решение, чем написанное с нуля.
