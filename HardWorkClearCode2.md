# Hard Work - Clear Code 2

## 2.1 Класс слишком большой или в программе создается слишком много его инстансов

- Пример:
  
  Класс для отправки писем с отчетами.
  Пример слишком большого класса.

```python
 class EmailSender:
     def __init__(self, emails, email_subject, start_date, end_date, language):
         self.emails = emails
         self.email_subject = email_subject
         self.start_date = start_date
         self.end_date = end_date
         self.language = language

         self.writers_xlsx = None
         self.writers_csv = None

     def send_to_server(self):
         """
         Метод пересылает созданные отчеты на сервер nginx
         """

     @staticmethod
     def send_message_to_email(recipient_address, message, subject):
         """
         Метод отправляет на почту recipient_address письмо message с темой subject
         """

     def send_report_to_email(self, recipient_address):
         """
         Метод отправляет на почту recipient_address письмо с ссылками на отчеты
         """
         

     def send_emails_with_no_data(self):
         """
         Метод отправляет на все почты из self.emails письмо о том, что данных нет
         :return:
         """
         

     def send_emails_with_reports(self, writers_xlsx, writers_csv):
         """
         Метод отправляет все отчеты из writers_xlsx и writers_csv на сервер и после на все почты из self.emails
         :param writers_xlsx:
         :param writers_csv:
         :return:
         """
```

- Как можно поправить:

1. Метод отправки отчетов на сервер `send_to_server` не должен принадлежать классу email. Метод `send_emails_with_reports` также связан с пересылкой отчетов. Следует создать отдельный класс `ReportSender`.
2. Еще возможный вариант исправления -- создать родительский класс EmailSender. Унаследовать от него классы, реализующие каждый вариант отправки отчетов.

- Пример после:
  
  Уберем лишние методы из класса.

```python
 class EmailSender:
     def __init__(self, emails, email_subject, start_date, end_date, language, report_sender: ReportSender):
         # Включили в конструктор класс ReportSender
         ...

     @staticmethod
     def send_message_to_email(recipient_address, message, subject):
         ...

     def send_report_to_email(self, recipient_address, report_sender):
         ...
         
     def send_emails_with_no_data(self):
         ...
         
 class ReportSender:
     def send_reports_to_server(self):
         ...

     def prepare_reports_to_sending(self, writers_xlsx, writers_csv):
         ...
```

- Результат:
  
  Сделали класс более соответсвующим SRP, разделив логику отправки отчетов на сервер и отправки писем.

## 2.2 Класс слишком маленький или делает слишком мало

- Пример:
  
  Единственная задача класса - добавить в родительский класс запрос для вставки данных под конкретного клиента.

```python
 class ClientXInsertTask(InsertTask):
     def __init__(
         self,
         config: ProcessConfig,
     ) -> None:
         super().__init__(config)
         self.insert_query = insert_into_search_query
```

- Как можно поправить:
  
  Возможно, не создавать подкласс для каждого отдельного случая.
  Можно попробовать обойтись словарем для набора клиентов.

- Пример после:

```python
 class InsertTask:
     def __init__(
         self,
         config: ProcessConfig,
     ) -> None:
         super().__init__(config)
         self.insert_queries = {
             "clientx": clientx_query,
             "clienty": clienty_query,
         }
```

- Результат:
  
  Сократили всю иерархию классов до одного класса, покрывающего всех клиентов.

## 2.3 В классе есть метод, который больше подходит для другого класса

- Пример:
  
  Класс, который реализует алерты исходя из полученных в базе данных значений.
  реализует метод `get_db_session(self, dsn: str)` который служит для подключения к БД.
  Лучше, если этот метод будет в отдельном классе, который отвечает полностью за БД.

```python
 class AlertSystem:
     def __init__(self, dsn, slack_webhook_url, initial_alert_delay):
         self.slack_webhook_url = slack_webhook_url
         self.initial_alert_delay = initial_alert_delay
         self.alert_trackers = {}
         self.dsn = dsn

     def get_db_session(self, dsn: str) -> None:
         ...

     def __get_results_from_db(self, query) -> List[Rows]:
         ...

     def check_time_diff(self) -> None:
         ...
```

