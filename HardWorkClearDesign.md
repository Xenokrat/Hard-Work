# Hard Work | Clear Design

## Первая попытка

### Начальная версия

> Код не мой :), хотя есть вероятность, что скоро будет мой.
> Скрипт запускается, выгружает из базы данных картинки с ссылками URL
> Обращается к Google API для распознавания изображения на картиках, записывает их в базу данных
```python
# main.py
import time

from config import *
from db import database_connection, get_banner_picture_url
from banner_detector import BannerDetector

if __name__ == '__main__':
    while 1:
        # берем все адреса картинок баннеров если processed == False
        # изображения баннеров которые еще не были распознаны.
        try:
            with database_connection.get_connection() as connection:
                with connection.begin():
                    banner_picture_urls = connection.execute(get_banner_picture_url()).fetchall()
                    log.info(f'Got 50 records from a table banner')
        except:
            continue

        count_detect_logos = 0
        count_detect_text = 0

        for banner_id_pict_url in banner_picture_urls:
            banner_detector = None
            try:
                banner_id, banner_pict_url = banner_id_pict_url
                banner_detector = BannerDetector(banner_id, banner_pict_url)
                if banner_pict_url:
                    banner_detector.detect_logos_uri()
                    banner_detector.detect_text()
                    count_detect_logos += 1 if banner_detector.logos_array else 0
                    count_detect_text += 1 if banner_detector.text_banner_array else 0
                banner_detector.update_to_db()
            except Exception as ex:
                log.error(str(ex)[:100])
            finally:
                if banner_detector:
                    del banner_detector

        log.info('50 banners viewed. \n'
                 f'Recorded: logos - {count_detect_logos}, '
                 f'text from banner image - {count_detect_text}')

        if len(banner_picture_urls) < 50:
            # ждем 12 часов
            time.sleep(43200)
```
```python
# banner_detector.py
from db import update_banner
from config import *
import time

from google.cloud import vision
from db import database_connection


class BannerDetector:
    """Распознает логотип и текст с картинки баннера,
    обновляет запись в БД.
    """

    def __init__(self, banner_id, banner_picture_url):
        self.banner_id = banner_id
        self.current_banner_picture_url = banner_picture_url
        self.client = vision.ImageAnnotatorClient()
        self.image = vision.Image()
        self.logos_array = []
        self.text_banner_array = []
        self.url_access_error = False
        log.info(f'banner_id:{self.banner_id}, '
                f' banner_picture_url: {self.current_banner_picture_url}')

    def detect_logos_uri(self):
        """Распознает название логотипов на картинке."""
        self.image.source.image_uri = self.current_banner_picture_url
        for i in range(0, 3):
            try:
                response = self.client.logo_detection(image=self.image)
                logos = response.logo_annotations
                for logo in logos:
                    self.logos_array.append(logo.description)
                if response.error.message:
                    # если у нас возникает ошибка доступа по ссылке, то данные не обновляем
                    if 'We can not access the URL currently' in response.error.message and i == 2:
                        self.url_access_error = True
                    raise Exception(
                        f'Failed to recognize logos. {response.error.message}')
            except Exception as ex:
                log.error(str(ex)[:100])
                time.sleep(1)
                continue
            break

    def detect_text(self):
        """Распознает текст на картинке баннера."""
        self.image.source.image_uri = self.current_banner_picture_url

        for i in range(0, 3):
            try:
                response = self.client.text_detection(image=self.image)
                texts = response.text_annotations
                for text in texts[1:]:
                    self.text_banner_array.append(text.description)
                if response.error.message:
                    if response.error.message:
                        # если у нас возникает ошибка доступа по ссылке, то данные не обновляем
                        if 'We can not access the URL currently' in response.error.message and i == 2:
                            self.url_access_error = True
                    raise Exception(
                        f'Failed to recognize text. {response.error.message}')
            except Exception as ex:
                log.error(str(ex)[:100])
                time.sleep(1)
                continue
            break

    def update_to_db(self):
        """Обновляет записи в таблице banner."""
        if not self.url_access_error:
            with database_connection.get_connection() as connection:
                with connection.begin():
                    connection.execute(update_banner(self.banner_id,
                                                    self.logos_array, self.text_banner_array)
                                    )
                    log.info(f'Database entry banner_id:{self.banner_id} updated. \n'
                            f'logos: {self.logos_array}. \n'
                            f'text from banner image: {self.text_banner_array}.')
```
```python
# db.py
from contextlib import contextmanager
from config import *

from food_retail_app_parcer_db.food_retail_app_parcer import banner, sa


class DB:
    """Класс для подключения и работы с БД."""

    def __init__(self, db_user, db_passwd, db_host, db_port, db_name):
        dsn = self.get_connection_dsn(db_user, db_passwd, db_host,
                                    db_port, db_name)
        self.engine = self.get_engine(dsn)

    @staticmethod
    def get_connection_dsn(db_user, db_passwd, db_host, db_port, db_name):
        return f'postgresql://{db_user}:{db_passwd}@{db_host}:{db_port}' \
            f'/{db_name}'

    @staticmethod
    def get_engine(dsn):
        return sa.create_engine(dsn, connect_args={'connect_timeout': 60})

    @contextmanager
    def get_connection(self):
        with self.engine.connect() as connection:
            yield connection

def get_banner_picture_url():
    """Запрос на получение 50-и необработанных записей."""
    query = (sa.select([banner.c.banner_id, banner.c.banner_picture_url])
        .where(banner.c.processed == False).limit(50))
    return query


def update_banner(banner_id, logo_banner, picture_banner_text):
    """Запрос на обновление записей таблицы banner.
    Если были получены логотипы или текст с картинки баннера,
    то обновляются поля для логотипов и/или для текста с картинки баннера,
    устанавливается processed=True.
    Если не было ссылки в БД, то устанавливает processed=True.
    """
    if logo_banner and picture_banner_text:
        values = {'logo_banner':logo_banner,
                'picture_banner_text': picture_banner_text,
                'processed': True}
    elif logo_banner:
        values = {'logo_banner': logo_banner,
                'processed': True}
    elif picture_banner_text:
        values = {'picture_banner_text': picture_banner_text,
                'processed': True}
    else:
        values = {'processed': True}

    query = (banner
            .update()
            .values(values)
            .where(banner.c.banner_id == banner_id))
    return query

# Коннект к базе
database_connection = DB(DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME)
```

