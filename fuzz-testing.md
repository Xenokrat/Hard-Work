
# Отчет по fuzz тестированию на Python

1.  [Python Atheris](#org4674be6)
2.  [Инфо о проекте](#org44a51df)
3.  [Подготовка <code>[100%]</code>](#org25c6012)
4.  [Процесс <code>[100%]</code>](#org13841c7)
5.  [Проблемы при использовании](#orgf76b695)
6.  [Найденные баги](#org884f39c)



<a id="org4674be6"></a>

# Python Atheris

<https://github.com/google/atheris>
Библиотека использует libFuzzer под капотом, транслируя код в CPython
```python
import atheris

with atheris.instrument_imports():
    import some_library
    import sys

def TestOneInput(data):
    some_library.parse(data)

atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
```

<a id="org44a51df"></a>

## Инфо о проекте


<a id="org46b0d81"></a>
- Название : report_sender_queue

<a id="org70d9d81"></a>

- Описание : принимает из POST запроса параметры в переменной config, создает запрос в базу данных, возвращает отчет в .csv

<a id="orgf3f4bca"></a>

- Размер : ~ 2000 строк


<a id="org25c6012"></a>

### DONE Подготовка <code>[100%]</code>

-   [X] Устанавливаем clang
-   [X] устанавливаем Atheris <https://github.com/google/atheris>
-   [X] скачиваем репозиторий с составлением отчетов
-   [X] добавить .env файл

<a id="org13841c7"></a>

### DONE Процесс <code>[100%]</code>

-   [X] Изучить видео Fuzzing famose Python library
-   [X] Качаем примеры из atheris

```python
QueryBuilder.build_category_report_query(config)
```

```python
import sys
import random

with atheris.instrument_imports():
    from report_sender_queue.utils.query_builder import QueryBuilder

def get_fuzz_str(input_bytes):
    fdp = atheris.FuzzedDataProvider(input_bytes)
    return fdp.ConsumeString(10)


@atheris.instrument_func
def TestOneInput(input_bytes):
    start_date = get_fuzz_str(input_bytes)
    end_date = get_fuzz_str(input_bytes)
    platforms = [get_fuzz_str(input_bytes) for _ in range(random.randint(1, 5))]
    config = {
        "start_date": start_date,
        "end_date": end_date,
        "platforms": platforms,
    }
    QueryBuilder.build_category_report_query(config)


def main() -> None:
    atheris.Setup(sys.argv, TestOneInput)
    atheris.Fuzz()

if __name__ == "__main__":
    main()
```

Вывод по результатам тестирования (пример)
```bash
INFO: Running with entropic power schedule (0xFF, 100).
INFO: Seed: 1285549000
INFO: -max_len is not provided; libFuzzer will not generate inputs larger than 4096 bytes

    === Uncaught Python exception: ===
IndexError: list index out of range
Traceback (most recent call last):
    File "/home/pavel/code/learning/report_sender_queue/atheris/fuzz_query_builder.py", line 26, in TestOneInput
    QueryBuilder.build_category_report_query(config)
    File "/home/pavel/code/learning/report_sender_queue/report_sender_queue/utils/query_builder.py", line 13, in build_category_report_query
    if platforms[0] == 'Яндекс':
        ~~~~~~~~~^^^
IndexError: list index out of range

==4488== ERROR: libFuzzer: fuzz target exited
SUMMARY: libFuzzer: fuzz target exited
MS: 0 ; base unit: 0000000000000000000000000000000000000000


artifact_prefix='./'; Test unit written to ./crash-da39a3ee5e6b4b0d3255bfef95601890afd80709
Base64:
```

<a id="orgf76b695"></a>

## Проблемы при использовании


<a id="orgc48ece3"></a>

- [X] Это наверное очевидно, но не подходит для тестирования запросов в базу данных :)

<a id="orgc48ece3"></a>

- [X] Вообще довольно непросто использовать на любых функциях / методах, которые не принимают обычные типы данных, вроде строк или целых чисел.


<a id="org57e723e"></a>

- [X] Библиотека не видит модули в проекте (решено &#x2013; всегда использовать with atheris.instrument imports())


<a id="org66dd3ee"></a>

- [X] Выдает ошибку при использовании datetime, возможно не совместим с python3.11, решения пока не нашел


<a id="org884f39c"></a>

## Найденные баги


<a id="org99527b7"></a>

- Нет валидации что в config передается дата правильного формата


<a id="orge580a97"></a>

- Нет валидации что в config список площадок не пустой


<a id="orgbacc905"></a>

- Нет валидации что полученные данные для записи в .csv правильных форматов (не содержат например двойной кавычки)

