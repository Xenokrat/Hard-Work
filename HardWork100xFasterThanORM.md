# Hard Work - Ускоряем код фреймворков в 100 раз

## Пример 1

Пример из рабочей ситуации.
На уровне клиентской логики: ежедневно создаем таблицу, идентичную основной.
Превращаем эту новую таблицу в партицию основной таблицы.
Также используем `alebmic` для управления миграциями.
Использование `SQLAlchemy` не позволяет (по крайней мере очевидно) реализовать механизм, описанный выше, особенно с учетом использования `alembic`, который "видит" таблицы-партиции, как новые объекты.
Гораздо проще было использовать просто "сырой" SQL для Постгреса, который легко записывать как

```python
date_str = "2023-09-01"
date_str_table_name = "shelf20230901"
raw_query = sqlalchemy.text(f"""
 CREATE TABLE IF NOT EXISTS partition_{date_str_table_name}
 PARTITION OF client.public.shelf_table
 FOR VALUES IN ('{date_str}')
""")
```

По итогам:
Новый вариант позволяет эффективно управлять созданием новых партиций, при этом не создавая проблем с дополнительной настройкой `alembic`.

## Пример 2

Один из проектов на `Django` в процессе обучения.
Логика происходящего следующая:
Для секции новостей по категориям необходимо выбрать и вывести на экран опубликованные новости, в соответствии с выбранной пользователем категорией.

Базовый запрос выглядит следующим образом:

1. До

```python
class NewsByCategory(ListView, MyMixin):
 ...
 def get_queryset(self):
  return NewsModel.objects.filter(
   category_id=self.kwargs["category_id"], is_published=True)
  )
```

Можно значительно улучшить этот запрос, включив в него опцию `select_related`, что позволяет получить все данные за один раз, вместо того, чтобы джойнить объекты по одному.

2. После с добавлением `select_related`

```python
class NewsByCategory(ListView, MyMixin):
 ...
 def get_queryset(self):
  return NewsModel.objects.filter(
   category_id=self.kwargs["category_id"], is_published=True)
   .select_related("category")
  )
```

Напишем "сырой" запрос в обход ORM.

3. После "прямой" SQL запрос

```python
class NewsByCategory(ListView, MyMixin):
    ...
    def get_queryset(self):
        category_id = self.kwargs["category_id"]

        sql_query = """
        SELECT 
         newsmodel.id, 
         newsmodel.title,
         newsmodel.content,
         newsmodel.category_id, 
         newsmodel.is_published,  
         category.id   AS category_id,  
         category.name AS category_name
        FROM newsmodel
        INNER JOIN category ON newsmodel.category_id = category.id
        WHERE newsmodel.category_id = %s AND newsmodel.is_published = true
        """

        with connection.cursor() as cursor:
            cursor.execute(sql_query, [category_id])
            results = cursor.fetchall()

        # Transform the raw SQL query results into NewsModel objects
        queryset = []
        for row in results:
            news_model = NewsModel(**row[:5])
            category = Category(id=row[5], name=row[6])
            news_model.category = category
            queryset.append(news_model)

        return queryset
```

Сравнивая по скорости варианты:

1) ~ 400 мс
2) ~ 110 мс
3) ~ 100 мс
Выбор сразу всех данных позволяет значительно сократить время выполнения.
Разница запроса через ORM и сырого запроса с полным JOIN несущественная.
Возможно, даже если мы выигрываем за счет прямого запроса SQL, далее время тратится на создание queryset'а вручную.

## Пример 3

Пробовал заменять ORM на прямой SQL в местах, где нужно просто получить небольшой объем информации, как например, получить список брендов для отправки на фронтенд для дальнейшего использования в качестве фильтра

1. Пример изначального запроса с использованием ORM

```python
def select_client1_brands():
 """
 Названия брендов для Клиента
 """
 all_brands = (
  list(client1_brands
  .union(platform1_categories_brands)
  .union(platform2_categories_brands))
 )
 query = (
  sa.select([brand.c.brand_name, brand.c.brand_id])
  .select_from(brand)
  .where(brand.c.brand_id.in_(all_brands))
 )
 return query
```

2. Пример преобразованного запроса

```python
def select_client1_brands():
 """
 Названия брендов для Клиента
 """
 query = """
  SELECT brand_name, brand_id 
  FROM brand WHERE brand_id IN (
    SELECT brand_id 
    FROM client1_brands 
    UNION 
    SELECT brand_id 
    FROM platform1_categories_brands 
    UNION SELECT brand_id 
    FROM platform2_categories_brands
  )
 """
 return query
```

Далее, если запустить 2 функции выше в цикле на множественное выполнение, то получим следующие результаты:

1. 116 мс +/- 11 мс.
2. 98 мс +/- 12 мс.
Очевидно, что использование прямого SQL запроса немного выигрывает, хотя результат будет более-менее заметен только при очень большом количестве обращений.

## Выводы

В целом по всем примерам ORM начинает проигрывать написанным вручную SQL запросам только тогда, когда идет множество отдельных обращений к БД. В таких случаях ORM нужно доп.время чтобы "скомпилировать" (в документации SQLAlchemy используют слово `compile`) код в реляционную раскладку (что происходит в несколько этапов, например, параметры "встраиваются" на отдельном шаге).
Для единичных, пусть даже больших и сложных запросов, разница по времени несущественная.
Я думаю, что проблема, описанная в этом занятии характерна для людей, которые занимаются в Web-разработке, в то время как я в основном пишу/поддерживаю ETL скрипты для данных.
Так или иначе, мне приходится взаимодействовать с ORM (`SQLAlchemy`) так как система контроля миграций (`alembic`) основана на ней.
Но за пределами этого изначально мне было значительно проще использовать "сырой" SQL запрос, так как на нем легче сформулировать сложную логику с множеством джойнов, оконных функций и т.д., плюс в результате работает немного быстрее, чем через ORM.
ORM насколько я вижу, вообще не дает практически никакого выигрыша (хотя в `SQLAlchemy` есть множество других полезных инструментов, например сессии).
Что касается передачи параметров, современные драйверы для БД, вроде `psycopg2` позволяют легко и безопасно параметризовать SQL запрос.
Когда-то много использовали библиотеку `pandas` для составления клиентских отчетов, но со временем стало понятно, что практически всю ее работу при желании можно переместить на БД, OLAP БД вроде `Clickhouse` очень хорошо справляются с этим (мне кажется, `pandas` тут выступает схожим образом с какой-нибудь ORM, позволяя реализовывать логику манипулирования данными из языка Python).
Теперь мы понимаем, что логику манипулирования данными стоит максимально переносить на БД.
БД справляется с этим намного лучше, особенно когда дело касается параллельных запросов.