### Словесное описание дизайна

**Текущее Тело скрипта**
- Пока в БД существуют необработанные строки (processed = False)
- Если строк больше 50 (_параметризовать_) выгружаем данные ИНАЧЕ засыпаем на 12 часов (_параметризовать_).
- Проходимся по необработанным строкам циклом
    - Для каждой строки создается класс banner_detector.
    - Пытаемся распознать методами класса на картинках логотипы | текст.
        - banner_detector.detect_logos_uri()
        - banner_detector.detect_text()
        - Note: все методы обращения к API выполняются по 3 раза, стоит (_параметризовать_).
    - Если что-то есть, записываем в БД.


### Исправления

**2. Попробуем записать в более декларативном стиле:**

2.1 К чему стремимся - максимально простой запуск main функции
Объявляем подключение в базе данных.
Отдельный класс запускает весь процесс обновления.

2.2 Нужен класс, в ответственности которого только "крутить" цикл обновления
также этот класс при необходимости параметризует настройки выполнения
для этого создадим абстрактный класс Proccessor.

2.3 Пусть выполнение запроса будет в ведении класса DB вместо BannerDetector
 так удасться сократить использование контекстных менеджеров

2.4 Вся работа с базой данных, в том числе и апдейты в таблицу -- 
должны находиться только в ведении класса DB.



#### 2.1

```python
def main() -> None:
    database_connection = DB(DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME)
    processor = BannerProccessor(database_connection)
    processor.run_cycle()
```

#### 2.2

