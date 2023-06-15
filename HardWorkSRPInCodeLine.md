# Hard Work - SRP

## 1. Пример

- Было:
  Задача функции - выведение запроса для таблицы категорий.
  Вертятное нарушение SRP - дополнительно верхняя планка для даты
  вычисляется внутри функции.

```python
def create_category_subquery(date_: datetime, days: int) -> Select:
   
 return (select([
     category_table.c.product_id,
     category_table.c.store_id,
     func.avg(category_table.c.shelf).label("mean_shelf"),
     func.groupUniqArray(categories_postres.c.sub_category_name)
         .label("sub_categories")
     ]).where(
         and_(
         category_table.update_time >= date_, 
       # Некорректная строчка
         category_table.update_time <  start_date + timedelta(days=days), 
     )))
```

- Стало
  Решение - вместо вычичления внутри функции передаем ей уже вычисленное
  значение верхней планки по дате.

```python
 def create_category_subquery(date_: datetime, date_next: datetime,) -> Select:
     
   return (select([
       category_table.c.product_id,
       category_table.c.store_id,
       func.avg(category_table.c.shelf).label("mean_shelf"),
       func.groupUniqArray(categories_postres.c.sub_category_name)
           .label("sub_categories")
       ]).where(
           and_(
           category_table.update_time >= date_, 
           # Корректировка
           category_table.update_time <  date_next, 
       )))
```

- Результат: более читабельный формат ORM запроса (которые и без того не
  слишком читабельно выглядят).

## 2. Пример

- Было:
  Функция внутри класса, который выполняет ряд асинхронных запросов
  для получения данных в БД.
  Функция должна подготавливать корутины, однако помимо этого:

1. Получает движок SQLAlchemy, и закрывает его в конце.

```python
 async def __prepare_coroutines(self) -> None:
     coroutines: List[Awaitable] = []

     # Вероятно также нарушение SRP
     visitor = self.visitor_cls()
     for task in self.tasks:
         coro = task.accept(visitor)
         coroutines.append(coro)

     await asyncio.gather(*coroutines)
     # Нарушение SRP внутри одной строчки
     await self.config.get_click_async_engine().dispose()
     # ---------------------------------------------------
```

- Стало
  Предлагаемое решение - закрывать движок должна отдельная функция.
  (заодно поправим - Экземпляр класса visitor должен
  создаваться внутри конструктора класса.)

```python
 async def __prepare_coroutines(self) -> None:
     coroutines: List[Awaitable] = []
     for task in self.tasks:
         coro = task.accept(self.visitor) # посетитель создался в __init__
         coroutines.append(coro)
     await asyncio.gather(*coroutines)

 # Закрываем асинхронный движок в отдельном методе
 async def dispose_async_engine(self) -> None:
   # Обращаемся к движку и
   # закрываем движок на разных строчках
     async_click_engine = self.config.get_click_async_engine()
     await async_click_engine.dispose()  # type: ignore
```

- Результат: Закрытие движка вынесено в отедельный метод, в котором
  у каждой строчки также единственная ответственность.

## 3. Пример

- Было:
  Очень длинная строчка из вызова множества методов для получения данных.

```python
 def get_data(self):
     """
     Метод берет необработанные данные
     и записывает JSON из базы в словари.
     """
     # id берем из кэша
     store_ids = [item[0] for item in select_active_stores()]

     with database_connection.get_connection() as connection:
         with connection.begin():
             # Проблемная строчка
             self.stores_raw_data = connection.execute(select_raw_data(store_ids)).fetchall()
       ...
            
```

- Стало
  Попроубем разделить получение данных на этапы построчно.

```python
 def get_data(self):
     """
     Метод берет необработанные данные
     и записывает JSON из базы в словари.
     """
     # id берем из кэша
     store_ids = [item[0] for item in select_active_stores()]

     # рефакторинг
     select_raw_data_query = select_raw_data(store_ids)
     with database_connection.get_connection() as connection:
         with connection.begin():
             connection.execute(select_raw_data_query)
             self.stores_raw_data = connection.fetchall()
```

- Результат: изменение позволило разделить запрос построчно по одной
  ответственности на строчку кода и как следствие улучить читабильность в функции.

## 4. Пример

- Было:
  Асинхронный метод в телеграм-боте для дипломного проекта Django.
  Внутри вызова метода ответа бота создается.

