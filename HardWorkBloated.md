# Hard Work - Про раздутость кода

## Пример 1

### П1.Было

В одной из первых версий симуляции Машины Тьюринга, была следующая проблема:
Лента в машине потенциально бесконечная (на концаптуальном уровне по крайней мере).

На практике, создавать бесконечную, или даже большую ленту нецелессобразно, поэтому задается начальная лента (т.е. обычный список под капотом) из 30 ячеек, затем если в ходе работы программы индекс выходит за пределы, лента незаметно для пользователя увеличивается в размерах:

```python
 def check_tape_expantion(self) -> None:
    if self.current_tape_cell + 1 >= len(self.tape):
        self.tape.extend(["_"] * 10)
    elif self.current_tape_cell <= 0:
        self.tape = ["_"] * 10 + self.tape
        self.current_tape_cell += 10
    else:
        return
```

Вторая мысль, которая пришла мне в голову гораздо позже: очень легко случайно или специально, написать программу, которая будет бесконечно увеличивать размер ленты (ну или хотя бы делать его очень большим).

Появился отдельный метод для валидации:

```python
MAX_TAPE_LENGTH = 1000
...
def validate_tape_length(self) -> None:
    if len(self.tape) >= MAX_TAPE_LENGTH:
        raise NonValidTape("Exeeded max tape length")
```

Очевидно, что это не очень оптимальный способ для проверки, так как:

- Во-первых: `check_tape_expantion` по-хорошему единственный метод, который может менять размер ленты (точно только увеличивать его, для оптимизации можно добавить метод, уменьшающий размер ленты, если ячейки не используются).
- `validate_tape_length` нужно не забыть вызывать каждый раз после использования первого метода.

### П1.Стало

Используем самый простой подход -- объединим методы в один

```python
MAX_TAPE_LENGTH = 1000
...

def check_tape_expantion(self) -> None:
    if len(self.tape) + 10 >= MAX_TAPE_LENGTH:
        self.stop_program_exec()
        logger.warning("Exeeded tape length")
        return

    if self.current_tape_cell + 1 >= len(self.tape):
        self.tape.extend(["_"] * 10)
    elif self.current_tape_cell <= 0:
        self.tape = ["_"] * 10 + self.tape
        self.current_tape_cell += 10
    else:
        return
```

теперь валидация длины ленты неразрывно связана с ее увеличением. Кроме того, не обязательно вызывать краш программы, можно просто приостановить выполнение и вывести предупреждение пользователю.

## Пример 2

Управление параметрами при выполнении программы при помощи текстовых конфигов и при помощи CLI параметров.

### П2.Было

Программа для выполнения отчетов с данными имеет интерфейс настройки через `.yaml` файл:

```yaml
dates:
  - 2023-08-01
  - 2023-08-02
apps:
  - app1
  - app2
```

Также поддерживается возможность настроить параметр при запуске программы через терминал:

```bash
python main.py --apps="app1,app2" --dates="2023-08-01,2023-08-02"
```

Второй вариант более приоритетный, так как конфигурационный файл нужен для ежедневного использования, а указание параметров в консоли -- для частных случаев использования

Параметры задаются в первом случае классом:

```python
@dataclass
class ParametersDataclass:
    param1: int = 1
    param2: int = 2
    date: str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    date_next: str = datetime.now().strftime("%Y-%m-%d")

```

Во втором случае параметры парсятся модулем `argparse` и дальше передаются как словарь в ходе работы программы.

```python
args = parser.parse_args()
```

Затем каждый раз, когда нужно использовать параметры в ходе работы программы, мы проверяем, не нужно ли обновить/дополнить эти параметры

```python
async def execute_single_query(
    subtask: str,
    conn: Conn,
    params: ParametersDataclass,
    args: dict[str, str],
) -> SQLResult:
    query = convert_subtask_name_to_query(subtask)
    
    # Проблемное место
    query_args = params.dict()
    query_args.update(args)
    async with conn.cursor() as cursor:
        await cursor.execute(query, query_args)
        res = tuple(await cursor.fetchall())
    return res
```

Очевидно, что способ не очень удобный, так как нужно всегда при использовании параметров обнолять их. Можно конечно вынести это в отедьную функцию, но ее также нужно будет вызвать каждый раз при использовании параметров.

### П2.Стало

