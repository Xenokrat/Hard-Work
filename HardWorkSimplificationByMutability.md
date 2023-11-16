# Hard Work - Мутабельность как упрощение модели данных

## Пример

Имеем класс, который отвечает за ежедневное обновление агрегационных метрик из сырых данных в БД.

Абстактрый класс следующего вида:

```python
class AbstractDBTask(ABC):
    def __init__(
        self, 
        engine: Engine, 
        params: dict[str, Any],
        main_table: sa.Table,
        sub_table: sa.Table | None
    ) -> None:
        self.engine = engine
        self.params = params
        self.insert_query = insert_en_table_query
        self.main_table = main_table
        self.sub_table = sub_table

    @abstactmethod
    async def accept(self, visitor) -> None:
        pass

    @abstactmethod
    async def insert_into_tmp_table(self) -> None:
        pass

    @abstactmethod
    async def insert_into_main_table(self) -> None:
        pass
```

Зачастую для агрегации удобно использовать временную таблицу, поэтому интерфейс содержит следующие методы:

1. Заполнение временной таблицы данными (если это нужно).
2. Заполнение основной таблицы даннми (часто с использованием временной)

Если допустим, что в какой-то момент времени, уже были созданы подклассы с реализацией различных задач для БД. В каких то ситуациях после использованя временной таблицы данные в ней могут занимать много места, или еще мешать каким образом, например, если мы переиспользуем эту таблицу для чего-то еще.
Поэтому есть необходимость после выполнения всех действий сделать `truncate table` для такой таблицы.

Такой метод изначально не был реализован в абстрактном классе, и решать, нужно ли очищать временную таблицу или нет, нужно уже в реализациях.

```python
table_clearing_schema = {
    ConcreteDBTask1: "truncate table public.sub_table1",
    ConcreteDBTask2: "truncate table public.sub_table2",
    ConcreteDBTask3: None,
    ConcreteDBTask4: "truncate table public.sub_table4",
}
```

Далее можно придумать как использовать эти "прикрепленные к классам" методы, например:

```python
def post_work_clearing(schema: dict[AbstractDBTask, str], client: DB) -> None:
    for post_task, query in schema:
        if query:
            client.execute(query)
```

Или другой вариант:

```python
client = clickhouse.Client(...#)
table_clearing_schema = {
    ConcreteDBTask1: lambda: client.execute("truncate table public.sub_table1"),
    ConcreteDBTask2: lambda: client.execute("truncate table public.sub_table2"),
    ConcreteDBTask3: lambda: None,
    ConcreteDBTask4: lambda: client.execute("truncate table public.sub_table4"),
}
```

Удобно, что python позволяет использовать сами классы в качестве ключей для словаря.
При этом если мы хотим использовать созданный объект, можно получить класс из объекта.

```python
task1 = ConcreteDBTask1(
    "engine",
    {"param1": 1},
    "main_table",
    "sub_table",
)
# Вызов функции очистки временной таблицы
table_clearing_schema.get(task1.__class__)()
```

## Выводы

Конечно, данный способ ощущается немного неестественным, или даже чем-то, что коллеги могли бы назвать code smell (с другой стороны, почему?), но при условии, если мы не хотим вмешиваться в уже "закрытые" классы, и при этом, как в примере выше, нам придется создавать еще 4 подкласса (а отдельных задач для БД может быть десятки), такое решение кажется вполне рабочим.

Естественно, неудобно, что новые поля фактически находятся "снаружи" класса, и для осуществляния доступа нужно дописывать дополнительные функции.
Также в ходе написания появилась еще идея: вообще, Python позволяет добавлять классам новые атрибуты и методы "на лету" в рантайме, при помощи `setattr`, расшияя класс и его объекты новым функционалом, причем именно "изнутри". Хотя такой подход кажется более уязвимым для ошибок (например, как быть уверенным, что в нужный момент времени объект действительно обладает нужным методом?).

В целом, если мы очень хотим соблюсти `open-close` принцип, или издержки для модификации слишком велики, метод кажется вполне применимым. Однако, опять же, это все еще больше напоминает "заплатку" (но, наверное есть и более оправданные случаи, например для соблюдения SRP), и более эффективным и элегатным решением будет продуманное проектирование структуры программы.