- Как можно поправить:
  Вынесем метод `get_db_session(self, dsn: str)` в класс, который отвечает за БД.

- Пример после:

```python
 class AlertSystem:
     def __init__(self, db_client: DB, slack_webhook_url, initial_alert_delay):
         # Теперь класс получает экземпляр класса БД для реализации запросов
         self.database_connection = db_client
         self.slack_webhook_url = slack_webhook_url
         self.initial_alert_delay = initial_alert_delay
         self.alert_trackers = {}

     def __get_results_from_db(self, query) -> List[Rows]:
         ...

     def check_time_diff(self) -> None:
         ...

 class DB(ABC):
     def __init__(self, db_user, db_passwd, db_host, db_port, db_name,) -> None:
         ...

     @staticmethod
     @abstractmethod
     def get_connection_dsn(
         db_user: str,
         db_passwd: str,
         db_host: str,
         db_port: str,
         db_name: str,
     ) -> str:
         pass

     @staticmethod
     def get_engine(dsn) -> sa.engine.Engine:
         ...

     @contextmanager
     def get_session(self) -> Generator[Session, None, None]:
         with Session(self.engine) as session:
             yield session
```

- Результат:
  
  Мы убрали из класса для Алертов ответственность за создание сессии с БД и перенесли этот метод в более подходящий класс для взаимодействия с БД.

## 2.4 Класс хранит данные, которые загоняются в него в множестве различных мест программы

- Пример:
  
  Имеется класс `ConfigParserYAML`, который парсит конфиг файл и передает информацию о настройках программы другим классам.
  Однако этот же класс используется иногда как промежуточное хранилище информации для других классов.

```python
class ConfigParserYAML:
 def __init__(self, config_file: str = "config.yaml") -> None:
     ... # загружаем конфиг из yaml файла
     self.config = parsed_yaml
     self.date = parsed_yaml.get("date")
     if self.date is None:
         self.date = (datetime.now() - timedelta(days=1)).date()
     else:
         self.date = (datetime.strptime(self.date, "%Y-%m-%d")).date()
     ...

 def get_date(self) -> datetime:
     return self.date

 def get_stages(self) -> Dict[str, List[str]]:
     return self.stages
```

Например:

```python
 class Processor:
     def __init__(
         self,
         stages: Dict[str, List[str]],
         process_config: ConfigParserYAML

     ) -> None:
         self.process_config = process_config
         # Класс сохраняет атрибуты, не имеющие к нему непосредственного отошения
         self.process_config.engine = clickhouse_engine
         self.process_config.metadata = MetaData(bind=self.click_engine)
         ...
```

- Как можно поправить:
  
  Если между классами необходимо передавать общую информацию, связанную с БД, для этого можно использовать отдельный класс.

- Пример после:

```python
 class ClickConfig(DBConfig):
     def __init__(self):
         self.engine = clickhouse_engine
         self.metadata = MetaData(bind=self.click_engine)
         ...
```

- Результат:

  Мы перестали передавать в различных местах программы в класс информацию, которая непостедственно не относится к его зоне ответственности.

## 2.5 Класс зависит от деталей реализации других классов

- Пример:

  Класс для обработки набора задач создает внутри в методе `__prepare_coroutines` подкласс Visitor'а.
  Следовательно, весь класс `Stage` зависит теперь от реализации `TaskProcessVisitor`.

```python
 class Stage:
     def __init__(
         self,
         name: str,
         commands: List[str],
         config: ProcessConfig,
         dbconfig: DBConfig,
     ) -> None:
         self.name = name
         self.dbconfig = dbconfig
         self.fabric = TaskFabric(commands, config)
         self.tasks: List[Task] = self.fabric.task_obj

     async def __prepare_coroutines(self) -> None:
         async_click_engine = self.dbconfig.get_click_async_engine()

         coroutines: List[Awaitable] = []

         # Создаем Посетителя
         visitor = TaskProcessVisitor()
         for task in self.tasks:
             coro = task.accept(visitor)
             coroutines.append(coro)

         await asyncio.gather(*coroutines)
         await async_click_engine.dispose()  # type: ignore

     def execute_stage(self) -> None:
         ...
```