```python
 async def end_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
     self._end_date = str(update.message.text)
     reply_keyboard = [["Подневный", "Помесячный"]]
     await update.message.reply_text(
         "Выберите тип отчета",
         # Проблемная строчка с точки зрения SRP
         reply_markup=ReplyKeyboardMarkup(
             reply_keyboard,
             one_time_keyboard=True,
             input_field_placeholder="Тип отчета",
         ),
     )
     return self.REPORT_TYPE
```

- Стало
  Будет более явно, если мы будем создадим объект `reply` заранее и при вызове метода
  будем использовать его.

```python
 async def end_date(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
     self._end_date = str(update.message.text)
     reply_keyboard = [["Подневный", "Помесячный"]]
     reply = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True,
             input_field_placeholder="Тип отчета",
     )

     await update.message.reply_text(
         # Рефакторинг здесь 
         "Выберите тип отчета", reply_markup=reply
     )
     return self.REPORT_TYPE
```

- Результат: повысили читабельность метода. (note: возможно также лучше вообще передавать
  объект в функцию в виде параметра, а не создавать его внутри)

## 5. Пример

- Было:
  В строчке одновременно происходит получение значения "date"
  и расчет значения start_date.

```python
 class VehicleDetailView(LoginRequiredMixin, DetailView):
     template_name = "auto/vehicle_detail.html"
     model = Vehicle
     context_object_name = "vehicle"

     def get_context_data(self, **kwargs):
         context = super().get_context_data(**kwargs)

         # В строчке одновременно происходит получение значения "date"
         # и расчет значения start_date
         start_date = (
             self.request.GET.get("date").date()
             - timedelta(days=90))
         )
         ...
```

- Стало
  Нужно разделить процесс на 2 этапа:

1. Получим значение date
2. Произведем расчет даты для start_date

```python
 class VehicleDetailView(LoginRequiredMixin, DetailView):
     template_name = "auto/vehicle_detail.html"
     model = Vehicle
     context_object_name = "vehicle"

     def get_context_data(self, **kwargs):
         context = super().get_context_data(**kwargs)

         # Небольшой рефакторинг
         date = self.request.GET.get("date")
         date = date.date()
         start_date = date - timedelta(days=90)
         ...
```

- Результат: более читабельный формат.

## 6. Пример

- Было:
  Еще одна функция для получения данных из БД.
  Здесь при запросе данных одновременно.

1. Создается запрос;
2. Подставляются параметры, при подстановке некоторые расчитываются "на месте";
3. Запрос в `str` оборачивается в ORM'овский `text()`;
4. Запрос передается в метод execute;

```python
 def get_data_from_db(self):
     # Подключение к базе
     ...

     # Меняем статус отчета в таблице на in progress
     ...

     # проблемное место
     with click_connection.get_session() as session:
         search_data = session.execute(text(get_search_query(
             date_start=self.start_date,
             date_end=self.end_date,
             ids=self.config['ids'],
             platforms=self.config['platforms'],
             deliveries=self.config['deliveries_raw_list'] if 'deliveries_raw_list' in self.config else None,
             store_stop_list=self.config.get("store_stop_list"),
         ))).all()

```

- Стало
  Попробуем выполнить перечисленные выше шаги поэтапно.

```python
 def get_data_from_db(self):
     # Подключение к базе
     ...

     # Меняем статус отчета в таблице на in progress
     ...

     deliveries = (
         self.config['deliveries_raw_list'] 
         if 'deliveries_raw_list' in self.config 
         else None
     )
     store_stop_list = self.config.get("store_stop_list", None)
     search_query_str = get_search_query(
         date_start=self.start_date,
         date_end=self.end_date,
         ids=self.config['ids'],
         platforms=self.config['platforms'],
         deliveries=deliveries,
         store_stop_list=store_stop_list,
     )
     search_query = text(search_query_str)

     with click_connection.get_session() as session:
         search_data = session.execute(search_query).all()
```

- Результат: отделили этап подготовки и создания запроса от его выполнения.

## Выводы

- В целом такой подход к написанию кода позволяет сделать его более читабельным,
  а также облегчает дальнейшие внесения измененй / рефакторинг (изменения можно внести
  сразу в нужном месте, и это реже повлечет за собой необходимость исправлять соседний
  код).
