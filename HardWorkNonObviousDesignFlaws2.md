## Пример 1
### Изменения
#### было
Имеется программа для обращения в базу данных и выдачу предупреждений о том, что имеется некоторая проблема, требующая внимания.
В целом предполагается следующее:
- Частые обращения в БД.
- Обработка ответа.
- Если проблема обнаружена, нужно сообщить клиенту.
- Чтобы сообщение об ошибке не отправлялось постоянно, задается некоторая задержка.
```python
class AlertSystem:
    def __init__(self, slack_webhook_url, initial_alert_delay):
        self.database_connection = DB(DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME)
        self.slack_webhook_url = slack_webhook_url
        self.initial_alert_delay = initial_alert_delay
        self.alert_trackers = {}

    def check_time_diff(self):
"""
Вот здесь метод реализовывал единственный алерт, при добавлении новых пришлось бы расширять класс.
"""
class DB:
	...
	def select_last_raw_updates():
		...
"""
Внутри класса, который отвечает за подключение к БД почему-то содержался метод, который выполнял конкретный запрос для Алерта выше. Однако этот класс должен отвечать только за подключение, а решать какая именно информация нужна следует в конкретном Алерте.
"""
```

#### стало
Весь дизайн следует значительно изменить, чтобы он стал более модульным.
```python
# -----------Модуль AlertSystem---------------------
class AlertSystem:
	"""Класс ответственнен только за запуск мониторингов"""
    def __init__(self, monitorings: List[Monitoring]) -> None:
        self.monitorings = monitorings
        self.initial_alert_delay = ALERT_TIME_INITIAL_DELAY

    def run_monitorings(self) -> None:
        for m in self.monitorings:
            m.run()


# -----------Модуль DB---------------------
class DB(ABC):
    def __init__(self, db_user, db_passwd, db_host, db_port, db_name) -> None:
        dsn = self.get_connection_dsn(db_user, db_passwd, db_host, db_port, db_name)
        self.engine = self.get_engine(dsn)

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
    def get_session(self) -> Generator[Session, None, None]:
        with Session(self.engine) as session:
            yield session

"""
Переопределяем методы для получения строки подключения к БД
"""
class PostgresqlDB(DB):
    @staticmethod
    def get_connection_dsn(
	     db_user,
		 db_passwd,
		 db_host,
		 db_port,
		 db_name
	) -> str:
	pass

class ClickhouseDB(DB):
    @staticmethod
    def get_connection_dsn(
	     db_user,
		 db_passwd,
		 db_host,
		 db_port,
		 db_name
	) -> str:
	pass        

# -----------Модуль Clients---------------------
"""
Аналогично здесь, отправка сообщений это также отдельный компонент и реализуется независимо от получения и обработки данных
"""
class Client(ABC):
    def __init__(self, **kwargs) -> None:
        pass

    @abstractmethod
    def send_message(self, alert_message: str) -> None:
        pass

class SlackWebhookClient(Client):
	...

class EmailClient(Client):
	...
```

### Границы и способ их задания
В данном случае итоговый интерфейс программы значительно изменился, так как изменились задачи классов. Новый интерфейс описан в `README.md` файле.
```markdown
# Система Алертов данных в БД

## Структура
- `class AlertSystem`
	- отвечает за запуск Алертов, не требуется изменять при добавлении нововведений.
 
- Модуль `Alerts`
	- Отвечает за конкретные алерты.
	- Унаследуйте новый класс BaseAlert
	- Укажите запрос к БД в атрибуте `query`
	- Переопределите метод eval_data для оценки получаемых данных
 
- Модуль `DB`
	- Отвечает подключения к различным БД (сессии, выполнение запросов и т.д.)
	- Унаследуйте новый класс BaseDB
	- Переопределите метод `get_connection_dsn` для подключения
 
- Модуль `Clients`
	- Отвечает за конечного потребителя информации.
	- Унаследуйте новый класс BaseClient
	- Переопределите метод `send_message_to_client`.

```

Так как программа в целом подверглась полностью рефакторингу, то нет нужды соотносить границы с другими элементами кода.

### Выводы
Первый вариант в лучшем случае можно было назвать прототипным, т.к. он поддерживал ровно одну задачу.
При внесении любых изменений пришлось бы значительно изменять всю программу.
После рефакторинга за счет модульности программы можно легко добавлять новые подключения к БД, новые Алерты и новых клиентов для получения сообщений.
Текущий вариант обеспечивает возможность легко добавлять новый функционал, не трогая прежний код.

