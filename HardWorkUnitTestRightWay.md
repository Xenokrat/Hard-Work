# Hard Work - Как правильно готовить юнит-тесты

## Пример 1

Если есть функция, которая должна получить название файла и вернуть запрос из него.

Первоначально проверялось только то, что возвращается корректный запрос из файла.

```python
def test_correct_convert_subtask_name_to_query() -> None:
    assert (
        qh.convert_subtask_name_to_query("test_query")
        ==
        "SELECT %(cnt)s;\n"
    )
```

Теперь опишем свойства:

- Уровень: юнит-тест
- Если название файла передано корректно, возворащается запрос из файла.
- Первое свойство должно быть верно для любых файлов.
- Если название файла некорректно, поднимается корректное исключение.

```python
correct_query_map = {
    "test_query1": "SELECT %(cnt)s;\n",
    "test_query2": "SELECT * FROM test_table;\n",
    "test_query3": "SELECT user_id, user_name FROM users WHERE 1=1;\n",
}
def test_correct_convert_subtask_name_to_query() -> None:
    for query, result in correct_query_map.items():
        assert (qh.convert_subtask_name_to_query(query) == result)

def test_correct_convert_subtask_name_to_query() -> None:
    with pytest.raises(FileDoesNotExist)
        qh.convert_subtask_name_to_query("incorrect_test_query")
```

## Пример 2

Для тестирования асинхронных запросов в `Clickhouse` использовали `Docker` контейнер
с бд, чтобы проверить, что запросы выполняются корректно.

При этом проверялись вообще все запросы (на пустых таблицах в поднимаемом контейнере).

```python
# Кусочек кода
@pytest.fixture
def process_config(self):
    p_config = MagicMock()
    dsn = "clickhouse+asynch://username:password@clickhouse:9000/db1"
    a_engine = create_async_engine(dsn)
    metadata = MetaData(a_engine)
    p_config.get_click_async_metadata.return_value = metadata
    p_config.get_click_async_engine.return_value = a_engine
    p_config.get_date.return_value = datetime.strptime("2023-06-01", "%Y-%m-%d")
    yield p_config

def test_agg_en_stock_with_tmp_tables(self, process_config) -> None:
    agg_en = AggregationStockEN(process_config)
    asyncio.run(agg_en.create_tmp_category_table())

def test_agg_en_no_stock_with_tmp_tables(self, process_config) -> None:
    agg_en = AggregationNoStockEN(process_config)
    asyncio.run(agg_en.create_tmp_category_table())
```

Если здесь подумать, нам не следует проверять все запросы, ведь мы не тестируем то, что SQL выполняется правильно. Тогда можно последовать двумя путями:

- Уровень: интеграционный тест
- Определим свойство как - асинхронные запросы успешно выполняются, тогда достаточно проверить, что хотя бы один запрос выполняется (оставим единсвенный запрос).

```python
@pytest.fixture
def process_config(self):
    p_config = MagicMock()
    dsn = "clickhouse+asynch://username:password@clickhouse:9000/db1"
    a_engine = create_async_engine(dsn)
    metadata = MetaData(a_engine)
    p_config.get_click_async_metadata.return_value = metadata
    p_config.get_click_async_engine.return_value = a_engine
    p_config.get_date.return_value = datetime.strptime("2023-06-01", "%Y-%m-%d")
    yield p_config

# Dummy запрос, достаточно понять, что (пустой) результат возвращается без ошибок
def test_correct_query_with_tmp_tables(self, process_config) -> None:
    query_result = TestTask(process_config)
    asyncio.run(agg_en.create_tmp_category_table())
    assert isinstance(query_resutl, tuple)
```

Второй подход - так как по сути за запрос отвечает внешняя библиотека, то нет смысла тестировать чужой код (хотя это может быть рискованно) и достаточно лишь метода пристального взгляда для того, чтобы убедиться, что мы корректно используем эту библиотеку.

## Пример 3

Изначальный тест:
Проверяем, что Питоновская функция корректно валидирует тип передаваемого агрумента ка `Int`.
После этого проверяем, что класс `InputTape` корректно инициирован с списком только `Int` значений.

```python
class TestValidate:
    def test_validate_int_data(value: int) -> None:
        assert validate_int_data(5) == 5

    def test_validate_int_data_fail(value: int) -> None:
        with pytest.raises(TypeError):
            validate_int_data('5')


class TestInputTape:
    def test_init(self) -> None:
        data = [1, 2, -5]
        itape = InputTape(data)
        assert itape._InputTape__data == [1, 2, -5]

    def test_init_fail(self) -> None:
        data = ['1', '2', '-5']
        with pytest.raises(TypeError):
            InputTape(data)

```

Выделим свойства:

- Уровень: юнит-тест
- Функция `validate_int_data` возвращает значение только для `Int`, в других случаях вызывает `TypeError`.