```python
@dataclass
class Proccessor(ABC):
    database: DB
    BATCH_SIZE: int = 50
    TIME_SLEEP_SEC: int = 43200
    RETRIES_POLICY: int = 3

    def run_cycle(self) -> None:
        while True:
            if not self.run_batch_proccess():
                time.sleep(self.TIME_SLEEP_SEC)
                continue

    @abstractmethod
    def run_batch_proccess(self) -> bool:
        pass

    def get_batch_data(self) -> List[Tuple[Any, ...]]:
        return self.database.execute_select_query(get_banner_query(self.BATCH_SIZE))

    def is_batch_size_enough(self, batch_data: List[Tuple[Any, ...]]) -> bool:
        return len(batch_data) >= self.BATCH_SIZE
```
Реализация под конкретную задачу с баннерами:

```python
class BannerProccessor(Proccessor):

    def run_batch_proccess(self) -> bool:
        batch_data = self.get_batch_data()

        if not self.is_batch_size_enough(batch_data):
            return False

        banner_detector = BannerDetector(batch_data, self.RETRIES_POLICY)
        banner_detector.detect_all()

        for banner_id, logo_banner in banner_detector.logos_array:
            self.database.execute_update_query(
                update_banner_query(banner_id, logo_banner)
            )

        for banner_id, text_banner in banner_detector.text_banner_array:
            self.database.execute_update_query(
                update_banner_query(banner_id, text_banner)
            )

        log.info(
            "50 banners viewed.\n"
            f"Recorded: logos - {banner_detector.count_detect_logos}, "
            f"text from banner image - {banner_detector.count_detect_text}"
        )
        return True
```

#### 2.3 TODO: вероятно методы detect* нужно еще рефакторить

```python
class BannerDetector:
    """Распознает логотип и текст с картинки баннера,
    обновляет запись в БД.
    """

    def __init__(
        self,
        banner_data: List[Tuple[Any, ...]],
        retries_policy: int,
    ) -> None:
        self.banner_data = banner_data
        self.RETRIES_POLICY = 3
        self.client = vision.ImageAnnotatorClient()
        self.image = vision.Image()
        self.count_detect_logos = 0
        self.count_detect_text = 0
        self.logos_array: List[Tuple[int, List[str]]] = []
        self.text_banner_array: List[Tuple[int, List[str]]] = []
        log.info("recived batch of 50 banners")

    def detect_all(self) -> None:
        for banner_id, banner_picture_url in self.banner_data:
            self.logos_array.append(
                self.detect_logos_url(banner_id, banner_picture_url)
            )
            self.text_banner_array.append(
                self.detect_text(banner_id, banner_picture_url)
            )

    def detect_logos_url(
        self, banner_id: int, banner_picture_url: str
    ) -> Tuple[int, List[str]]:
        """Распознает название логотипов на картинке."""
        self.image.source.image_uri = banner_picture_url
        for i in range(self.RETRIES_POLICY):
            try:
                response = self.client.logo_detection(image=self.image)
                logos = response.logo_annotations
                res: List[str] = []
                for logo in logos:
                    res.append(logo.description)
                if (
                    "We can not access the URL currently" in response.error.message
                    and i == 2
                ):
                    # если у нас возникает ошибка доступа по ссылке,
                    # то данные не обновляем
                    raise Exception(
                        f"Failed to recognize logos. {response.error.message}"
                    )
            except Exception as ex:
                log.error(str(ex)[:100])
                time.sleep(1)
                continue
        return (banner_id, res)

    def detect_text(
        self, banner_id: int, banner_picture_url: str
    ) -> Tuple[int, List[str]]:
        """Распознает текст на картинке баннера."""
        self.image.source.image_uri = banner_picture_url
        for i in range(self.RETRIES_POLICY):
            try:
                response = self.client.text_detection(image=self.image)
                texts = response.text_annotations
                res: List[str] = []
                for text in texts[1:]:
                    res.append(text.description)
                if (
                    "We can not access the URL currently" in response.error.message
                    and i == 2
                ):
                    # если у нас возникает ошибка доступа по ссылке,
                    # то данные не обновляем
                    raise Exception(
                        f"Failed to recognize logos. {response.error.message}"
                    )
            except Exception as ex:
                log.error(str(ex)[:100])
                time.sleep(1)
                continue
        return (banner_id, res)
```


