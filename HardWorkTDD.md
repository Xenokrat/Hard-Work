# Hard Work TDD | Думать на уровне дизайна

## Test driven development -- Первая попытка

### Проект - сервис для формирования очетов для клиентов из наших базы данных.

- Сначала напишем тесты для клиентов базы данных. Используем Mocks, так как сейчас у меня пока нет готовых SQL-запросов для тестирования БД, поэтому тестируем только код Python.

Рекомендация по тестированию баз данных от ChatGPT4:

>- If you only need to test how your code interacts with the database and not the actual SQL queries,
> then mocking the database is a good choice.
>- If your code relies on specific database features or behavior that cannot be easily mocked or reproduced with an in-memory database, 
> using a dedicated test database might be more appropriate.
> - If you want to test the actual SQL queries and their results but don't need a full-fledged database, 
> using an in-memory or temporary database could be a suitable option.

<hr>
<br>
Итак, согласно _ChatGPT_, сначала реализуем mocking тестирование, 
а потом, когда будут актуальные SQL-запросы, сможем реализовать тесты и для них.

<br>
Пример теста для клиента базы PostgreSQL:

```python
import unittest
from unittest.mock import MagicMock

from suckless_rsq.clients.postgresql_client import PostgreSQLClient


class TestPostgreSQLClient(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_session = MagicMock()
        self.postgresql_client = PostgreSQLClient(self.mock_session)

    def test_execute_query(self) -> None:
        query = "SELECT * FROM test_table;"
        self.postgresql_client.execute_query(query)
        self.mock_session.execute.assert_called_with(query)


if __name__ == "__main__":
    unittest.main()
```

- Реализация после теста:

```python
from typing import Any, List, Optional, Tuple

from sqlalchemy.orm import Session


class PostgreSQLClient:
    def __init__(self, session: Session) -> None:
        self.session = session

    def execute_query(self, query: str) -> Optional[List[Tuple[Any, ...]]]:
        result = self.session.execute(query)
        return result.fetchall()
```


## Вторая попытка
## Мышление на уровне спецификации


- Во-первых: неприятная вещь, но я действительно не начал с планирования хотя бы структуры всего сервиса, вообще откровенно говоря, до нее как правило не доходит дело, сейчас в нашем производственном коде не пишут даже юнит-тестов :).

- Попробуем составить план по сервису отчетов согласно единому дизайну.

<hr>
1. Существует несколько клиентов базы данных, реализация которых должна быть схожей
Поэтому следует создать классы:

<br>

**AbstractDBClient**

  Методы:

    - execute_query - получает данные в списке от конкретной базы данных.
    - execute_query_iter - получает данные порциями.

Реализация:

-> **ClickhouseDBClient** - реализация клиента для базы данных Clickhouse.

-> **PostgreSQLDBClient** - реализация клиента для базы данных Postgresql.

-> ...**Потенциально, другие бд**.

<hr>
2. Существует несколько вариантов формата конечных отчетов.
Поэтому мы должны добавить классы:

<br>

**AbstractReportFormat**

  Методы:

    - write_report - записывает данные в файл.

Реализация:

-> **ExcelReportFormat** - отчет в формате xlsx.

-> **CSVReportFormat** - отчет в формате csv.

-> ...**Потенциально, другие форматы**.

<hr>
1. Базовый отчет, одинаковый для всех баз данных и клиентов.
    Реализуется следующим образом:

<br>

**AbstractReport**

    Получает при создании:
    - AbstractDBClient
    - AbstractReportFormat
    
  Методы:
    
    - get_sql_query - формирует SQL запрос на основе данных настроек (config).
    - make_report - запрашивает данные из базы и записывает их в файл.

Реализация:

    -> ShelfReport
    -> SearchReport
    -> CategoryReport
    ...

- Также есть клиенты, у которых есть дополнительные специфические требования к базовым видам отчетов
   Я думаю, мы должны реализовать это при помощи наследования:

Реализация:

    -> Client1ShelfReport(ShelfReport)
    -> Client2CategoryReport(CategoryReport)
    ...

По итогам основная функция будет выглядеть примерно так:
    
    1. Получаем POST запрос с данными настроек (config).
    2. Создаем объект report на основе запрашиваемых данных.
    3. Создаем и записываем отчет.

Например:
```python
report = Client1ShelfReport(
    config = config
    db_client = ClickhouseClient(),
    format = CSVReport(),
)
data = report.make_report()
data.save_report()
```

Я думаю, потому что в спецификации есть такие форматы, как CSVReport,
мы могли бы получать данные порциями и сразу же записывать их.
Эта идея вроде следует из как раз из дизайна спецификации :).

Добавим тест метода для итеративного выполнения запроса для клиентов.

Пример PostgreSQL:

```python
import unittest
from unittest.mock import MagicMock

from suckless_rsq.clients.postgresql_client import PostgreSQLClient


class TestPostgreSQLClient(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_session = MagicMock()
        self.postgresql_client = PostgreSQLClient(self.mock_session)

    def test_execute_query(self) -> None:
        query = "SELECT * FROM test_table;"
        self.postgresql_client.execute_query(query)
        self.mock_session.execute.assert_called_with(query)

    def test_execute_query_iter(self) -> None:
        query = "SELECT * FROM test_table;"
        mock_result_proxy = MagicMock()
        self.mock_session.execute.return_value = mock_result_proxy
        result_iterator = self.postgresql_client.execute_query_iter(query)
        self.assertEqual(result_iterator, mock_result_proxy)


if __name__ == "__main__":
    unittest.main()
```

- Реализация на основе нового теста:
```python
from typing import Any, List, Optional, Tuple

from sqlalchemy.engine import ResultProxy
from sqlalchemy.orm import Session


class PostgreSQLClient:
    def __init__(self, session: Session) -> None:
        self.session = session

    def execute_query(self, query: str) -> Optional[List[Tuple[Any, ...]]]:
        result = self.session.execute(query)
        return result.fetchall()

    def execute_query_iter(self, query: str) -> ResultProxy:
        result = self.session.execute(query)
        return result
```
  **TODO**: продолжаем:
- Берем элемент спецификации.
- Пишем под него тесты.
- Пишем код, следующий из спецификации и проверяемый тестами.
- Рефакторинг, когда тесты проходят и если требуется.