Достаточно ли двух тестов, один из которых передает `Int` значение и второго теста, который передает любое отличное? Я думаю, что для такой простой функции будет достаточно и такой проверки.
Как альтернативный варинат, можно рассмотреть фазз-тестирование -> поток значений должен приводить только к возвращению `Int` значения или к `raise TypeError`.

Если вдуматься, то свойство получения корректно инициализированного класса `InputTape` зависит от использования `validate_int_data`, и не относится к функционалу самого класса, поэтому тестирование его конструктора лишнее, и мы можем сократить все до:

```python
class TestValidate:
    def test_validate_int_data(value: int) -> None:
        assert validate_int_data(5) == 5

    def test_validate_int_data_fail(value: int) -> None:
        with pytest.raises(TypeError):
            validate_int_data('5')
```

## Пример 4

В симуляции RAM-машины, имеем функцию, которая проверяет, что в программе встретился deadlock.

В первоначальной версии просто вручную подобрал программу, которая приводит к дедлоку, убдились, что корректно вызывается исключение.

```python
def test_deadlock(self, mock_program: Program) -> None:
    mock_program.command_str_list = [
        "deadlock:",
        "LOAD 2, [0]",
        "JNZ [0], deadlock",
        "WRITE",
        "HALT"
    ]
    with pytest.raises(DeadlockError):
        mock_program.exec_many_steps()
```

Более формальный подход.
Выразим свойства:

- Уровень: юнит-тестирование
- Из множества вводимых пользователем программ, все программы, имеющие дэдлок корректно обрабатываются.
- Все корректные программы не вызвают исключение с дедлоком.

Предлагаемое решение:

- Самый минимум, нужно также убедиться, что хотя бы 1 правильная программа не вызывает дедлок.
- Возможно фазз-тестирование, нужен поток рандомных команд. Однако проверить, что все последовательности команд, приведшие к дэдлоку корректны (и все не приведшие также корректно отработали).
- Проверять десятки случаев, как в пункте выше, малореально. Возможно достаточно метода пристального взгляда.

## Пример 5

Проверяем, что программа, состоящая из описания в `YAML` файле, возвращает корректный результат.
В изначальном варианте, придумал `dummy` задачи для программы, и проверял возвращают ли они при таких предпосылках

```python
@pytest.fixture
def query_params() -> None:
    return qh.ParametersDataclass(
        cnt=5, cnt2=3,
    )

@pytest.fixture
def program() -> None:
    return qh.Program(
        dates=[1, 2],
        stages=[
            {
                "stage": "stage_name1",
                "tasks": ["test_task1", "test_task2"]
            },
            {
                "stage": "stage_name2",
                "tasks": ["test_task2", "test_task1"]
            },
        ]
    )

def test_execute_program(program: qh.Program,  query_params: qh.ParametersDataclass) -> None:
    res = qh.execute_program(program, query_params)
    assert res == [
        (((5,),), ((3,),)),
        (((3,),), ((5,),)),
        (((5,),), ((3,),)),
        (((3,),), ((5,),))
    ]

```

Свойства

- Уровень: интеграционный тест
- При корректно заданный командах, программа возвращает корректный результат.

Такое свойство получается очень расплывчатым, при попытке как-то конретизировать его мы "проваливаемся" обратно на уровень юнит-тестов, а это не то, что нужно.

Возможное решение: сформулировать правило, по которому можно расчитать, к какому значению должен привести каждый набор команд и прогнать через программу.

Но здесь возникает парадокс, нам как бы и нужна программа изначально, чтобы расчитать подобный результат.
Опять таки, мы не можем вручную задать много возможных комбинаций программ, при этом еще и зная, к какому результату они должны приводить.

Еще идеи для решения:

- Фазз тестирование потоком корректных команд - не проверяем результат (заранее не знаем), но зато проверяем отстствие неожиданных исключений.
- Возвращаемся к `code review` и методу пристального взгляда :).

## Выводы

Интересно, что ранее сталикивался с подобным подходом как BDD, когда мы тестируем поведение функции, вместо каких-либо отдельных случаев.

Иногда затруднительно выделить своство так, чтобы его тестирование как-то отличалось от собственно тестируемого когда. Например, если мы тестируем, что функция корректно возвращает остаток от деления на число, то при попытке тестировать "как своство", метод тестирования сложно сделать как-то иначе, чем собственно саму реализацию расчета остатка от деления.

Некоторые (особенно когда тесты интеграционные) свойства очень тяжело выразить как-то точнее, чем "программа возвращает правильный результат", тогда приходится задумываться о том, насколько вообще корректно была поставлена задача, которую решает тот или иной кусок кода.

В целом, это полезный фреймворк для мышления при подходе к тестированию - даже в случае, если не удастся корректно выделить свойство и обернуть его в тест, мы в целом можем хотя бы описать его, и попробовать найти альтертативный подход (или хотя бы отметить такое свойство).
Это ощутимо отличается от обычного подхода, когда мы наугад выбираем несколько случаев (которые могут вообще не отражать реального поведения программы в работе) и полагаем, что функция "безопасна".