#### 2.4

```python
from contextlib import contextmanager
from typing import Any, List, Tuple

from food_retail_app_parcer_db.food_retail_app_parcer import (  # type: ignore
    banner, sa)
from sqlalchemy.sql import Select, Update  # type: ignore


class DB:
    """Класс для подключения и работы с БД."""

    def __init__(self, db_user, db_passwd, db_host, db_port, db_name):
        dsn = self.get_connection_dsn(db_user, db_passwd, db_host, db_port, db_name)
        self.engine = self.get_engine(dsn)

    @staticmethod
    def get_connection_dsn(db_user, db_passwd, db_host, db_port, db_name):
        return f"postgresql://{db_user}:{db_passwd}@{db_host}:{db_port}" f"/{db_name}"

    @staticmethod
    def get_engine(dsn):
        return sa.create_engine(dsn, connect_args={"connect_timeout": 60})

    @contextmanager
    def get_connection(self):
        with self.engine.connect() as connection:
            yield connection

    def execute_select_query(
        self,
        query: Select,
    ) -> List[Tuple[Any, ...]]:
        with self.get_connection() as conn:
            return conn.execute(query)

    def execute_update_query(
        self,
        query: Update,
    ) -> None:
        with self.get_connection() as conn:
            conn.execute(query)
            conn.commit()


def get_banner_query(batch_size: int) -> Select:
    """Запрос на получение 50-и необработанных записей."""
    return (
        sa.select([banner.c.banner_id, banner.c.banner_picture_url])
        .where(banner.c.processed is False)
        .limit(batch_size)
    )


def update_banner_query(
    banner_id,
    logo_banner=None,
    picture_banner_text=None,
) -> Update:
    values = {"processed": True}
    if logo_banner:
        values["logo_banner"] = logo_banner
    if picture_banner_text:
        values["picture_banner_text"] = picture_banner_text

    query = banner.update().values(values).where(banner.c.banner_id == banner_id)
    return query
```

### Выводы

Ушло 4 часа на корректировку дизайна, теперь функция main() выглядит более ясной.
При необходимости можно скорректировать запуск main() с другими параметрами, или другими классами Proccessor.
Разделение ответственности между классами более прозрачное.
Управление контекстом подключения к базе только в рамках класса DB.
Меньше вложенных контекстных менеджеров и циклов.
~~удалить Я убил слишком много времени здесь, упс~~.


## Вторая попытка

### Начальная версия

> Код реализует некоторую логику для клиента, в данном случае:
> 1. Выгрузка данных из одной базы Postgresql.
> 1.1 Опционально, какая-то логика обработки данных внутри
> 2. Перенос в другую (клиентскую) базу данных Postgresql.
```python
from client_uploader import Client1Uploader


__name__ == '__main__':
 # обновление данных в базе Client1
    client1 = Client1Uploader()
    client1.get_data()
    client1.insert_data()
```