Возможно сразу перед запуском основной части программы, модифицировать класс `ParametersDataclass` обновив его всеми нужными значениями.

```python
class ParametersDataclass:
    param1: int = 1
    param2: int = 2
    date: str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    date_next: str = datetime.now().strftime("%Y-%m-%d")
    ...

    # Добавим метод для обновления
    def update_params(self, new_params: dict[str, str]):
        for param, val in new_params.items():
            self.getattribute(param) = val
```

Тогда после создания экземпляра `ParametersDataclass` просто вызываем `update_params`.
Теперь пример можно упростить:

```python
async def execute_single_query(
    subtask: str,
    conn: Conn,
    params: ParametersDataclass,
) -> SQLResult:
    query = convert_subtask_name_to_query(subtask)
    
    async with conn.cursor() as cursor:
        await cursor.execute(query, params.dict())
        res = tuple(await cursor.fetchall())
    return res
```

## Пример 3

Внути программы имеется механизм, который может увеличивать ресурсы на сервере в ходе работы скрипта, если это требуется.
Как можно управлять работой такого механизма?

### П3.Было

Изначально самое прямолинейное решение -- в начале при запуске определенных работ, требующих ресурсов, запускаем функцию, которая делает увеличение ресурсов.
Одновременно с этим, ставим булевый флажок, что произошло увеличение ресурсов, чтобы впоследствии знать, что их нужно высвободить.

```python
def upscaling() -> bool:
    """Увеличение рерсусов при помощи POST запроса"""

    response = requests.patch(
        scale_url,
        json=upscale,
        auth=(KEY_ID, KEY_SECRET),
    )
    assert response.status_code == 200
    min_total_memory_response = response.json()['result']['minTotalMemoryGb']
    max_total_memory_response = response.json()['result']['maxTotalMemoryGb']
    log.info("UPSCALE API: minTotalMemoryGb -> %s",
                min_total_memory_response)
    log.info("UPSCALE API: maxTotalMemoryGb -> %s",
                max_total_memory_response)
    return True
```

```python
is_server_upscaled = upscaling()
for day in program.dates:
    execute_program(program, param_obj)
    ...
if is_server_upscaled:
    downscale()
```

Этот код вероятно можно считать "раздутым", так как управление ресурсами рассредоточено по программе:

- Нужно не забыть вызвать увеличение ресуса в начале программы
- При возникновении проблем, нужно проверять текущий статус ресурсов, и уменьшать их обратно при необходимости
- В конце работы вызвать уменьшение ресурсов.

По крайней мере с поледними 2 проблемами, можно справиться, создав конекстный менеджер, который также позволит держать весь код управления ресурсами в одном месте.

### П3.Стало

```python
@contextmanager
def upscaling_downscaling() -> None:
    try:  # noqa
        response = requests.patch(
            scale_url,
            json=upscale,
            auth=(CLICK_KEY_ID, CLICK_KEY_SECRET),
        )
        assert response.status_code == 200
        ...
        yield
    finally:
        try:
            response = requests.patch(
                scale_url,
                json=downscale,
                auth=(CLICK_KEY_ID, CLICK_KEY_SECRET),
            )
        except Exception as e:
            log.error(e)
            raise e
```

Теперь достаточно для любого процесса, который требует выделения ресурсов, просто обернуть его в данный контекстый менеджер, который также позаботиться об уменьшении ресурсов на серевере при окончании работы скрипта и даже в случае возникновения исключений.

```python
with upscaling_downscale():
    for day in program.dates:
        param_obj.date = day.strftime("%Y-%m-%d")
        param_obj.date_next = (day + timedelta(days=1)).strftime("%Y-%m-%d")
        execute_program(program, param_obj)
```

## Выводы

На первом примере, отчетливо видно, насколько важно планировать заранее дизайн программы, чтобы ключевые характеристики были продуманы заранее, и не было необходимости добавлять новые правила "на лету".
В целом, "раздутость" кода как раз является признаком плохо продуманного дизайна, и, как следствие, общей хрупкости системы и узязвимости к внесению изменений.
Главными способами управлять "раздутостью" кода является объединение логических частей программы в одном месте, ограничение состояний в пределах специально выделенных классов, использование контекстных менеджеров - все эти средства позволяют разделить программу на логические части и значительно проще рассуждать о ее работе и возможных ошибках.