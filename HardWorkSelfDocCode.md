# Hard Work | Antipattern Self Documenting Code

## Пример 1

Класс VehicleService из проекта Автопарк на Django,
обновленный для отделения бизнес-логики. Опишем данную изоляцию структуры в "слои" в docstring класса.
```python
class VehicleService:

  """
  Сервис для взаимодействия с авто.
  Классы Service создаются с идеей изолировать взаимодействие с базой данных до единого сервиса,
  реализующейго валидации и различные методы получения данных для передачи во view.
  Для всех взаимодействий с БД используйте только классы Service, не взаимодейтсвуя с БД напрямую.
  Инициализируется на уровне view.
  Для взаимодействия с базой данных использует подклассы Repository при инициализации.
  Новые валидации добавляйте в метод _validate_and_processed_vehicle.
  """

  def __init__(self) -> None:
      self.vehicle_repository = VehicleRepository()
      self.driver_repository = DriverRepository()
      self.enterprise_repository = EnterpriseRepository()

  def get_all_vehicles(self) -> QuerySet[BetterVehicle]:
      vehicles = self.vehicle_repository.get_all_vehicles()
      map(self._validate_and_processed_vehicle, vehicles)
      return vehicles

  def get_vehicle_by_id(self, vehicle_id: int) -> BetterVehicle:
      vehicle = self.vehicle_repository.get_vehicle_by_id(vehicle_id)
      self._validate_and_processed_vehicle(vehicle)
      return vehicle

  def _validate_vehicle_driver(self, vehicle_id: int, driver_id: int) -> bool:
      vehicle = self.vehicle_repository.get_vehicle_by_id(vehicle_id)
      driver = self.driver_repository.get_driver_by_id(driver_id)
      enterprise = self.enterprise_repository.get_enterprise_by_id(vehicle.enterprise_id)

      if vehicle is None or driver is None or enterprise is None:
          return False

      return driver.enterprise_id == enterprise.id

  def _validate_reg_numbers(self, vehicle_id: int) -> bool:
      regex = "^\w*$"
      reg_number = self.vehicle_repository.get_vehicle_by_id(vehicle_id).registration_number
      if not reg_number:
          return False
      if not re.search(regex, reg_number):
          return False
      return True

  def _validate_and_processed_vehicle(self, vehicle: Optional[BetterVehicle]) -> None:
      if vehicle is None:
          return None
      if not all(
          [
              self._validate_reg_numbers(vehicle.id),
              self._validate_vehicle_driver(vehicle.driver_id, vehicle.enterprise_id),
          ]
      ):
          raise ValidationError("Not valid")
```


## Пример 2

Класс Database из прошлого примера Hard Work
Т.к. общий дизайн уже описан, перенесем сюда все что относится к использованию класса Database.
Описание в docstring:
```python
class Database(ABC):
    """
    Любые взаимодействия с базами данных использованием этого класста
    или его подкассов. Экземпляр класса передается в DataProcessor для выполнения запросов.
    Запросы для выполнения формируется в классе Report и его подклассах.

    Для добавления взаимодействия с новой БД - создать подкласс, реализующий 
    метод get_connection_dsn (требуется поддержка SQLAlchemy).

    TODO 1: реализовать методы для удаления | создания.
    IDEA 2: некоторые библиотеки реализуют другие способы взаимодействия с SQL.
    например: Pandas - pd.read_sql | pd.to_sql
    Для реализации создать подкласс (для соответствующей БД) и переопределить методы.
    """

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


## Пример 3

Класс Processor в проекте по обработке текста на изображениях.
Отвечает за размер, периодичность обработки данных.
Укажем это в описании класса в коде.
```python
class BannerProcessor(Processor):
    """
    Класс для управления обновлением данных в БД при работе с обновленем данных 
    при помощи внешнего API.

    В данном случае реализует обработку изображений на баннерах.
    Управляет размером обрабатываемы партий данных, периодом ожидания,
    Передает в обработчик количество попыток переподключения в API.

    Входной класс для всего скрипта -- для запуска создается экзепляр в main, вызывается комманда 
    run_cycle.
    """

    def __init__(
        self,
        database: DB,
        BATCH_SIZE: int = 50,
        TIME_SLEEP_SEC: int = 42600,
        RETRIES_POLICY: int = 3,
    ) -> None:
        self.database = database
        self.BATCH_SIZE = BATCH_SIZE
        self.TIME_SLEEP_SEC = TIME_SLEEP_SEC
        self.RETRIES_POLICY = RETRIES_POLICY

    def run_cycle(self) -> None:
        while True:
            if not self.run_batch_proccess():
                time.sleep(self.TIME_SLEEP_SEC)
                continue

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

        for banner_id, text_banner in banner_detector.logos_array:
            self.database.execute_update_query(
                update_banner_query(banner_id, text_banner)
            )

        log.info(
            "50 banners viewed.\n"
            f"Recorded: logos - {banner_detector.count_detect_logos}, "
            f"text from banner image - {banner_detector.count_detect_text}"
        )
        return True

    def get_batch_data(self) -> List[Tuple[Any, ...]]:
        return self.database.execute_select_query(get_banner_query(self.BATCH_SIZE))

    def is_batch_size_enough(self, batch_data: List[Tuple[Any, ...]]) -> bool:
        return len(batch_data) >= self.BATCH_SIZE
```


## Пример 4

Небольшой модуль, реализует класс для получения данных \для дашборда (дашборд "Настроечные фильтры").
Укажем описание с точки зрения дизайна в начале модуля.
```python
"""
Подклассы CRUD создаются для соответствующих операций с базами данных
через SQLAlchemy(Принимают объект Session).
Используются в функциях в модуле api -> endpoints.
Передают данные в serializers.

TODO: возможно реализовать отдельно метод для запросов, не возвращающих данных из базы.
"""
from abc import abstractmethod

from sqlalchemy.orm import Query, Session

from dashboard_backend.models import filter_table


class CRUDBase:
    @abstractmethod
    def get_query(self, db: Session, field: str) -> Query:
        pass


class CRUDSetupFilters(CRUDFilterBase):
    def get_query(self, db: Session, field: str) -> Query:
        table_field = getattr(self.model.c, field)
        db_query = (
            db.query(table_field.label(field))
            .group_by(table_field)
            .order_by(table_field)
        )
        return db_query


setup_filter = CRUDSetupFilters(filter_table)
```

## Выводы:

В целом описание задач класса внутри дизайна в целом, не только может помочь другим программистам,
но и позволяет меньше держать в голове самому взаимодействия внутри проекта.

Держать маленький кусочек "документации" внутри проекта в коде довольно удобно.
Впредь буду стараться писать в начале модуля или в docstring класса такие описания.
Думаю, наиболее удачное место для них -- в абстрактном классе или интерфейсе.

Вообще если я правильно понимаю, антипаттерн это не сам "самодокументирующийся код" как таковой,
(все равно лучше стараться писать как можно более выразительно и ясно), а то что он не может полностью
заменить комментарии / документацию на уровне дизайна.