```python
import time
import psycopg2
import pandas as pd
import psycopg2.extras as extras
from config import *
from client1_db import *


class Client1Uploader:
  def __init__(self):
      self.shelf_data = None
      self.search_data = None
      self.banner_data = None

  def get_data(self):
      conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
      cursor = conn.cursor()

      start = time.time()
      cursor.execute(get_eshelf_daily_query())
      self.shelf_data = pd.DataFrame(cursor.fetchall())
      end = time.time()
      log.info(f'Read: shelf_data, time spent: {round(end - start)}')

      start = time.time()
      cursor.execute(get_search_daily_query())
      self.search_data = pd.DataFrame(cursor.fetchall())
      end = time.time()
      log.info(f'Read: search_data, time spent: {round(end - start)}')

      start = time.time()
      cursor.execute(get_banner_daily_query())
      self.banner_data = pd.DataFrame(cursor.fetchall())
      end = time.time()
      log.info(f'Read: banner_data, time spent: {round(end - start)}')

      cursor.close()
      conn.commit()
      conn.close()

  def insert_banner_data(self):
      start = time.time()
      conn = psycopg2.connect(dbname=CLIENT1_DB_NAME, user=CLIENT_DB_USER, password=CLIENT_DB_PASSWORD,
                              host=CLIENT_DB_HOST, port=CLIENT_DB_PORT)
      cursor = conn.cursor()
      banner_insert_query = get_insertion_query(
          "table",
          "column1, column2, column3"
      )

      tuples = [tuple(x) for x in self.banner_data.to_numpy()]
      extras.execute_values(cursor, banner_insert_query, tuples)
      cursor.close()
      conn.commit()
      conn.close()
      end = time.time()

      log.info(f'Write: banner_data [Client1], time spent: {round(end - start)}')

  def insert_search_data(self):
      start = time.time()
      conn = psycopg2.connect(dbname=CLIENT1_DB_NAME, user=CLIENT_DB_USER, password=CLIENT_DB_PASSWORD,
                              host=CLIENT_DB_HOST, port=CLIENT_DB_PORT)
      cursor = conn.cursor()
      search_insert_query = get_insertion_query(
          "table",
          "column1, column2, column3"

      )

      tuples = [tuple(x) for x in self.search_data.to_numpy()]
      extras.execute_values(cursor, search_insert_query, tuples)
      cursor.close()
      conn.commit()
      conn.close()
      end = time.time()

      log.info(f'Write: search_data [Client1], time spent: {round(end - start)}')

  def insert_shelf_data(self):
      start = time.time()
      conn = psycopg2.connect(dbname=CLIENT1_DB_NAME, user=CLIENT_DB_USER, password=CLIENT_DB_PASSWORD,
                              host=CLIENT_DB_HOST, port=CLIENT_DB_PORT)
      cursor = conn.cursor()
      eshelf_insert_query = get_insertion_query(
          "table",
          "column1, column2, column3"
      )

      tuples = [tuple(x) for x in self.shelf_data.to_numpy()]
      extras.execute_values(cursor, eshelf_insert_query, tuples)
      cursor.close()
      conn.commit()
      conn.close()
      end = time.time()

      log.info(f'Write: shelf_data [Client1], time spent: {round(end - start)}')

  def insert_data(self):
      self.insert_banner_data()
      self.insert_search_data()
      self.insert_shelf_data()
```
```python
def get_insertion_query(table: str, columns: str) -> str:
 return f"""
     INSERT INTO {table}({columns}) VALUES %s
 """


 def get_eshelf_daily_query() -> str:
     return f"""
     SOME RAW SQL
     """


 def get_search_daily_query() -> str:
     return f"""
     SOME RAW SQL
     """


 def get_banner_daily_query() -> str:
     return f"""
     SOME RAW SQL
     """
```

### Словесное описание дизайна

**Текущее Тело скрипта.**
- Запускается функция main().
- Создается экземпляр класса обработки под Клиента1.
- Запрашиваются в одном методе get_data() все данные, релевантные для клиента.
- Данные записываются в атрибуты класса Client как DataFrame
- Отдельно вызываются методы для вставки в клиентскую базу данных.

### Исправления

**Что плохо?**

  1.1 Данные получаются сразу для всех отчетов одновремменно, и "ждут" в памяти пока не выгрузится все.

  1.2 Нет возможности загружать конкретые отчеты по отдельности, т.к. get_data запрашивает сразу все, нет модульности.

  1.3 Все методы вставки сами создают коннекшн к клиентской базе, что неправильно, за подключение должен отвечать отдельный класс.

2.1 Добавим класс **Database**. В его ответственности:
- Вся работа с базой данных: создание подключения, выполнение запросов, закрытие подключения.

2.2 Добавим класс **DataTransfer**. В его ответственности:
- Принимаем подключение к нашей БД.
- Принимаем класс отчета.
- Принимаем подключение к клиентской БД.

2.3 Добавим класс **ReportData**. В его ответственности:
- Получить данные от DataTransfer.
- Вызвать метод make_report(), отдать данные.

3. Итоговая схема:
3.1 Создается экземпляр Database для собственной БД.
3.2 Создается экземпляр Database БД клиента.
3.3 Создается экземпляры Report с реализацией конкрентых отчетов. 
3.4 Создается экземпляр DataTransfer.
-> Принимает подключения.
-> Обрабатывает все Report.


