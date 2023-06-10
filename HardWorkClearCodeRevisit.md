# Hard Work - Clear Code



## Методы, которые используются только в тестах.

- Пример до
  для тестирования обектов, с которым работает Посетитель,
  создавал подставного посетителя, чтобы он вызывал тестовые методы.
```python
 class FakeVisitor(TaskProcessVisitor):
     async def visit_test(self, task):
         await task.execute_test_query()

 class TaskExample:
     def __init__(self, config: ProcessConfig) -> None:
         self.config = config
         self.engine = config.get_click_async_engine()

     def accept(self, visitor: FakeVisitor) -> Awaitable:
         return visitor.visit_test(self)
```
- Как можно поправить:
  Так как посетитель определяет не сам, какие методы можно вызывать
  А ориентируется на то, каким объект "посещается", достаточно указать реальный метод.
  Т.к. в моем случае используется долгий запрос к базе, можно переопределить метод тестируемого объекта
  (в данном случае тестируется не он, а работа Посетителя в целом).

- Пример после
```python
# Испозьзуем теперь реального, а не подставного Посетителя
 class TaskProcessVisitor(Visitor):
     async def visit_en_aggregation(self, task) -> None:
         await task.insert_into_table()

 class AggregationENTaskMock(AggregationENTask):
    # Этот метод не переопределяем, привожу его здесь для 
    # наглядности
     def accept(self, visitor: TaskProcessVisitor) -> Awaitable:
         return visitor.visit_en_aggregation(self)

    # Переопределяем запрос на более простой.
     async def insert_into_table(self) -> None:
         async with make_session(self.engine, is_async=True) as asession:
             query = text("INSERT INTO delete_me (id, name) VALUES(:id, :name)")
             result = await asession.execute(query, {"id": 1, "name": "kek"})
```
- Комментарий
  Избавались от лишних классов с доп.методами (`TaskExample`, `FakeVisitor`)
  Выглядит проще и "чище".


## Цепочки методов.

- Пример до
  Метод для создания SQL запроса вызывает метод для создания подзапроса, которому нужно также вызывать метод для внутреннего подзапроса.

```python
 def create_category_query(self, date_: date) -> Select:
     end_date = date_ + timedelta(days=1)
     ...
     return create_inner_subquery(date_, subquery_category)

 def create_inner_subquery(self, date_: date) -> Select:
     end_date = date_ + timedelta(days=1)
     ...
     inner_subquery = ...
     return create_middle_subquery(date_, subquery_category)

 def create_middle_subquery(date_: date, inner_subquery: Select) -> Select:
     end_date = date_ + timedelta(days=1)
     ...
     middle_subquery = ...
     return create_final_subquery(date_, subquery_category)

 def create_final_subquery(date_: date, middle_subquery: Select, target_table: Table) -> Select:
     end_date = date_ + timedelta(days=1)
     ...
     final_subquery = ...
     return final_subquery
```

Как можно поправить:
Достаточно одного метода, в котором можно создать все подзапросы за один раз и объединить их.
(подзапросы не имеют смысла за пределами этого запроса).

- Пример после
```python
 def create_category_query(self, date_: date) -> Select:
     end_date = date_ + timedelta(days=1)
     inner_subquery =  # реализация
     middle_subquery = # реализация с использованием inner_subquery
     final_subquery =  # реализация с использованием middle_subquery
     return final_subquery

```
- Комментарий
  Метод получится довольно большим, однако все необходимые этапы зависимы друг от друга, поэтому кажется что это нормально.


## У метода слишком большой список параметров.

- Пример до
  Запрос использует в качестве параметров 2 даты,
  На самом деле вторая дата излишняя, т.к. это всегда "день" и "сделующий за ним день".
  Таким образом второй параметр лишний, т.к. зависит от первого.
```python
 def create_en_no_stock_category_subquery(start_date: datetime) -> Select:
     end_date = start_date + timedelta(days=1)

     return (select([
         # здесь выбор колонок из базы
         ]).select_from(
             # параметры запроса
         )
         .where(
             # параметры запроса
         )
         .group_by(
             # параметры запроса
         )
     )
```
- Как можно поправить:
  Расчитываем вторую дату внутри метода.
  В метод передаем только один параметр.

