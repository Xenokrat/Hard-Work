# Hard Work - Об опасности стандартных подходов

## Оценка структур данных в коде проекта (или их отсутствие)

На практике на работе имеем вроде бы классическую схему

- `FastAPI` на бэкэнде, с БД в виде `Clickhouse` (может не совсем стандартно).
- На фронтэнде JSовский `Vue`
- Передача данных через `JSON`

Тут ничего не могу сказать конкретного про то, насколько это надежный формат в целом, но по крайней мере `JSON` довольно прозрачный формат для сериализации, кроме того, исходя из характера приложения (дашборд с визуализациями данных), в целом в 95% случаем осуществляются только `READ` запросы и никакие ID практически не используются.

Вероятно, более надежный вариант это фулстек фреймворк (`Django | DRF`)

## Идеи для REST API без id в качестве идентификаторов

### Пример 1

Есть сервис, предоставляющий отчеты с данными по продажам клиента исходя из запросов пользователя

На текущий момент:

Эндпоинт состоит из {наш_url}/reports/идентификатор_uuid_клиента/id_отчета

На странице отчета пользователь вводит период для выгрузки данных, при отправке формируется POST запрос.

Как можно изменить структуру:

- Эндпоинт: {наш_url}/reports/{country_x_sales_report | country_y_sales_report}
- Полноценная аутентификация

`Clickhouse` повзволяет удобно выстраивать пайплайны для данных прямо на уровне БД. Возможно решение тогда - заранее пред-собирать отчеты и хранить их в мат.вью (которые Клик умеет как раз автоматически обновлять без вмешательства).
В запрос остается подстваить только выбранный диапазон дат.

Тогда остается передать только диапазон дат, плюс некоторые интересующие пользователя фильтры.

```JSON
{
  "date_start": "2023-01-01",
  "date_end": "2023-02-01",
  "country": ["Russia"],
  "brand": ["Coca-Cola"]
}
```

В таком виде SQL нужен минимально, и как указано в посте про ORM: "SQL, по большому счёту, создан для OLAP, для всяческих аналитических задач и сложных запросов".

### Пример 2

Если взять за пример дипломный проект автопарка, то можно в REST избавиться например от айдишек автомобилей

Эндпоинт: /vehicles/{licensePlate}

```json
{
  "licensePlate": "а123вф",
  "make": "Toyota",
  "model": "Camry",
  "year": 2022
}
```

(/vehicles/а123вф)

Аналогичным образом мы будем находить записи (но номерному знаку) для PUT/PATCH/DELETE запросов.
В части хранения как раз таких данных (не точек поездки), вероятно лучше использовать `MongoDB` как JSON-ориентированную БД.

## Выводы

В своей работе пока не сталкивался с закрытми форматами сериализации. Во ситуациях когда нужна сериализация, мы имеем дело с `JSON` или `XML`. Взял на заметку идею о том, чтобы не использовать айдишники в составе REST API, ведь это не только похоже на использование глобальных переменных, но и также дает косвенную информацию (например об общем количестве записей, или о том, что если номер id пропущен, какой-то элемент был удален), которую мы не очень хотим раскрывать.
В целом, однако, у меня ощущение, что при общем стремлении к микросервисам, потребность в сериализации/десериализации весьма высока и избежать использования `JSON` в большинстве случаев практически невозможно.