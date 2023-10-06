# Hard Work - Пишем безошибочный код

## Пример 1

Класс `ReportCreator` управляет процессом создания клиентские отчетов на основе данных из БД. Для этого он выполняет следующие задачи:

- Отправляет сигнал для БД на увеличение ресурсов перед запуском формирования отчетов.
- Запускает выполнение формирования отчетов путем создания объекта класса `Stage` и запуском его метода выполнения

Эти задачи должны быть выполнены последовательно, необходимо сначала увеличивать ресурсы, только потом формировать отчеты

Часть оригинального кода:

```python
class ReportCreator:
    def __init__(
        self,
        stages: Dict[str, List[str]],
        dates: List[datetime],
        engine: str,
    ) -> None:
        self._stages = stages
        self._dates = dates
        self._click_async_dsn: str = engine
        self._async_click_engine = create_async_engine(engine)

    def upscale_db(self) -> None:
        try:
            # too much code
            ...
        except RequestException as e:
            log.error(e)

    def run_process(self) -> None:
        for date in self.dates:
            log.info(f"Processing date: {date}")
            self._process_stages(date)
    
    def _process_stages(self, date: datetime) -> None:
        for stage in self.stages:
            log.info(f"Processing stage: {stage.stage}")
            stage = Stage(
                name=stage.stage, 
                commands=stage.tasks, 
                engine=self._async_click_engine, 
                date=date
            )
            stage.execute_stage()
```

Создадим абстрактный класс для состояния:

```python
class AbstractDBState(ABC):
    def __init__(
        self,
        stages: Dict[str, List[str]],
        dates: List[datetime],
        engine: str,
        context
    ) -> None:
        self._stages = stages
        self._dates = dates
        self._click_async_dsn: str = engine
        self._async_click_engine = create_async_engine(engine)
        self.context = context

    @abstractmethod
    def change_db_resourses(self) -> None:
        pass
        
    @abstractmethod
    def run_process(self) -> None:
        pass
```

Конкретные классы состояния:
Эти классы также принимают контекст, который управляет состояниями и переводят этот контекст при необходимости в следующее состояние.

```python
class NonScaledDBState(AbstractDBState):

    def change_db_resourses(self) -> None:
        """
        Здесь будем подстраивать ресурсы БД под задачу
        """
        try:
            # too much code
            ...
            # !!!!
            self.context.current_state = self.context.scaled_state
        except RequestException as e:
            log.error(e)

    def run_process(self) -> None:
        raise Exception("Cannot run before upscale resources")


class ScaledDBState(AbstractDBState):

    def change_db_resourses(self) -> None:
        """
        Здесь будем вернем ресурсы БД к изначальным
        """
        try:
            # too much code
            ...
            # !!!!!!!
            self.context.current_state = self.context.non_scaled_state
        except RequestException as e:
            log.error(e)

    def run_process(self) -> None:
        for date in self.dates:
            log.info(f"Processing date: {date}")
            self._process_stages(date)
    
    def _process_stages(self, date: datetime) -> None:
        for stage in self.stages:
            log.info(f"Processing stage: {stage.stage}")
            stage = Stage(
                name=stage.stage, 
                commands=stage.tasks, 
                engine=self._async_click_engine, 
                date=date
            )
            stage.execute_stage()
```

Создадим класс, управляющий этими состояниями:

```python
class ReportCreatorContext:
    def __init__(
        self,
        stages: Dict[str, List[str]],
        dates: List[datetime],
        engine: str,
    ) -> None:
        self.non_scaled_state = NonScaledDBState(
            stages, dates, engine, create_async_engine(engine),
        )
        self.scaled_state = ScaledDBState(
            stages, dates, engine, create_async_engine(engine),
        )
        self.current_state = self.non_scaled_state

    def change_db_resourses(self) -> None:
        self.current_state.change_db_resourses()

    def run_process(self) -> None:
        self.current_state.run_process()

```

Итого:

Мы создали управляющую конструкцию, которая не должна позволить никоим образом запустить формирование отчетов без предварительной подготовки за счет невозможности такого состояния. Это достигается путем реализации допустимых состояний как отдельных сущностей и механизмов перехода одного состояния в другое.

## Пример 2

В реализации GUI для машины Тьюринга, имеем основной класс приложения, в котором есть булевый флажок, который отвечает за то, что программу допустимо запускать.

Некоторые методы, при изменении набора команд для машины Тьюринга, или значений в ленте, проверяют валидность (допустимость) этого набора для запуска симуляции.

Естественно, булевое значение в переменной класса - не самое надежное решение, попробуем исправить.

