# Hard Work | True inheritance



## Неистинное наследование

- В ходе чтения "Паттернов проектирования" Фрименов решил попробовать паттерн "Команда".
- Есть список объектов (скажем что это Задачи(Task)) с инструкциями для выполнения в базе данных.
- По задаче нужно перебрать все объекты в списке и выполнить инструкции.
- Для этого определяю абстрактный класс "Command".
- Затем для каждой агрегации переопределяем метод `execute()` в этом классе, чтобы клиент мог
  вызвать на список комманд, которые ему необходимы, один метод.

Пример:
Класс задачи, у которой есть несколько методов работы с базой.
```python
 class AggregationX:
     def __init__(
         self,
         config: ProcessConfig,
     ) -> None:
         self.DATE = config.get_date()
         self.table: Table = config.get_table()
         self.insert_stmt = insert_stmt

     def insert_into_table(self, session) -> None:
         session.execute(
             self.en_table.insert().from_select(
                 [
                     "field1",
                     "field2",
                 ],
                 self.insert_stmt,
             ),
         )

     def create_table(self) -> None:
         ...
```
Отдельные подклассы Команды переопределяют метод `execute()`, чтобы реализовать некую логику
за счет методов Задачи.
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
В основном процессе скрипт проходится по списку комманд.
```python
 class Stage:
     def __init__(
         self,
         name: str,
         commands: List[str],
         config: ProcessConfig,
     ) -> None:
         self.name = name
         self.config = config
         self.fabric = CommandFabric(commands, config)
         self.commands: List[Command] = self.fabric.commands_obj

     async def __prepare_coroutines(self) -> None:
         dsn = self.config.get_click_async_dsn()
         async_click_engine = create_async_engine(dsn)
         async with make_session(async_click_engine, is_async=True) as asession:
             # Create a list to store the coroutines
             coroutines: List[Awaitable] = []

             # Create a coroutine for each object's execute method
             for command in self.commands:
                 command
                 coro = command.execute(asession)
                 coroutines.append(coro)

             # Await all the coroutines concurrently
             await asyncio.gather(*coroutines)
         await async_click_engine.dispose()  # type: ignore
```

Похоже на подходящее место, чтобы попробовать применить Visitor.
(В коде переопределяется метод для выполнения + про Visitor пишут, что он как раз является 
более мощной версией Command).


## Истинное наследование


- Создаем класс Visitor.
- Теперь логика, которая раньше реализовывалась в Команде, присутствует в одном классе,
- При этом это происходит для всех задач одновременно.

```python
 class TaskProcessVisitor(Visitor):
     async def visit_en_aggregation(
         self,
         task: AggregationEN,
     ) -> None:
         await task.create_table(self.task.main_table)
         await task.insert_into_table(task.insert_stmt, self.session)

     async def visit_ru_aggregation(
         self,
         task: AggregationRU,
     ) -> None:
         await task.create_mat_view_1()
         await task.create_mat_view_2()
         await task.insert_into_table(self.task.table_1)
         await task.insert_into_table(self.task.table_2)
```
Добавим метод `accept()` в задачу, чтобы она могла реализовать метод Double Dispatch.
В будущем такой метод должен быть включен во все классы, с которыми может взаимодействовать `Visitor`.
```python
class AggregationEN:
    def __init__(
        self,
        config: ProcessConfig,
    ) -> None:
        self.DATE = config.get_date()

        self.en_table: Table = darkstore_agg_en_table
        self.insert_stmt = create_subquery3(self.DATE)

    def accept(self, visitor: Visitor) -> Awaitable:
        return visitor.visit_en_aggregation(self)
```
- Исправляем класс с основным процессом.
- Фабрика для команд больше не нужна.
- Вместо этого в процессе создается эксемпляр посетителя.
- `Посетитель` проходится по всем переданным задачам, и реализует прописанную у него логику.

```python
 class Stage:
     def __init__(
         self,
         name: str,
         commands: List[str],
         config: ProcessConfig,
     ) -> None:
         self.name = name
         self.config = config
         self.fabric = TaskFabric(commands, config)
         self.tasks: List[Task] = self.fabric.task_obj

     async def __prepare_coroutines(self) -> None:
         dsn = self.config.get_click_async_dsn()
         async_click_engine = create_async_engine(dsn)
         async with make_session(async_click_engine, is_async=True) as asession:
             coroutines: List[Awaitable] = []

             # Создаем Посетителя
             visitor = TaskProcessVisitor(asession)
             for task in self.tasks:
                 coro = task.accept(visitor)
                 coroutines.append(coro)

             # Await all the coroutines concurrently
             await asyncio.gather(*coroutines)
         await async_click_engine.dispose()  # type: ignore
```

**Плюсы**:
- Избавились от промежуточной прослойки классов Комманд.
- Все методы работы с базой реализованы внутри одного класса, где их лего наблюдать и изменять при необходимости.
- В будущем могут появится и другие классы, не похожие на класс Task, под них в первом случае пришлось бы делать
дополнительную иерархию классов. C `Visitor` возможно просто включить в него дополнительную логику, главное чтобы 
новые классы имели метод `accept()`.

**Минусы**: 
- Сложнее тестировать. 
Если исользуется тестовый Task, что нужно также добавить посетителю знание об этом тестовом Таске.
Чтобы не трогать исходный код Посетителя. Приходится через мок подставлять фальшивого посетиеля.

**Личное мнение**:

- Нравится, что не нужна прослойка из комманд, можно сократь проект на целый модуль, но с тестированием намучился сильно :). Вероятно, не стоит создавать посетителя прям в методе Клиента, лучше наверное в конструкторе. 

- Похоже именно это имеют в виду в минусах, когда пишут что в этом паттерне нарушается инкапсуляция классов которые посещает `Visitor`, поэтому они становятся более зависимыми друг от друга.
