# Hard Work - Как проектировать программы in small

## Пример 1

Функция для возвращения множества сочетаний элементов из 2 списоков.
Ниже простейшее императивное решение с вложенными циклами:

```python
def cross_join_client_base_data(self) -> set[tuple[str, str]]:
    client_data = self.client_products_list["data"]
    base_data = self.base_products_list["data"]
    res = set()
    for cd in client_data:
        for bd in base_data:
            res.add((cd, bd))
    return res
```

Пробуем рассуждать с точки зрения выходных данных и ко-рекурсии.

```python
def cross_join_client_base_data(self) -> set[tuple[str, str]]:
    client_data = self.client_products_list["data"]
    base_data = self.base_products_list["data"]
    return self._cross_join_client_base_data(client_data, base_data)
    
def _cross_join_client_base_data(
    self,
    client_data: list[str],
    base_data: list[str],
) -> set[tuple[str, str]]:
    """Рекурсивная функция для реализации cross_join_client_base_data"""

    # Когда выходной сет будет пустым? 
    # Если набор клиентских значений и/или базовых значений пустой
    if not all([client_data, base_data]):
        return set()

    # В других случаях, когда выход не пуст, что нужно добавить к нему?
    # Сочетания значения из одного списка со всеми из другого
    # Как рекурсивно будет достраиваться сет?
    # вызовом этой же функции уже без добавленного элемента c_val
    c_val = client_data.pop()
    return (
        _cross_join_client_base_data(client_data, base_data) |
        {(c_val, b_val) for b_val in base_data}
    )
```

## Пример 2

Пример из алгоритмических задач (Древо Жизни - двумерная матрица, в которой симулируется рост и отмирание веток дерева).
Попробуем переосмыслить функцию, которая симулирует поведение в нечентый год, когда из двумерного массива нужно удалить все старые (возраст >2) значения возраста веток.

```python
def odd_year(parsed_tree: list[list[int]], h: int, w: int) -> list[list[int]]:
    # branches become older
    new_parsed_tree = even_year(parsed_tree, h, w)

    branches_to_del = set()
    for row in range(h):
        for col in range(w):
            if new_parsed_tree[row][col] > 2:
                branches_to_del.add((row, col))

    branches_to_del_copy = branches_to_del.copy()
    for branch in branches_to_del_copy:
        # add upper
        if branch[0] > 0:
            branches_to_del.add((branch[0] - 1, branch[1]))
        # add bottom
        if branch[0] < h - 1:
            branches_to_del.add((branch[0] + 1, branch[1]))
        # add left
        if branch[1] > 0:
            branches_to_del.add((branch[0], branch[1] - 1))
        # add right
        if branch[1] < w - 1:
            branches_to_del.add((branch[0], branch[1] + 1))
    for branch in branches_to_del:
        row = branch[0]
        col = branch[1]
        new_parsed_tree[row][col] = 0

    return new_parsed_tree
```

Измененный вариант функции

```python
def odd_year(parsed_tree: list[list[int]], h: int, w: int) -> list[list[int]]:
    # Эту часть не будем трогать, т.к. тут происходит увеличение возраста всех веток,
    # реализованное в функции even_year
    new_parsed_tree = even_year(parsed_tree, h, w)
    return _odd_year(new_parsed_tree, h, w)

def _odd_year(tree: list[list[int]], h: int, w: int) -> list[list[int]]:
    # Базовый случай? 
    # Когда в массве нет цифр больше 2
    if all(max(i) < 3 for i in tree):
        return tree

    # В других случаях, когда есть элементы больше 2,
    # что нужно сделать?
    # найти первое значение больше 2, удалить его и соседние согласно правилу задачи
    next_cell = find_next_cell_to_delete(tree) 
    # далее рекурсивно вызываем _odd_year пока ячейки для удаления не закончатся
    return (
        _odd_year(delete_dying_cells(tree, next_cell, h, w)
    ))

# вспомогательные функции
def find_next_cell_to_delete(tree) -> tuple[int, int] | None:
    for row in tree:
        for col in row:
            if tree[row][col] > 2:
                return (row, col)
    return None

def delete_dying_cells(tree: list[list[int]], cell: tuple[int, int], h: int, w: int):
    to_del = set(filter(
        lambda x: all([0 <= x[0] < w, 0 <= x[1] < h]),
        [cell,
         (cell[0] + 1, cell[1]),
         (cell[0] - 1, cell[1]),
         (cell[0], cell[1] + 1),
         (cell[0], cell[1] - 1)]
    ))
    return [
        [tree[row][col] for col in range(h)
        if (row, col) not in to_del
        else 0
        ] for row in range(w)
    ]
```