---
## Пример 2
### Изменения
Имеется класс для безопасного копирования / удаления файлов на удаленный сервер.
Все подобные операции должны заканчиваться  закрытием `SCP` соединения.
Поэтому было бы очень логично с точки зрения дизайна, что из такого класса можно сделать контекстный менеджер.
#### было
```python
class ScpFileSender:
    def __init__(self, report_writer: ReportWriter, server_path: str) -> None:
        ssh = SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(AutoAddPolicy)
        ssh.connect(
            hostname=NGINX_HOST,
            username=NGINX_USERNAME,
            password=NGINX_PASSWORD,
        )
        self.scp = SCPClient(ssh.get_transport())
        self.report_writer = report_writer
        self.server_path = server_path

    def remove_sent_files(self) -> None:
        for file_name in self.report_writer.files_list:
            try:
                os.remove(file_name)
            except FileNotFoundError:
				log.warning("File not existing")
			finally:
		        self.scp.close()
			

    def send_all_files(self) -> None:
        for file_name in self.report_writer.files_list:
            start = time.time()
            file_path = self.server_path + file_name
            try:
	            self.scp.put(file_name, file_path)
            except Exception as e:
				log.error(e)
			finally:
	            end = time.time()
	            log.info(
	                f"Upload: file {file_name} to {self.server_path}, \
	                    time spent: {round(end - start)}"
	            )
			        self.scp.close()
```

#### стало
```python
class ScpFileSender:
    def __init__(self, report_writer: ReportWriter, server_path: str) -> None:
        ssh = SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(AutoAddPolicy)
        ssh.connect(
            hostname=NGINX_HOST,
            username=NGINX_USERNAME,
            password=NGINX_PASSWORD,
        )
        self.scp = SCPClient(ssh.get_transport())
        self.report_writer = report_writer
        self.server_path = server_path

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb) -> None:
        self.scp.close()

    def remove_sent_files(self) -> None:
        for file_name in self.report_writer.files_list:
            try:
                os.remove(file_name)
            except FileNotFoundError:
				log.warning("File not existing")

    def send_all_files(self) -> None:
        for file_name in self.report_writer.files_list:
            start = time.time()
            file_path = self.server_path + file_name
            self.scp.put(file_name, file_path)
            end = time.time()
            log.info(
                f"Upload: file {file_name} to {self.server_path}, \
                    time spent: {round(end - start)}"
            )
```


### Границы и способ их задания
- Интерфейс все-таки изменился, нужно было найти все места в программе, которые используют класс `ScpFileSender` и инициализировать его как контекстный менеджер
```python
with ScpFileSender(report_writer, server_path="/var/www/reports/") as sender:
	sender.send_all_files()
	sender.remove_sent_files()
```
- Однако помимо того, что класс должен использоваться с `with` в остальном интерфейс остался прежним.
- Роль класса и его взаимоотношения с другими частями программы остались неизменными.
- Класс вызывается непосредственно в месте, где происходит передача данных по сети.

