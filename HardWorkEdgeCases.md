# Hard Work - Справляемся в краевыми случаями

## Мои примеры

### Пример 1.1

Имеем функцию, которая должна рассчитать размер скидки на продукт по данным, полученным из парсинга приложения доставки в БД.

```python
import numbers


def calculate_discount_percent(
    price, 
    price_before_discount, 
    is_app_gives_discount_info=True,
) -> float:

    # Переданы корректные значения информации по ценам
    if any([
        not isinstance(price, numbers.Number),
        not isinstance(price_before_discount, numbers.Number),
    ]):
        raise TypeError("prices must be numeric")

    # Парсер или площадка не могут отавать информацию по скидкам
    if not is_app_gives_discount_info:
        return 0.0
    
    # Парсер отдал значение скидки больше, чем до скидки
    if price > price_before_discount:
        log.warn("Found price before discount is less than price")
        return 0.0
    
    # Проверка на 0 у значения до скидки
    if price_before_discount <= 0:
        return 0.0
    
    return round((price_before_discount - price) / price_before_discount, 2)
```

Так как информация, полученная после парсинга `HTML` странички бывает не слишком надежной, а сам парсер зачастую не содержит проверок информации перед записью, нужно проверять информацию перед помещением в БД, поэтому проверки в виде множества условных операторов необходимы.

### Пример 1.2

Классический пример, если нужно реализовать (дву-) связный список, тогда краевыми случаями
будут каждый случай, когда мы имеем дело либо с действием над "головой", "хвостом" или над пустым списком. Например, удаление:

```python
def delete(self, val: T, all=False) -> None:
    node = self.head
    parent = None  # here we save node parent
    is_first_found = False

    while node is not None:
        if is_first_found and not all:
            return None

        # if node has no parent then it's head
        if (node.value == val) and (parent is None):
            self.head = node.next
            node = node.next
            is_first_found = True
            continue

        elif (node.value == val) and (parent is not None):
            parent.next = node.next
            node = node.next
            is_first_found = True
            continue

        parent = node
        node = node.next

    # if node has no next then it's tail
    if parent.next is None:
        self.tail = parent
    else:
        self.tail = parent.next
    return None

    # empty list
    if self.head is None:
        self.tail = None
        return None
```

Каждый случай необходимо рассматривать отдельно и созавать соответствующий блок кода с `if`.
(на курсе также рассматривается способ, облегчающий эти действия - создание пустого `DummyNode`)

### Пример 1.3

Код ниже имеет дело с запросами в БД, по информации из которой нужно принять решение об отправке в бот сообщения о наличии проблем. Сверяется наличие и правильность ко заранее установленным площадкам.
Имеют место сделующие краевые случаи:

1. К БД нет подключения.
2. Сверка по приложениям показывает наличие приложения, которого раньше не было (не отслеживаемое приложение).
3. По площадке почему-то нет записи о последней даты обновления (резульат либо сбоя в другом месте прораммы, либо из-за п.2)
4. Пост-запрос на эндпоит для бота-алертов не проходит

```python
def check_time_diff(self, retries=3):
    with self.database_connection.get_connection() as connection:
        with connection.begin():
            results = connection.execute(select_last_raw_updates())
    
    # 1. БД не возвращает данные
    if not results and retries <= 0:
        log.error("No data recived from DB)
        return

    if not results:
        log.warn("No data recived from DB, trying again tries=%s", retries)
        sleep(60)
        self.check_time_diff(retries = restires - 1)
        return
    # 1. Пытаемся снова, до 3 попыток по умолчанию

    current_time = datetime.datetime.utcnow()
    alert_text = f"*ALERT*: The database time is: _{current_time.strftime('%d.%m %H:%M')}_\nMore than an hour without updates:\n"
    text_is_changed = False

    for row in results:
        platform, db_time = row

        # 2. Сверка по приложениям показывает наличие приложения,
        # которого раньше не было (не отслеживаемое приложение).
        if platform not in self.alert_trackers:
            self.alert_trackers[platform] = {
                "last_alert_time": None,
                "next_alert_delay": self.initial_alert_delay
            }
            log.warn("Detected a new platform %s", platform)
        # 2

        if abs((current_time - db_time).total_seconds()) > ALERT_PERIOD_SECONDS:
            # 3. По площадке почему-то нет записи о последней даты обновления
            if self.alert_trackers[platform]["last_alert_time"] is None:
                self.alert_trackers[platform]["last_alert_time"] = current_time
                continue
            # 3. Пропускаем до следующей проверки

            if (current_time - self.alert_trackers[platform]["last_alert_time"]).total_seconds() > \
                self.alert_trackers[platform]["next_alert_delay"] * ALERT_TIME_INCREASE_MULTIPLIER:
                alert_text += f' - *{platform}*, last update _{db_time.strftime("%d.%m %H:%M")}_\n'
                text_is_changed = True

                self.alert_trackers[platform]["last_alert_time"] = current_time
                self.alert_trackers[platform]["next_alert_delay"] *= 2

        else:
            self.alert_trackers[platform]["next_alert_delay"] = self.initial_alert_delay

    alert_message = {"text": alert_text}
    if text_is_changed:
        # 4. Пытаемся отправить сообщение
        tries = 3
        while tries > 0:
            try:
                requests.post(self.slack_webhook_url, data=json.dumps(alert_message))
                return
            except ServerException:
                tries -= 1
        log.error("Could not send message to Bot")


```