## Пример 3

Функция, которая парсит из строкового значения комманду, и возвращает действительное значение комманды плюс список аргументов для ее выполнения (пример из реализации ram-машины).

```python
def parse_command(self) -> tuple[str, str | None | tuple[str, ...]]:
    command_str = self.command_str_list[self.current_command]
    parsed = command_str.split(" ", 1)
    command = parsed[0].strip().lower()
    args = parsed[1].strip() if len(parsed) > 1 else None
    args = tuple(args.split(","))
    # Mark
    if command[-1] == ":":
        return "mark", None
    if not hasattr(self.command_cls, command):
        raise NonValidProgram(f"\"{command}\" not implemented")
    return command, args
```

Попробуем сосредоточиться на выходных данных:
выходными данными будет кортеж, состоящий из первого элемента - строки названия комманды
и второго элемента, который является вложенным кортежем из n-го количества агрументов (пока в строке).

```python
def get_command_name(command_str: str) -> str:
    ...

def get_command_args(command_str: str) -> tuple[str, ...] | None:
    ...

def parse_command(self) -> tuple[str, str | None | tuple[str, ...]]:
    command_str = self.command_str_list[self.current_command]
    return get_command_name(comand_str), get_command_args(command_str)

```

Тогда, во первых, нужно получить комманду:

```python
def get_command(command_str: str) -> str:
    # Очень простая функция, дополнительных пояснений не требуется
    parsed = command_str.split(" ", 1)
    return parsed[0].strip().lower()

def get_command_args(command_str: str) -> tuple[str, ...] | None:

def _get_command_args(args_str: str, args: tuple[str, ...]) -> tuple[str, ...] | None:
    # Когда нужно возвращать все аргументы?
    # Если args_str - пустая строка, возвращаем агрументы
    if not args_str:
        return args

    # Когда args_str не пустая, что нужно сделать?
    # найти следующий аргумент
    arg, new_arg_str = args_str.split(",", 1)
    args += arg
    # рекурсивно вызываем дальше
    return _get_command_args(new_arg_str, args)
    
# Объединяем вместе
def parse_command(self) -> tuple[str, str | None | tuple[str, ...]]:
    command_str = self.command_str_list[self.current_command]
    return get_command_name(comand_str), get_command_args(command_str)
```

## Выводы

Впервые из этого занятия узнал о подходе  "How to Design Programs", буду также пользоваться.
Кажется полезным упражнением, подходить к любым проблемам с точки зрения рекурсии (и вообще, функционального стиля).
Альтернативный подход, рассмотренный в занятии, также в некоторых ситуациях кажется позволяет облегчить написание функции. Рассматривая задачу "с конца", получается как бы "вытягивающий" процесс, когда именно результат тянет за собой собственный способ реализации. Но такой подход в целом новый для меня, буду в целом пытаться по возможности писать как можно чаще именно с такой позиции (исходя из входных структур данных, или выходных).
На примере данного задания, на личном опыте убедился, насколько бывает непросто заставлять себя писать в функциональном стиле (в частности рекурсивные программы). Несмотря на множество пройденных упражнений по функциональщине, применение такого стиля в реальных программах требует дополнительных усилий, хотя в некоторых случаях получаются гораздо более компактные и изящные решения.

P.S.

То, как сложно мне было найти материал для этого урока из рабочего, говорит, наверное о качестве выполняемых мной заданий:
в 95% случаев в коде происходят не преобразования данных даже, а вызов методов из уже готовых инструментов (выгрузить из БД, сохранить в БД (логику с данными проще оставлять на стороне БД, сделать POST-запрос и т.д.)).
