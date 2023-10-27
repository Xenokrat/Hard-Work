# Hard Work - Про раздутость кода часть 2

## Пример 1

В одном из скриптов для передачи данных в клиентские БД имеем класс `ConfigParserYAML`.

При создании экземпляра класса, в конструкторе мы пытаемся сразу:

1. Понять какой конфигурационный файл передан (если никакой, то пытаемся использовать дефолтный).
2. Проверяем наличие в открытом `YAML` конфиге параметра дат -- можгут быть переданы:

    - Конкретная дата `date`
    - Диапазон дат `date_range`
    - Ничего, тогда по умолчанию берем вчерашний день

Указанный ниже класс дополнил комментариями:

```python
class ConfigParserYAML:
    def __init__(self, config_file: str = "config.yaml") -> None:
        self.config = None
        self.stages = None
        self.dates = None

        # Читаем конфигурационный файл, если он указан
        # в противном случае используем стандартный config.yaml в корне проекта

        config_file_path = os.path.abspath(config_file)
        log.info(config_file_path)
        try:
            with open(config_file_path, "r") as configfile:
                parsed_yaml = yaml.safe_load(configfile)
        except FileNotFoundError:
            log.error("Config file not found")
            sys.exit(-1)
        self.config = TasksConfig(**parsed_yaml)

        # Ищем в конфиге параметры `date` или `date_range` для укзания даты/дат
        # для составления отчетов, если таких нет, формируем отчет за вчера

        if date_range := parsed_yaml.get("date_range"):
            assert len(date_range) == 2, "Should be 2 args for date_range"
            self.dates = self.get_daterange(*date_range)
            return

        if dates := parsed_yaml.get("dates"):
            self.dates = dates
            return

        if self.dates is None:
            yesterday = (datetime.now() - timedelta(days=1)).date()
            log.info(f"Date set as {yesterday.strftime('%Y-%m-%d')}")
            self.dates = [yesterday]

```

## Пример 2

Имеем функцию `execute_stage`, которая должна быть синхронной, при этом она отвечает за запуск цикла подзадач, который выполняется асинхронно. Для этого выделяем прямо внутри функции подфункцию, которая будет асинхронной и выполнять позадачи, а в основной запускаем эту функцию в асинхронный контекст.
Добавлены комментарии:

```python
def execute_stage(
    stage: Stage,
    params: ParametersDataclass
) -> set[tuple[SQLResult]]:
    log.info(f"EXECUTING STAGE: %s", stage)

    # Данная функция создает асинхронный пул соединений к БД
    # и выполняет переданные задачи асинхронно

    async def _execute_stage() -> Awaitable:
        async with get_pool_asynch() as pool:
            res = await asyncio.gather(*[
                execute_task(task, pool, params)
                for task in stage["tasks"]
            ])
        return set(res)
    
    # возвращаем результат уже в синхронном контексте
    return asyncio.run(_execute_stage())
```

## Пример 3

Имеем функцию, которая выполняет запросы в асинхронном контексте.
В определенный момент, появилась потребность собирать статистику по скорости выполнения запросв, для этого включаем в код небольшой кусочек, измеряющий время работы, дополнительно возвращаем полученный результат:

```python
async def execute_single_query(
    subtask: str,
    conn: Conn,
    params: ParametersDataclass
) -> SQLResult, dict[str, int]:
    query = convert_subtask_name_to_query(subtask)

    async with conn.cursor() as cursor:
        # измеряем время выполнения запроса для сбора статистики
        start_time = time.time()
        await cursor.execute(query, params.dict())
        res = tuple(await cursor.fetchall())
        end_time = time.time()
        elapsed_time = end_time - start_time
        log.info(f"EXECUTE SUBTASK: %s, time spent %s", subtask, round(elapsed_time, 2))

    # Дополнительно возвращаем словарь: {"название подзадачи": время выполнения}
    return res, {subtask: elapsed_time}
```

Вероятно, можно было также решить созданием какого-нибудь декоратора, но этот вариант более простой.

## Пример 4

Кусочек программы, обрабатывающий UI элемент, в котором можно:

1. Добавить новую запись в таблицу
2. Редактировать уже существующую запись

```python
  def add_or_edit_command(self) -> None:
        text = self.ui.line_edit_command.text().strip()
        
        # Проверяем, получен ли текст в поле ввода
        if text:
            selected_item = self.ui.col_commands.currentItem()
            
            # Если при этом выбран существующий элемент, редактируем его
            if selected_item:
                selected_item.setText(text)

            # Если нет, создаем новый
            else:
                item = QListWidgetItem(text)
                self.ui.col_commands.addItem(item)

            self.ui.line_edit_command.clear()
            self.ui.col_commands.clearSelection()
```

Добавил комментарии, т.к. мне кажется, что эти блоки не вынести в отдельную функцию, при этом они реализуют 2 варианта поведения в зависимости от действий пользователя.

## Пример 5

функция для парсинга комманды бля бота в мессенджере, содержит следующие логические блоки:

1. Устанавливаем соединение (`ack`)
2. Проверяем получена ли в теле запроса команды дополнительная информация для запроса.
3. Делаем запрос в БД и возвращаем информацию пользователю.

В учетом выделенных выше блоков, добавим следующие комментарии:

```python
@app.command("/check_app_parsing")
def app_parsing_state_command(ack, say, logger, body):
    # Сообщаем боту, что соединение с ботом/БД установлено
    ack("Fetching data from DB")

    # Проверяем, если пользователь передал дополительные условия для запроса
    app = country = app_filter = country_filter = ""
    if body["text"]:
        try:
            app = body["text"].split(",")[0].strip()
            app_filter = f"AND darkstore_platform = '{app}'" if app != "all" else ""
            logger.info(f"check_app_parsing: APP {app}")
        except IndexError:
            pass
        try:
            country = body["text"].split(",")[1].strip()
            country_filter = (
                f"AND darkstore_country = '{country}'" 
                if country != "all" else ""
            )
            logger.info(f"check_app_parsing: COUNTRY {country}")
        except IndexError:
            pass
    log.debug(f"App filter {app_filter}")
    log.debug(f"Country filter {country_filter}")
    
    # Запрос в БД и ответ
    try:
        result = get_app_data(app_filter, country_filter)
        logger.info(result)
        say(result)
    except Exception as e:
        logger.error(e)
```

## Выводы

Умение видеть логические блоки в отдельных функциях позволяет лучше понимать, какие действия с данными и их преобразования происходят в программе в процессе ее работы.

Хотя всегда думаю, нужно спрашивать себя, если эти логические блоки можно выделить внутри функции, не можно ли выделить их в отдельные функции, чтобы было проще переиспользовать их и тестировать. Однако это не всегда возможно, или легко.

Впредь, если буду видеть в функциях несколько логических блоков, буду оставлять комментарии, чтобы задачи функции были более понятны другим программистам.

Чувтствую некоторое облегчение, что иногда нормально не выделять какие-либо блоки кода отдельно, когда это не имеет смысл, при этом это нужно просто компенсировать указанием логики в комментах/доках.