### Пример 1.4

Имеем функцию для записи данных парсера сайта доставки в БД.
Изначально, в нашей архитектуре, "сырые" данные пишутся в БД в виде JSON файла.
Ввиду некоторых ограничений при записи, необходимо проверять возможность записи этих данных в одну строку.

Для проверки возможности записи очередной партии данных о продукте, используем функцию, которая, в зависимости от указанных констант:

1. В зависимости от формата данных, выбираем верхнюю границу размера для одной записи
2. Убедиться, что размер партии данных задан верно
3. Убедиться, что размер патрии данных не больше лимита, если он больше, то пробуем разбить на подгруппы.
4. Наконец, проверяем возомжность записи.

```python
MAX_CAPACITY = 50
LONG_DATA_FORMAT_MAX_CAPACITY = 35
MAX_BATCH_SIZE = 10

def can_accept_data_batch(
    data_batch_size: int, 
    product_data_id: int,
    current_batches: dict[int, list[int]],
    is_special_data_format: bool,
) -> bool:

    # Задаем максимальный размер ячейки в зависимости от формата данных
    capacity_limit = (
        LONG_DATA_FORMAT_MAX_CELL_CAPACITY 
        if is_special_event 
        else MAX_CELL_CAPACITY
    )

    # Проверям правильность данных по размеру партии
    if not isinstance(data_batch_size, int):
        return False
    if data_batch_size < 1:
        return False

    # Разделяем большие порции данных на подгруппы, если это необходимо
    if data_batch_size > MAX_BATCH_SIZE:
        num_subgroups = -(-data_batch_size // MAX_BATCH_SIZE)  # разделяем на подгруппы
        subgroups = (
            [MAX_BARCH_SIZE] * (num_subgroups - 1) 
            + [data_batch_size % MAX_BARCH_SIZE or MAX_BARCH_SIZE]
        )
    else:
        subgroups = [party_size]

    # Проверяем доступность для записи данных для указанного продукта
    product_data_batches_size = sum(current_batches.get(product_data_id, []))
        for subgroup_size in subgroups:
            if product_data_batches_size + subgroup_size > capacity_limit:
                return False
            product_data_batches_size += subgroup_size

    return True
```

## Новые идеи после изучения "43) Как справляться с краевыми случаями"

При подходе к занятию, честно пытался вывести типичные краевые случаи, которые нахожу в своей работе до изучения материала.
После изучения материала понимаю, что типичным решением таких проблем является как раз "повышение уровня абстракции". В то время как я зачастую просто решаю такие проблемы "в лоб", добавляя новые проверки и обработки исключений. Причина, вероятно, в том, что я нечасто имею дело с большими иерархиями классов и "правильным" ООП в своей работе.

Насколько я рассматриваю типичные случаи большого количества краевых условий,
тут действия нужно планировать, исходя из 2 параметров:

- Насколько вероятно добавление новых краевых случаев?
- Насколько вероятны проявление этих краевых случаев на практике (это во многом обсуждается в материале занятия).

Первый пункт для меня актуален также, как и второй, потому что во многих случаях можно быть увереным, что вероятность того, что при парсинге названий чего-либо размер данных увеличится на порядок, довольно низкая (и вероятно это значит, что с данными что-то не так).
Поэтому в целом из предложенных в занятии решений мне кажется, что подход "ограничения функциональности" мне ближе всего. Потому что создание универсальных структур более время затрано и сложно, однако если мы более-менее уверены, что не предвидится значительных изменеий (если им неоткуда взяться, хотя тут конечно, может иметь место самообман:)).

Ну и дополнительно, вероятно более узкоспециализированные функции могли мы мне позволить обрабатывать различные "краевые" (например, пустые данные из БД) сиутации более эффективно.


## Выводы

В целом, естественно, большое количество постоянно "уточняющихся" условий при создании кода это значительная головная боль. Классический совет с "решением проблемы на более высоком уровне абстракции" не только может приводить к неясному и запутанному коду, но и, как мне кажется не так часто встречается на практике. 

Гораздо более распространенный подход в реальности, когда разработчики не слишком профессиональны - это справляться с краевыми случаями по мере их поступления, в виде заплаток, дополнительных условных операторов, блоков try-catch и т.д., часто также нарушая принцип `open-close`. 

Самое важное, что я вынес для себя в этом занятии, что этот стандартный совет как справляться с такого рода проблемой по крайней мере не едиственный, и теперь могу держать в голове пару других подходов.

Ну и в очередной раз упоминается подход к решению, основанный на понятиях из абстрактной алгебры/теории групп. Что лишний раз доказывает, насколько математика может быть важна при проектировании программ и что изучение ее даже более абстрактных областей может дать преимущества в практических областях.