### Тесты (use cases)
Убеждаемся, что код действительно отправляет файлы с помощью mock-объектов (#TODO возможно нужно переписать тесты, т.е. по сути реальная передача не проверяется, только то что вызываются нужные методы).

```python
class TestScpFileSender(unittest.TestCase):

    def setUp(self):
        self.mock_report_writer = Mock()
        self.mock_report_writer.files_list = ["file1.txt", "file2.txt", "file3.txt"]
        self.mock_ssh = Mock()
        self.mock_ssh.get_transport.return_value = "dummy_transport"

    def test_init(self):
        with patch("SSHClient", return_value=self.mock_ssh):
            sender = ScpFileSender(self.mock_report_writer, "/remote/server/path/")
        self.assertEqual(sender.report_writer, self.mock_report_writer)
        self.assertEqual(sender.server_path, "/remote/server/path/")

    def test_remove_sent_files(self):
        sender = ScpFileSender(self.mock_report_writer, "/remote/server/path/")
        with patch("os.remove") as mock_remove:
            sender.remove_sent_files()
        self.assertEqual(mock_remove.call_count, 3)

    def test_send_all_files(self):
        sender = ScpFileSender(self.mock_report_writer, "/remote/server/path/")
        sender.scp = Mock()
        with patch("time.time", side_effect=[100, 200, 300]):
            sender.send_all_files()
        self.assertEqual(sender.scp.put.call_count, 3)
```

#### Выводы
Такое изменение позволило сделать код немного более компактным. 
Но главное - теперь класс полностью отвечает своей роли, как инструмент для захватывания, использования и затем освобождения некоторого ресурса.

---
## Пример 3
### Изменения
Имелась программа, в которой задается конфиг для ежедневного обслуживания процессов в БД. (Создание агрегаций по данныхм, обновления материализованных вью и т.п.). 
При запуске всех процессов последовательно теряется много времени. 

Нужно было, чтобы часть процессов запускалась параллельно.
Для этого можно было бы создать наследника класса `Stage`, который бы переопределял метод `execute_stage` и дополнительно имел бы приватный метод, который создает корутины для одновременного выполнения.
(я надесь, что введение приватного метода для наследника класса не считается нарушением его интерфейса :)).
```python
class AsyncStage(Stage):
    def __init__(
        self,
        name: str,
        commands: List[str],
        engine,
        date,
    ) -> None:
        self.name = name
        self.engine = engine
        self.fabric = TaskFabric
        self.visitor_cls = TaskProcessVisitor
        self.tasks: List[Task] = self.fabric.get_task_object_list(commands, engine, date)

    async def __prepare_stage(self) -> None:
        async_click_engine = self.engine
        coroutines: List[Awaitable] = []
        # Создаем Посетителя
        visitor = self.visitor_cls()
        for task in self.tasks:
            coro = task.accept(visitor)
            coroutines.append(coro)
        # Await all the coroutines concurrently
        await asyncio.gather(*coroutines)
        try:
            await async_click_engine.dispose()  # type: ignore
        except Exception as e:
            log.warning(e)
            pass

    def execute_stage(self) -> None:
        # Run the async function
        asyncio.run(self.__prepare_coroutines())

```

Также изменили способ парсинга конфигурационного файла, так как теперь он принимает не конкретную задачу, но на каждую стадию - лист из одной задачи ИЛИ лист из нескольких задач, которые должны обрабатываться как корутины.
```python
class TaskConfig(BaseModel): 
	stage: str
	tasks: List[TaskEnum]

class TasksConfig(BaseModel): 
	stages: List[TaskConfig]

class ConfigParserYAML:
    def __init__(self, config_file: str = "config.yaml") -> None:
        self.config = None
        self.stages = None
        self.dates = None

        config_file_path = os.path.abspath(config_file)
        log.info(config_file_path)
        try:
            with open(config_file_path, "r") as configfile:
                parsed_yaml = yaml.safe_load(configfile)
        except FileNotFoundError:
            log.error("Config file not found")
            sys.exit(-1)
        self.config = TasksConfig(**parsed_yaml)
```

#### Границы и способ их задания
- Изменилось взаимодействие с конечным пользователем (человеком, который задает конфигурационный файл), т.к структурно изменился формат файла. Тогда вероятно достаточно добавить новый формат в документацию:
```yaml
# Образец конфигурационного файла
date_range: 
  - 2023-04-25
  - 2023-04-30
stages:
  - stage: Агрегация 1 search
    tasks: 
    - search_aggregation_ru
    - search_aggregation_en
    
  - stage: Агрегация 1 main
    tasks:
    - aggregation_ru_1
    - aggregation_ru_2

  - stage: Агрегация 2 main
    tasks:
    - aggregation_en_1
    - aggregation_en_2

```
- Удалось оставить без изменений интерфейс внутри программы.
	- Интерфейс модуля `ConfigParser` остался неизменным (все также открывается и парсится файл), методы все те же.
	 - Интерфейс модуля `Processor` также не изменился, так как он просто запускает процессы обработки. Что 'внутри' у этих процессов вне его зоны ответственности. Т.е. этому модулю просто 'подсунули' обработку нескольких корутин вместо одного процесса.
	 - Добавился только отдельный модуль, который упаковывает процессы в корутины в классе `Stage`.

#### Тесты (use cases)

