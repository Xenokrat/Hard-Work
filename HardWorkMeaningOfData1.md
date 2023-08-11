# Пример денормализации данных

## Денормализация связи между структурой данных в таблицах продуктов и их категорий

Пример из мира SQL.
В БД PostgreSQL Имелась большая таблица по ежедневному обновлению продажи продуктов в магазинах, вида вроде.

```SQL
SELECT
 update_time,
 store_id,
 product_id,
 price,
 discount,
 ...
FROM product_update
```

В целом такие данные хранятся в нормализованном виде вместе со справочником по продуктам, где указаны различные характеристики продуктов.
Существует также еще третья таблица, где отслеживается изменение категорий, в которых продукты находятся в магазине.

```SQL
SELECT
 update_time,
 store_id,
 category_id,
 product_id
FROM category_product_update
```

(У таблицы обновлений категорий соответственно имеется свой справочник).

Со временем мы пришли к использованию другой БД - `Clickhouse` для совместного использования с системами для BI - аналитики, поскольку `Clickhouse` значительно быстрее делает `SELECT` запросы, особенно с использованием `GROUP BY`.
Однако проблема была в том, что операции с `JOIN` проблематичны для Кликхауса, и он выполняет их относительно медленно, и с использованием большого объема RAM (иногда больше, чем имеется у сервера).

Поэтому для быстрого использования с BI-системой, создали отдельную денормализованную таблицу (которая обновляется раз в сутки) специально для `Clickhouse`.
Такая таблица в итоге содержит информацию по продажам продукта в магазине в указанное время, и массив из всех категорий продукта в это же время.

```update_time -- store_id -- product_id -- category_name[]```

Также в нее включили значительную часть справочной информации (название продуктов, бред, адрес магазина и т.д.)

### Выводы по примеру 1

#### Плюсы

- Плюс такого подхода в том, что запросы на выборку из такой таблицы очень быстрые, в том числе и с использованием `GROUP BY`, и на аналитический экран можно вывести статистику по продукту с названиями в обход `JOIN` операции очень быстро.
- `Clickhouse` также позволяет использовать функции для поиска по массивам, которые также довольно быстрые. Благодаря хранению категорий продуктов в массиве, не приходится делать огромный `JOIN` всех категорий каждого продукта к нему.

#### Минусы

- Дополнительное место для хранения денормализованных данных (`Clickhouse` в целом очень хорошо жмет данные внутри колонок, особенно если при создании таблицы правильно выбран `ORDER BY`).
- Дополнительные затраты на создание и поддержание таких агрегаций.

## Денормализация связи между объектом Программы и объектом, реализующим Команды в симуляции RAM-машины

Дополнительные проект по симуляции RAM-машины:
У меня имеется 2 отдельных класса:

- Класс `Program` - находится на более высоком уровне абстракции, содержит в себе список команд (необработанных, в виде строковых значений), регистр, входную / выходную ленту и т.д. Его задача - брать значения из списка команд и определять и реализовывать инструкцию.
- Класс `Commands` - как раз нужен для реализации логики выполнения команд.

```python
class Program:

    def __init__(
        self,
        command_cls: Commands,
        reg: Register,
        input_tape: InputTape,
        output_tape: OutputTape,
        command_str_list: list[str],
        current_command: int = 0,
    ) -> None:
        self.command_cls = command_cls
        self.reg = reg
        self.input_tape = input_tape
        self.output_tape = output_tape
        self.command_str_list = command_str_list
        self.current_command = current_command
        self.running: bool = False

 def parse_command(self) -> None:
        command_str = self.command_str_list[self.current_command]
        parsed = command_str.split(" ", 1)
        if len(parsed) == 1 and parsed[0].isdigit():
            pass
        # Case of mark
        elif len(parsed) == 1 and parsed[0] in allowed_commands_no_args:
            match parsed[0]:
                case "READ":
                    self.do_read()
            # MORE CODE
 ...
 def do_load(self, args: str) -> None:
        try:
            str_value, str_address = args.split(",")
        except ValueError:
            raise NonValidCommand(f"\"{args}\" are invalid arguments for LOAD")
        value = self.parse_const_arg(str_value)
        address = self.parse_address_arg(str_address)
        self.command_cls.load(self.reg, value, address)
```

Хотя по идее это будет нарушением принципа `SRP`, возможно класс `Program` мог бы реализовывать логику команд самостоятельно, так как он обладает всеми необходимыми знаниями для этого.
Другим плюсом будет то, что для добавления новых команд будет достаточно модифицировать только один класс.
Пример метода без использования класса-комманд:

```python
class Program:

    def __init__(
        self,
        command_cls: Commands,
        reg: Register,
        input_tape: InputTape,
        output_tape: OutputTape,
        command_str_list: list[str],
        current_command: int = 0,
    ) -> None:
        self.reg = reg
        self.input_tape = input_tape
        self.output_tape = output_tape
        self.command_str_list = command_str_list
        self.current_command = current_command
        self.running: bool = False

  def load(self, reg: Register, value: numeric, address: int) -> None:
        try:
            str_value, str_address = args.split(",")
        except ValueError:
            raise NonValidCommand(f"\"{args}\" are invalid arguments for LOAD")
        value = self.parse_const_arg(str_value)
        address = self.parse_address_arg(str_address)
        self.command_cls.load(self.reg, value, address)
        self.reg[address] = value
  ...
```

### Выводы по примеру 2

Потенциально, такое изменение может упростить модель данных, поскольку мы можем обрабатывать логику обработки программы и парсинга и выполнения конкретных команд в пределах этой программы.
Негативным фактором может стать то, что класс `Program` получается очень перегруженным. Возможно решением будет выделить из данного класса другие сущности (например парсинг строк в команды).

## Общие выводы

Денормализация отношений между структурами данных в некоторых ситуациях позволяет получить значительное преимущество.

Главное помнить, что это почти всегда trade-off: более удобная модель данных получается за счет потери гибкости, или дополнительных издержек на поддержание более плотно связанной структуры.

Нужно всегда стремиться оценить получаемые плюсы и минусы, а также контекст при принятии решения о том, чтобы денормализовать отношения между объектами.