- Пример после
```python
def create_en_no_stock_category_subquery(start_date: datetime, end_date: datetime) -> Select:
 start_date = date_
 end_date = start_date + timedelta(days=1)

 return (select([
     # здесь выбор колонок из базы
     ]).select_from(
         # параметры запроса
     )
     .where(
         # параметры запроса
     )
     .group_by(
         # параметры запроса
     )
 )
```
- Комментарий
  Пример небольшой, но метод стало легче использовать и он защищен от ошибок.
  (Запрос НЕ с "день", "следующий день" выдаст неверную информацию).


## Странные решения (несколько методов используются для решения одной и той же проблемы, создавая несогласованность).

- Пример до
  В примере метод `get_click_async_engine` создает движок для работы с БД.
  Этот метод обращается к уже установленному в конструктое параметру для создания.
  В это же время метод `get_click_async_metadata` нуждается в движке. При этом
  внутри него создается отдельный движок, хотя можно использовать уже созданный.
```python
 class ProcessConfig:
     def __init__(self, **kwargs) -> None:
         ...

     def get_date(self) -> datetime:
         return self.date

     def get_click_async_dsn(self) -> str:
         return self.click_async_dsn

     def get_click_async_engine(self) -> Engine:
         async_engine = make_engine(self.click_async_dsn, async_=True)
         return async_engine

     def get_click_async_metadata(self) -> MetaData:
         dsn = self.kwargs["async_dsn"]
         async_engine = make_engine(self.click_async_dsn, async_=True)
         return MetaData(bind=async_engine)

```
- Как можно поправить:
  Не нужно создавать движок в 2 методах :).
  Установим движок как атрибут класса, и при необходимости будем обращаться к нему.

- Пример после
```python
 class ProcessConfig:
     def __init__(self, **kwargs) -> None:
         ...
     def get_date(self) -> datetime:
         return self.date

     def get_click_async_dsn(self) -> str:
         return self.click_async_dsn

     def get_click_async_engine(self) -> Engine:
         async_engine = make_engine(self.click_async_dsn, async_=True)
         self.async_engine = async_engine
         return async_engine

     def get_click_async_metadata(self) -> MetaData:
         return MetaData(bind=self.async_engine)
```
- Комментарий


## Чрезмерный результат. Метод возвращает больше данных, чем нужно вызывающему его компоненту. 

### 1. Пример до

Пример из задачи дипломного проекта.
Метод возвращает точки трека автомобиля, но так как они были
отданы API, т.е. с JSON с лишней информацией.
```python
 def get_track(
     self,
     start_point: Point_,
     end_point: Point_,
 ) -> List[Dict]:
     route = self.client.directions(
         coordinates=([start_point] + [end_point]),
         profile="driving-car",
         format="geojson",
     )
     return route["features"][0]["geometry"]["coordinates"]
```
- Как можно поправить:
  Думаю, не обязательно создавать дополнительные методы обработки и 
  метод може сразу вернуть список из объектов класса Point_ на месте.

- Пример после
```python
 def get_track(
     self,
     start_point: Point_,
     end_point: Point_,
 ) -> List[Point_]:
     route = self.client.directions(
         coordinates=([start_point] + [end_point]),
         profile="driving-car",
         format="geojson",
     )
     route_points = route["features"][0]["geometry"]["coordinates"]
     route_points_clear = [Point_(p) for p in route_points]
     return route_points_clear
```
- Комментарий
  Изменение позволило убрать лишний метод, т.к. другому методу не нужно
  иметь дело с избыточной информацией из `get_track()`.


### 2. Пример до

Еще неболошой пример из одной из первых моих программ. В классе находится
список общий слов в названиях различных продуктов.
Один из методов возвращает токенизированные слова.
Метод зачем-то одновремменно обрабатывает 2 сравниваемых текста
и возвращает оба.
```python
 def calc_common_words(self, text1, text2) -> Tuple[List]:
     tokenized_text1 = self.tokenize(text1)
     tokenized_text2 = self.tokenize(text2)
     return tokenized_text1, tokenized_text2
```
- Как можно поправить:
  Метод должен просто принимать на входе один текст и возвращать сет из токенов.
- Пример после
```python
 def calc_common_words(self, text) -> List:
     tokenized_text = self.tokenize(text)
     return tokenized_text
```
- Комментарий
  Метод достаточно просто вызвать дважды для обоих сравнивемых
  названий продуктов.