- Как можно поправить:
  
  Лучше не создавать внутри `Stage` конкретный класс Посетителя, вместо этого будем передавать экземпляр
  Посетителя в конструктор (в конструкторе тип агрумента будет абстрактным посетителем).

- Пример после:

```python
 class Stage:
     def __init__(
         self,
         name: str,
         commands: List[str],
         config: ProcessConfig,
         visitor: Visitor
     ) -> None:
         self.name = name
         self.config = config
         self.fabric = TaskFabric(commands, config)
         self.tasks: List[Task] = self.fabric.task_obj
         self.visitor = visitor

     async def __prepare_coroutines(self) -> None:
         async_click_engine = self.config.get_click_async_engine()

         coroutines: List[Awaitable] = []

         # больше не создаем Посетителя
         for task in self.tasks:
             coro = task.accept(self.visitor) # используем переданный экземпляр Посетителя
             coroutines.append(coro)

         await asyncio.gather(*coroutines)
         await async_click_engine.dispose()  # type: ignore

     def execute_stage(self) -> None:
         ...
     # В другом месте программы
```

- Результат:

## 2.6 Приведение типов вниз по иерархии (родительские классы приводятся к дочерним)

- Пример:

  Имеется родительский класс `Database` и подклассы `Postgresql`, `MySQL`.
  В списке клиентов баз данных (`Database`) проверяется принадлежность дочернему классу.

```python
class Database:
    def __init__(self, connection):
        self.connection = connection

    def get_data(self):
        raise NotImplementedError("Should be used on concrete database")

class Postgresql(Database):
    def get_data(self):
        ...

class MySQL(Database):
    def get_data(self):
        ...

 ...
db_clients = [Postgresql(connection), MySQL(connection), ...]
#
# Здесь может быть точно неизвестно, покроют ли все условия if объекты в списке.
for client in db_clients:
    if isinstance(client, Postgresql): get_date() # do smth
    if isinstance(client, MySQL): get_date() # do smth

 # В таком примере получится ошибка
 db_clients = [Postgresql(connection), MySQL(connection), MongoDB(connection)]
 for client in db_clients:
     if isinstance(client, Postgresql): get_date() # do smth
     if isinstance(client, MySQL): get_date() # do smth
```

- Как можно поправить:
  
  Полиморфизм подтипов по дизайну не отличается значительно, но не нарушает принцип подстановки Лисков.

- Пример после:

```python
class Database(ABC):
    def __init__(self, connection):
        self.connection = connection

    @abstractmethod 
    def get_data(self):
        pass

class Postgresql(Database):
    def get_data(self):
        ...

class MySQL(Database):
    def get_data(self):
        ...

db_clients = [Postgresql(connection), MySQL(connection), ...]

# Здесь может быть точно неизвестно, покроют ли все условия if объекты в списке.
for client in db_clients:
    client.get_data()

```

  Более очевидный пример, чем в Python будем видимо в языке вроде Java (т.к. в Питоне нет прямого понижения типов)

```java
public class Database{}
public class Postgresql extends Database{}

public static void main(String[] args) {
    Database parentClient = new Postgresql();
    Postgresql clildClient = (Postgresql)parentClient;
}
```

- Результат:

  Новый дизайн не нарушает принцип подстановки и не вызовет ошибку при приведении к дочерним классам.

## 2.7 Когда создается класс-наследник класса, приходится создавать классы-наследники для некоторых других классов

- Пример:
  
  В примере ниже класс `CSVDatasource` наследуется от класса `FileDatasource` и зависит от его реализации.
  Точно так же, если мы захотим создать подкласс `PostgresqlDatasource`, то придется наследовать его
  не от `Datasouce`, а создавать (как ниже в примере) промежуточный класс `SQLDatasource`.

```python
class Datasource:
    def __init__(self):
        ...

    def get_data(self):
        ...

 class FileDatasource(Datasource):
    def __init__(self, file_path):
        self.file_path = file_path

    def get_data(self):
        """Открывает и читает текстовый файл"""
        with open(self.file_path, "r") as f:
            ...
     
 class SQLDatasource(Datasource):
     def __init__(self, sql_client):
        self.sql_client = sql_client

     def get_data(self):
         """Создает подключение в бд"""
        self.sql_client.execute_query('SELECT 1')

 class CSVDatasource(FileDatasource):
 def get_data(self):
     """Открывает и читает текстовый файл"""
     with csv.read(self.file_path, "r") as f:
         ...
```