Для тестирования измененного скрипта для работы с БД, при помощи `pytest` и shell скрипта с `docker`ом в контейнере разворачивается полноценная база данных со всеми используемыми таблицами.
Естественно, в процессе тестирования таблицы будут пустые (их слишком много наверное, чтобы заполнять тествыми данными), однако проверяется, что все исполняемые запросы адекватны структуре таблиц и не вызывают ошибок.
Теперь при добавлении нового функционала в виде отчетов или мониторингов для базы данных я всегда могу быть уверен, что хотя бы на уровне таблицы, колонок и типов данных они всегда будут адекватными.

```python
class TestExecuteQueryWithTmpTables:
    @pytest.fixture(autouse=True)
    def tmp_tables(self):
        dsn = "clickhouse://username:password@clickhouse:8123/db1"
        engine = create_engine(dsn)
        metadata = MetaData(engine)
        category_update.metadata = metadata
        category_update_ru.metadata = metadata
        categories_postres.metadata = metadata
        darkstore_postres.metadata = metadata
        categories_postres.engine = MergeTree(
            order_by=(categories_postres.c.category_tree_id),
        )
        darkstore_postres.engine = MergeTree(
            order_by=(darkstore_postres.c.darkstore_id),
        )
        try:
            category_update.create()
            category_update_ru.create()
            categories_postres.create()
            darkstore_postres.create()
        except Exception as e:
            if "already exists" in str(e):
                pass
        yield
        category_update.drop()
        category_update_ru.drop()
        categories_postres.drop()
        darkstore_postres.drop()

class MockStage:
    def __init__(
        self,
        name: str,
        commands: List[str],
        config: ProcessConfig,
    ) -> None:
        self.name = name
        self.config = config
        self.fabric = MockFabric(commands, config)
        self.tasks: List[Task] = self.fabric.task_obj
        self.visitor_cls = FakeVisitor


class TaskExample:
    def __init__(self, config: ProcessConfig) -> None:
        self.config = config
        self.engine = config.get_click_async_engine()

    def accept(self, visitor: FakeVisitor) -> Awaitable:
        return visitor.visit_test(self)

    async def execute_test_query(self) -> None:
        async with make_session(self.engine, is_async=True) as asession:
            query = text("INSERT INTO delete_me (id, name) VALUES(:id, :name)")
            result = await asession.execute(query, {"id": 1, "name": "kek"})
            print(result)


class TestAsyncInsertQuery:
    @pytest.fixture
    def process_config(self):
        p_config = MagicMock()
        p_config.get_click_async_dsn.return_value = (
            "clickhouse+asynch://username:password@clickhouse:9000/db1"
        )
        p_config.get_click_async_engine.return_value = create_async_engine(
            "clickhouse+asynch://username:password@clickhouse:9000/db1"
        )
        yield p_config

    @pytest.fixture(autouse=True)
    def create_tmp_table(self):
        engine = create_engine("clickhouse://username:password@clickhouse:8123/db1")
        with make_session(engine) as session:
            session.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS delete_me(id UInt16, name String)"
                    "ENGINE = MergeTree() ORDER BY (id)"
                )
            )
            yield
            session.execute(text("DROP TABLE delete_me"))

    @patch(
        "client_worker.stage.Stage.__init__",
        new=MockStage.__init__,
    )
    def test_async_process(self, process_config):
        tasks1 = ["task", "task", "task"]
        tasks2 = ["task", "task", "task"]
        tasks_dict = {"stage1": tasks1, "stage2": tasks2}
        processor = Processor(tasks_dict, process_config)
        processor.process_stages()
```
#### Выводы
Таким образом, удалось таким образом сделать процесс для взаимодействия с БД лучше, при этом в конкретном случае изменение не затронуло интерфейс программы в целом и не пришлось вносить изменение в реализацию других компонентов программы.
Надеюсь, это является признаком того, что в целом изначальный дизайн программы был в целом правильным, т.к. внесение изменений получилось очень локальным.

## Общие выводы
Теперь что-то вроде бы выстраивается в моей голове насчет подхода к написанию программ.
- Дизайн интерфейса возможно самое важное при создании программы, что что в последствии меньше всего должно подвергаться изменениям.
- Программы должны быть максимально компонентными, чтобы можно было внести даже значительные изменения при необходимости, при этом не изменяя интерфейс.
- При выполнений условий выше, можно не опасаться внесения изменений, если это приводит к улучшению общего дизайна, делает программу проще, более читабельной и пригодной для внесения изменений. (тут вспоминается занятие по TDD, где мы переписывали программу каждый раз, когда тесты не проходили).