```python
@dataclass
class TuringMachineApp:
    state_value: int
    alph_value: int
    is_ready_to_start: bool = True
    is_on: bool = False
    current_table_state: int = 1
    table_data: list[list[str]] = field(default_factory=list)
    tape: list[str] = field(default_factory=lambda: ["_"] * 30)
    current_tape_cell: int = 15
    mutex = QMutex()

    # Методы класса (все не расписываю)
    ...    

    def __validate_table(self):
        self.machine.is_ready_to_start = True
        for row, row_val in enumerate(self.machine.table_data):
            for col, cell_val in enumerate(row_val):
                self.__validate_table_cell(cell_val, row, col)

    def __validate_table_cell(
        self, cell_value: str, row: int, col: int
    ) -> None:
        col_msg = str(col - 1) if col > 0 else "_"
        row_msg = row + 1
        try:
            val_change, move, step = cell_value.split(" ")
        except ValueError:
            QMessageBox.critical(
                self, "Fail",
                f"Wrong number of arguments, cell {col_msg}-Q{row_msg}"
            )
            self.machine.is_ready_to_start = False
            return
```

Изначально создаваемый класс должен быть машиной Тьюринга, не готовой к запуску, т.е. содержать только возможности вносить изменения в таблицу команд и валидировать значения.
Для реализации всего этого, создадим базовый класс `TMBaseState`, который будет абстрактным.

```python
@dataclass
class TMBaseState(ABC):
    app: App
    ...
    # В конструкторе теперь указываем ссылку на приложение (которое выступает в роли контекста)

    # Методы класса (все не расписываю)
    ...    
    @abstractmethod
    def execute_single_step(self) -> bool:
        pass

    @abstractmethod
    def execute_many_steps(self) -> None:
        pass

    # класс умеет валидировать, так как это умеют все состояния машины 
    def _validate_table(self):
        self.app.current_machine = self.app.ready_machine
        for row, row_val in enumerate(self.machine.table_data):
            for col, cell_val in enumerate(row_val):
                self.__validate_table_cell(cell_val, row, col)

    # класс умеет валидировать, так как это умеют все состояния машины 
    def _validate_table_cell(
        self, cell_value: str, row: int, col: int
    ) -> None:
        col_msg = str(col - 1) if col > 0 else "_"
        row_msg = row + 1
        try:
            val_change, move, step = cell_value.split(" ")
        except ValueError:
            QMessageBox.critical(
                self, "Fail",
                f"Wrong number of arguments, cell {col_msg}-Q{row_msg}"
            )
            self.app.current_machine = self.app.non_ready_machine
            return
```

Изначальная, не готовая к запуску, машина:

```python
class TMNonReadyState(TMBaseState):
    """
    Переопределяем методы здесь, чтобы они вызывали сообщение пользователю
    о необходимости исправить ошибки
    """

    def execute_single_step(self) -> bool:
        QMessageBox.critical(
            self, "Fail",
            f"Please fix errors in table"
        )
        return False

    def execute_many_steps(self) -> bool:
        QMessageBox.critical(
            self, "Fail",
            f"Please fix errors in table"
        )
        return False

```

Готовый к работе вариант

```python
class TMReadyState(TMBaseState):
    """
    Переопределяем методы здесь, чтобы они выполняли команды
    """

    def execute_single_step(self) -> bool:
       with QMutexLocker(self.mutex):
            current_tape_cell_val = self.tape[self.current_tape_cell]
            if current_tape_cell_val == "_":
                columns_inx = 0
            else:
                columns_inx = int(current_tape_cell_val) + 1
            command = self.\
                table_data[self.current_table_state - 1][columns_inx]
            val, move, next = self.__parse_command(command)
            self.__update_machine_state(val, move, next)
            if next == 0:
                self.current_table_state = 1
                return False
            return True

    def execute_many_steps(self) -> bool:
        """По аналогии с execute_single_step"""
        return True

```

В основной части приложения создаем контекст, содержащий оба варианта машины:

```python
class TuringMachineGUI:
    """Нужно перенести сюда данные, так как 2 классов состояния 
       дожны ссылаться на одно состояние при симуляции
    """
    state_value: int
    alph_value: int
    is_on: bool = False
    current_table_state: int = 1
    table_data: list[list[str]] = field(default_factory=list)
    tape: list[str] = field(default_factory=lambda: ["_"] * 30)
    current_tape_cell: int = 15
    mutex = QMutex()

    # Создаем обе машины
    self.non_ready_machine = TMNonReadyState(self)
    self.ready_machine = TMReadyState(self)
    self.current_machine = self.non_ready_machine
```

При валидации, если все ок, методы валидации НЕ-готовой машины изменять текущий класс в приложении на готовую к работе машину, и все те же переопределенные методы будут ответственны за запуск симуляции.