- Как можно поправить:
  
  Возможно 2 варианта решения -- либо огранизовать все так, чтобы все источники данных наследовались от абстрактного
  класса `Datasource`, либо SQLDatasource и FileDatasource должны быть независимыми абстрактными классами.

- Пример после:

```python
 class FileDatasource(ABC):
     def __init__(self, file_path):
         self.file_path = file_path

     @abstractmethod
     def get_data_from_file(self):
         pass
     

 class SQLDatasource(ABC):
     def __init__(self, sql_client):
         self.sql_client = sql_client

     @abstractmethod
     def get_data_from_db(self):
         pass
```

- Результат:
  
  После исправления при создании новых классов, отвечающих за источники данных больше не нужно создавать промежуточные
  классы для реализации.

## 2.8 Дочерние классы не используют методы и атрибуты родительских классов, или переопределяют родительские методы

- Пример:
  
  Класс `Alert` задает тип сообщения и релазизует метод `send_alert`. Однако наследники класса `TelegramAlert` и `SlackAlert`
  фактически полностью переопределяют метод `send_alert` и не используют атрибут `type_`.

```python
 class Alert:
     def __init__(self, type_, client):
         self.type_ = type_
         self.client = client

     def send_alert(self):
         self.client.send(f'alert {type_}')

 class SlackAlert(Alert):
     def __init__(self, type_, client):
         super().__init__(type_, client)
         self.message = 'Alert from Slack'

     def send_alert(self):
         self.client.send_to_slack(self.message)

 class TelegramAlert(Alert):
     def __init__(self, type_):
         super().__init__(type_, client)
         self.message = 'Alert from Telegram'

     def send_alert(self):
         self.client.send_to_telegram(self.message)
```

- Как можно поправить:
  
  Исправим иерархию классов так, чтобы не было необходимости переопределять метод. Для этого определим способ
  отправки сообщения в конструкторе. Также будем использовать аттрибут `type_` и в дочерних классах.

- Пример после:

```python
 class Alert:
     def __init__(self, type_, client):
         self.type_ = type_
         self.send_method = client.send
         self.message = f'Alert {_type}'

     def send_alert(self):
         self.send_method(self.message)

 class SlackAlert(Alert):
     def __init__(self, type_, client):
         super().__init__(type_, client)
         self.message = f'Alert {_type} from Slack'
         self.send_method = client.send_to_slack

 class TelegramAlert(Alert):
     def __init__(self, type_, client):
         super().__init__(type_, client)
         self.message = f'Alert {_type} from Telegram'
         self.send_method = client.send_to_telegram
```

- Результат:

  Улучшили дизайн таким образом, что больше нет необходимости в переопределении и дочерние классы используют родительский метод в зависимости от своих атрибутов.

## 3.1 Одна модификация требует внесения изменений в несколько классов

- Пример:
  
  Модуль для подготовки отчетов клиентам.
  Допустим, что необходимо добавить еще одного клиента.
  Имеется очень большой класс `MainReport` в котором в различных местах реализуется логика в зависимости от клиента.
  Также изменения потребуются в методах класса Sender.
  Имеются также другие классы, где хард-кодом упоминается название клиента, что также потребует каждый раз внесения изменений
  при появлении нового клиента.

```python
 class MainReport:
     def __init__(self, start_date, end_date, user, report_id, config):
         self.start_date = start_date
         self.end_date = end_date
         self.user = user
         self.report_id = report_id
         self.config = config

         self.updates_df = None
         self.writers_xlsx = defaultdict(dict)
         self.writers_csv = defaultdict(dict)
         self.stop_products = None
     ...

     def prepare_data_from_db(self):
         if self.user.lower() in ('client', 'client_xxxxxxxxxxxxx'): # hash
                     self.stop_products = pepsico_stop_products

     def remove_unnesessary_plt(self):
         if platforms and 'client' in platforms:
             platforms.remove('client')


 class Sender:
     ...
     def prepare_data_before_sending(self):
         # Берем данные клиента
         if platform_deliveries and 'client' in platform_deliveries:
             sber_platform_deliveries = {'client': self.config['platform_deliveries']['client']}
             sber_updates_df = self.get_full_query_df(
                 table_name='table_name',platform_deliveries=sber_platform_deliveries,)

```

