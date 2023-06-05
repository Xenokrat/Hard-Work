# Hard Work - Visitor Mixin



## Продолжаю Проект по автоматизации ETL процессов в базе данных.

- Отдельная задача из серии действий с БД реализуется классами TaskName
- В прошлый раз реализовали класс Visitor, который "посещал" Tasks и выполнял определенные методы этих классов.
- В некоторых Тасках создаются временные таблицы, которые можно удалить после завершения работы.
- Ссылки на таблицы хранятся в атрибутах классов Task и все они начинаются с `tmp_table...`

```python
 class TaskAggregationY(Task):
     def __init__(
         self,
         config: ProcessConfig,
     ) -> None:
         self.DATE = config.get_date()
         self.engine = config.get_click_async_engine()

         self.final_table: Table = final_table

         self.tmp_query_table1 = create_query_for_table1(self.DATE)
         self.tmp_table1 = None
         self.tmp_query_table2 = create_query_for_table2(self.DATE)
         self.tmp_table2 = None

     async def accept(self, visitor) -> Awaitable:
         return await visitor.visit_task_aggregation_y(self)

     async def create_query_for_table1(self) -> None:
         """
         Создаем временную таблицу tmp_table1 и 
         сохраняем ссылку на нее в атрибуте класса.
         """

     async def create_query_for_table2(self) -> None:
         """
         Создаем временную таблицу tmp_table2 и 
         сохраняем ссылку на нее в атрибуте класса.
         """

     async def insert_into_final_table(self) -> None:
         """
         Реализуем вставку в обычную таблицу с запросами, использующими
         временные таблицы выше.
         """
```

Можно попробовать создать примесь, которая будет реализовывать метод удаления временных таблиц,
чтобы не приходилось вносить изменения в все уже существущие классы Task... с временными таблицами.
В Python примеси реализуюся в основном через множественное наследование.

Создадим класс CleanupTablesMixin:
```python
class CleanupTablesMixin:
    async def delete_tmp_tables(self) -> None:
        tmp_tables_attr = [attr for attr in dir(self) if attr.startswith("tmp_table")]

        for attr in tmp_tables_attr:
            table = getattr(self, attr)
            try:
                await table.drop(bind=self.engine checkfirst=True)
            except Exception as e:
                log.error(e)
                continue
```

Включим этот миксин в приведенный выше класс
```python
class TaskAggregationY(CleanupTablesMixin, Task):
    def __init__(
        self,
        config: ProcessConfig,
    ) -> None:
        self.DATE = config.get_date()
        self.engine = config.get_click_async_engine()
        self.final_table: Table = final_table

        self.tmp_query_table1 = create_query_for_table1(self.DATE)
        self.tmp_table1 = None
        self.tmp_query_table2 = create_query_for_table2(self.DATE)
        self.tmp_table2 = None

        ...
```


Пусть класс Visitor вызывает метод очищения после завершения работы всех методов.
```python
class TaskProcessVisitor(Visitor):
    async def visit_search_ru_aggregation(
        self,
        task,
        ) -> None:
        await task.create_query_for_table1()
        await task.create_query_for_table2()
        await task.insert_into_final_table()
        # NEW
        await task.delete_tmp_tables()
```


## Выводы

Использование миксина позволило добавить дополнительное одинаковое поведение довольно разным по структуре
классам без изменения кода внутри классов и использования наследования.
Т.е. Посетитель используется для того, чтобы реализовать некую сходную логику в одном конексте
(например последовательное выполнение _разных_ преобразований данных). Миксин же можно использовать
для реализации сходного функционала для объектов, не обязательно из одной иерархии классов.


## P.S.

В последний момент пришла идея в голову, что такой миксин возможно можно реализовать как менеджер контекста. 
```python
class CleanupTablesMixin:
    def __enter__(self):
        return self

    def __exit__(self, ext_type, ext_value, traceback):
        tmp_tables_attr = [attr for attr in dir(self) if attr.startswith("tmp_table")]

        for attr in tmp_tables_attr:
            table = getattr(self, attr)
            try:
                await table.drop(bind=self.engine checkfirst=True)
            except Exception as e:
                log.error(e)
                continue
```

В Visitor тогда все задачи можно будет вызывать как:
```python
class TaskProcessVisitor(Visitor):
    async def visit_task_aggregation_y(
        self,
        task,
    ) -> None:
        with task as task_manager:
          await task.create_query_for_table1()
          await task.create_query_for_table2()
          await task.insert_into_final_table()
```