Итого:
Разделением ответственности о валидации правильности данных программы и собственно запуском мы добились большей безопасности при работе приложения, так как теперь методы, отвечающие за корректную работу симуляции, связаны с соответствующим состоянием.

## Пример 3

Дополнительная идея - при создании отчетов, уже в ходе непосредственного выполнения запросов к БД, можно также разделить на состояния:

- задача перед запуском серии запросов
- задача в процессе выполнения серии запросов

Это разделение состояний нужно в случае, если например, произойдет ошибка при выполнении процесса. Так как в процессе может происходить создание и заполнение временных таблиц, нужно дополнительно учитывать это перед перезапуском.
Таким образом, возможны 2 сценария:

- запуск на "чистую", без предварительной очистки
- запуск после неудачного выполнения предыдущей попытки

Т.е. нам нужны 2 класса состояний:

Базовый класс:

```python
class BasicTaskState(ABC):

    def __init__(
        self, engine: Engine
        drop_tmp_query: sa.text,
        create_tmp_query: sa.text,
        insert_tmp_query: sa.text,
        insert_into_main_query: sa.text,
    ) -> None:
        self.engine = engine
        self.drop_tmp_query = drop_tmp_query
        self.create_tmp_query = create_tmp_query
        self.insert_tmp_query = insert_tmp_query
        self.insert_into_main_query = insert_into_main_query

    @abstractmethod
    def accept(visitor: TaskVisitor) -> None:
        pass

    @abstractmethod
    def drop_tmp_table(self) -> None:
        pass

    @abstractmethod
    def create_tmp_table(self) -> None:
        pass

    @abstractmethod
    def insert_into_tmp_table(self) -> None:
        pass

    @abstractmethod
    def insert_into_main_table(self) -> None:
        pass
```

Вариант класса, который должен использоваться при стандартном использовании. Все методы, имеющие дело с временными таблицами, нам не нужно, чтобы не нарушать интерфейс, можно просто оставить их "пустыми".

```python
class ClearTaskState(BasicTaskState):

    def accept(visitor: TaskVisitor) -> None:
        return visitor.visit_standard_report_creation(self)

    def drop_tmp_table(self) -> None:
        pass

    def create_tmp_table(self) -> None:
        pass
        
    def insert_into_tmp_table(self) -> None:
        pass

    def insert_into_main_table(self) -> None:
        with make_session(self.engine) as session:
            for query in self.insert_into_main_query:
                session.execute(query, self.params)
```

Вариант класса, который должен использоваться при формировании отчета после нештатного завершения.

```python
class EmergencyTaskState(BasicTaskState):

    def accept(visitor: TaskVisitor) -> None:
        return visitor.visit_emergency_report_creation(self)

    def drop_tmp_table(self) -> None:
        with make_session(self.engine) as session:
            for query in self.drop_tmp_query:
                session.execute(query)

    def create_tmp_table(self) -> None:
        with make_session(self.engine) as session:
            for query in self.create_tmp_query:
                session.execute(query, self.params)
        
    def insert_into_tmp_table(self) -> None:
        with make_session(self.engine) as session:
            for query in self.insert_tmp_query:
                session.execute(query)

    def insert_into_main_table(self) -> None:
        with make_session(self.engine) as session:
            for query in self.insert_into_main_query:
                session.execute(query, self.params)
```

 Управляем поведением классов в ходе работы при помощи паттерна "Посетитель":

```python
 def visit_standard_report_creation(self, task) -> None:
        task.insert_into_main_table()

 def visit_emergency_report_creation(self, task) -> None:
        task.drop_category_table()
        task.create_category_table()
        task.insert_into_category_table()
        task.insert_into_main_table()
```

## Выводы

Разделение классов на несколько классов, отвечающих за специфичные состояния в ходе работы программы, как мне кажется, позволяет добиться следующего:

- Лучшее соблюдение принципа SRP, у класса как такового меньше ответственности, вместо этого она распределена по нескольким классам-состояниям.
- Разделение классов на классы, содержащие данные и классы, управляющие поведением (как раз классы-состояния), позволяет проще писать такой код, и рассуждать о нем.
- Классы-состояния гораздо более безопасны для использования, чем другие варианты (вроде использования булевых флажков внутри класса).

Также можно выделить некоторые минусы:

- Код получается в целом более многословным
- Нужно решать, что делать с объектами-состояниями, после переключения на другое состояние (держать в памяти, удалять)?
- Не всегда очевидно, как все классы состояния должны реализовывать один интерфейс (что делать, если метод не нужен внутри конкретного состояния, ничего?)

В целом в большинстве случаев преимущества использования классов-состояний очевидны и позволяют создавать более надежные и безопасные приложения.