- Как можно поправить:
  
  Весь модуль требует значительного рефакторина.
  Исправить возможно при помощи инкапсуляции клиентской логики. Для этого необходимо создать абстрактный класс клиета и от
  него реализовать поведение конкретных клиентов.

- Пример после:

```python
class Client(ABC):
     @abstractmethod
     def prepare_data_from_db(self):
        ...

     @abstractmethod
     def remove_unnesessary_plt(self):
        ...
        
     @abstractmethod
     def prepare_data_before_sending(self):
        ...

 class ConcreteClient(Client):
     def prepare_data_from_db(self):
         ...

     def remove_unnesessary_plt(self):
         ...

     def prepare_data_before_sending(self):
         ...

```

- Результат:
  
  При разрастании модуля с клиентскими отчетами, крайне затруднительно поддерживать архитектуру, где прописано разное поведение методов
  с условиями зависимости от конкретного клиента. Вместо этого необходимо инкапсулировать все методы, связанные с конкрентым
  клиентом и передавать классу Отчета такое объект для обработки.

## 3.2 Использование сложных паттернов проектирования там, где можно использовать более простой и незамысловатый дизайн

- Пример:
  
  Ранее использовал паттерн "Комманда" для реализации логики для схожих по задачам классов, но с разынми наборами методов,
  чтобы их можно было выполнить при помощи метода `execute`.

```python
 class AggregateXCommand(Command):
     def __init__(self, config: ProcessConfig) -> None:
         self.task = AggregationX(config)
     
     def execute(self) -> None:
         self.task.create_table(self.task.main_table)
         self.task.insert_into_table(self.task.insert_stmt)


 class AggregateYCommand(Command):
     def __init__(self, config: ProcessConfig) -> None:
         self.task = AggregationY(config)

     def execute(self) -> None:
         self.task.create_mat_view_1()
         self.task.create_mat_view_2()
         self.task.insert_into_table(self.task.table_1)
         self.task.insert_into_table(self.task.table_2)
```

- Как можно поправить:

  Можно обойтись без введения дополнительно обертки в виде классов-комманд, если у кажной задачи (`Aggregation` в примере)
  будет метод, обобщающий необходимые для выполнения операции (тот же метод `execute`, только теперь он будет относится к классу `Aggregation`).
  Паттерн Комманда был бы более уместен, если бы нужно было реализовать разные наборы вызовов методов под разные задачи (в данном случае это не так).

- Пример после:

```python
 class AggregationX:
     def __init__(self, main_table, insert_stmt):
         self.main_table = main_table
         self.insert_stmt = insert_stmt

     def execute(self) -> None:
         self.create_table()
         self.insert_into_table()

     def create_table(self):
         ...

     def insert_into_table(self):
         ...

 class AggregationY:
     def __init__(self, main_table, insert_stmt):
         self.main_table = main_table
         self.insert_stmt = insert_stmt

     def execute(self) -> None:
         self.create_mat_view_1(self)
         self.create_mat_view_2(self)
         self.insert_into_table(self)
         self.insert_into_table(self)

     def create_mat_view_1(self):
         ...

     def create_mat_view_2(self):
         ...

     def insert_into_table(self):
         ...
```

- Результат:
  
  Упростили логику выполнения программы, уменьшили количество классов, не используя паттерн ради наличия паттерна.

## Общие выводы

Заметил, что во многих случаях плохого кода, проблемы, вызываемые затрагивают сразу несколько категорий ошибок, изучаемых в приложении.
Например, если класс слишком большой, значит он реализует методы, которые более подходят другому классу. Также возможно значит, что
этот другой класс выполняет слишком **мало**. Также нарушения SRP часто связаны с бОльшей связанностью кода, когда например внутри метода создается инстанс друого класса.
В целом соблюдение общих принципов (вроде **SOLID**) позволяет не допускать сразу множества проблем, рассмотренных в упражнении.