#### 2.1

```python
# По большей части позаимствовал из предыдущего примера
class Database(ABC):
   def __init__(self, db_user, db_passwd, db_host, db_port, db_name):
       dsn = self.get_connection_dsn(db_user, db_passwd, db_host, db_port, db_name)
       self.engine = self.get_engine(dsn)

   @staticmethod
   @abstractmethod
   def get_connection_dsn(db_user, db_passwd, db_host, db_port, db_name):
       pass

   @staticmethod
   def get_engine(dsn):
       return sa.create_engine(dsn, connect_args={"connect_timeout": 60})

   @contextmanager
   def get_connection(self):
       with self.engine.connect() as connection:
           yield connection

   def execute_select_query(
       self,
       query: Select,
   ) -> Optional[List[Tuple[Any, ...]]]:
       try:
           with self.get_connection() as conn:
               return conn.execute(query)
       except Exception as ex:
           log.error(str(ex)[:100])
       return None

   def execute_update_query(
       self,
       query: Update,
   ) -> bool:
       try:
           with self.get_connection() as conn:
               conn.execute(query)
               conn.commit()
       except Exception as ex:
           log.error(str(ex)[:100])
           return False
       return True

class PostgresqlDB(Database):
   def get_connection_dsn(db_user, db_passwd, db_host, db_port, db_name):
       return f"postgresql://{db_user}:{db_passwd}@{db_host}:{db_port}" f"/{db_name}"
```

#### 2.2

```python
class DataTransfer:
    def __init__(self, work_db: Database, client_db: Database, reports: List[Report],) -> None:
    self.work_db = work_db
    self.client_db = client_db
    self.reports = reports

    def proccess_reports(self) -> bool:
    for report in self.reports:
        report_data = work_db.execute_select_query(report.create_report_query())
        if not report_data: 
            log.error(f"Report {repr(report)} exited with error during select query")
            return False
        if not client_db.execute_update_query(report.create_update_query()):
            log.error(f"Report {repr(report)} exited with error during update query")
            return False
    return True
```

#### 2.3

```python
class Report(ABC):
   @staticmethod
   @abstractmethod
   def create_report_query() -> str:
       pass

   @staticmethod
   @abstractmethod
    def create_update_query() -> str:
       pass

class ShelfReport(Report):
    COLUMNS = "column1, column2, column3"
    TABLE = "shelf_table"

    @staticmethod
    def create_report_query() -> str:
        return f"SOME RAW SQL"

    @staticmethod
    def create_update_query() -> str:
        return f"INSERT INTO {TABLE}({COLUMNS}) VALUES %s"

class BannerReport(Report):
    COLUMNS = "column1, column2, column3"
    TABLE = "banner_table"

   @staticmethod
   def create_report_query() -> str:
       return f"SOME RAW SQL"

   @staticmethod
   def create_update_query() -> str:
       return f"INSERT INTO {TABLE}({COLUMNS}) VALUES %s"
```


#### Main

```python
def main() -> None:
    work_db = PostgresqlDB(DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME)
    client_db = PostgresqlDB(CLIENT_DB_USER, CLIENT_DB_PASSWORD, CLIENT_DB_HOST, CLIENT_DB_PORT, CLIENT_DB_NAME)
    shelf_report = ShelfReport()
    banner_report = BannerReport()

    data_transfer = DataTransfer(
        work_db=work_db,
        client_db=client_db,
        reports=[shelf_report, banner_report]
    )
    if data_transfer.proccess_reports():
        log.info("Reports successfully transfered")
        return
    log.error("Reports not formed properly")

if __name__ == "__main__":
    main()
```



### Выводы

Ушло 3 часа на корректировку дизайна, функция main() теперь более декларативна, 
формирование отчетов и передача в базу клиента изолированы друг от друга для разных типов отчетов.
Управление контекстом подключения к базе только в рамках класса DB.
Можно будет настроить более точечно логирование.
При необходимости можно будет переделать классы отчетов, чтобы они принимали параметры названий таблиц / столбцов.
