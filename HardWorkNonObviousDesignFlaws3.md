## Пример 1
### Изменения
#### Было
Задача с GUI для машины Тьюринга
1. Имели файл, который частично формировался при помощи программы `Qt Designer`.
2. В первоначальном варианте логика работы кнопок, логика обновления машины и собственно сам дизайн были в пределах одного модуля.
```python
class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(400, 300)
        self.verticalLayout = QtWidgets.QVBoxLayout(Form)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.alph_label = QtWidgets.QLabel(parent=Form)
        font = QtGui.QFont()
        
    ...
        
	def step_left(self):
        self.machine.current_tape_cell -= 1
        self.update_tape_graphics()

    def step_right(self):
        self.machine.current_tape_cell += 1
        self.update_tape_graphics()

    def set_empty_value(self):
        self.machine.tape[self.machine.current_tape_cell] = ""
        self.update_tape_graphics()

    def set_cell_value(self):
        new_value = self.ui.cell_value_box.value()
        self.machine.tape[self.machine.current_tape_cell] = new_value
        self.update_tape_graphics()

	...

```

#### Стало
Как как файл с GUI формируется программой автоматически, существует риск при внесении изменений полностью перезаписать файл со всеми методами.
Практически лучше переделать дизайн, разделив логику отрисовки GUI, действия Машины Тьюринга, и связать  всю логику через основной модуль.
Это позволяет (при условии что названия элементов не изменяются) легко 
- изменять дизайн UI, 
- изменять логику действия машины
не затрагивая при этом остальную часть программы.
```python
# ----------Модуль Machine-------------#
@dataclass
class TuringMachineApp:
    state_value: int
    alph_value: int
    is_ready_to_start: bool = True
    is_on: bool = False
    current_table_state: int = 1
    ...

# ----------Модуль GUI-------------#
class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(400, 300)
        self.verticalLayout = QtWidgets.QVBoxLayout(Form)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.alph_label = QtWidgets.QLabel(parent=Form)
        font = QtGui.QFont()
        ...

# ----------Модуль Основной-------------#
class TuringMachineGUI(QMainWindow):
    def __init__(self, machine: TuringMachineApp) -> None:
        super().__init__()
        self.setWindowTitle("Turing Machine Array")
        self.setGeometry(100, 100, 800, 600)
        self.cell_size = 100

		# Здесь 
        self.machine = machine
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        ...
```

### Границы и способ их задания

- Внутренние границы изменяются значительно, так как один модуль превращается в 3.
- Для внешнего пользователя GUI изменение будет не заметно.


### Выводы
Внесенные изменения позволяют разделить логику работы программы от ее внешнего вида и механизмов, которые репрезентует данная программа.
Такое разделение позволяет работать с разными элементами GUI, не затрагивая остальные и легко вносить локальные изменения.

## Пример 2
### Изменения
#### Было
Проект с системой уведомлений событий в БД работал следующим образом:
1. В БД постоянно отправлялись запросы для оценки наличия/правильности всех данных.
2. Если проблема обнаруживалась, отправлялось сообщение с ошибкой.
3. Чтобы сообщения не спамились постоянно, одинаковые уведомления "ставили себя на паузу (`self.alert_delay`) на какое-то время.
4. Время паузы постепенно увеличивалось `ALERT_TIME_INCREASE_MULTIPLIER` и сообщения об одной и той же ошибке отправлялись все реже.
Ниже пример одной из части программы
```python
class AlertSystem:
    def __init__(self, monitorings: List[Monitoring]) -> None:
        self.monitorings = monitorings
        self.initial_alert_delay = ALERT_TIME_INITIAL_DELAY
        ...

	def set_delays(self) -> None:
        for m in self.monitorings:
            if not m.alert_delay:
	            m.alert_delay = ALERT_TIME_INITIAL_DELAY
            
    def run_monitorings(self) -> None:
        for m in self.monitorings:
            m.run()


class CountryMonitoring(Monitoring):
    query = query
    PLATFORMS_COUNTRIES = PLATFORMS_COUNTRIES

    def __init__(self, db_client: DB, message_client: Client) -> None:
        super().__init__(db_client, message_client)
        self.alert_delay = COUNTRY_ALERT_TIME_INITIAL_DELAY
        ...

    def eval_data(self, data) -> str:
        if not data:
            log.debug("no data")
            return ""

        current_time = datetime.utcnow()
        monitoring_date = (datetime.utcnow() - timedelta(days=1)).strftime("%d-%m")
        alert_text = f"*ALERT*: The database time is: _{current_time.strftime('%d.%m %H:%M')}_\nOne or more countries are missing from database in _{monitoring_date}_:\n"
        text_is_changed = False
        
        is_alert_not_delayed = current_time >= self.time_to_check

        currect_platform_coutries = defaultdict(set)
        for app, country in data:
            currect_platform_coutries[app].add(country)
        
        for app in currect_platform_coutries:
            if app not in self.PLATFORMS_COUNTRIES:
                log.warning(f"App {app} not in default platform list")
                continue

            default_country_set = self.PLATFORMS_COUNTRIES[app] 
            current_country_set = currect_platform_coutries[app]
            is_country_missig =  default_country_set != current_country_set

            if is_country_missig and is_alert_not_delayed:
                missing_countries = default_country_set - current_country_set
                alert_text += f"\n*{app}*:\n"
                alert_text += "\n".join(missing_countries)
                alert_text += "\n----------------------------"
                text_is_changed = True
        
        if text_is_changed:
            self.time_to_check = self.time_to_check + timedelta(seconds=self.alert_delay)
            log.debug(f"Next time to delay is {self.time_to_check}")
            self.alert_delay *= ALERT_TIME_INCREASE_MULTIPLIER
            return alert_text
```

#### Стало
В целом такой подход оказался переусложненным и никому особо не понравился).
Постоянный поток сообщений об ошибках в какой-то момент стал просто привычным, а увеличение времени отправки следующего сообщения ошибках не мотивировал предпринимать какие-либо действия.
Поэтому было решено упростить программу.
1. 2-4 Раза в день в определенное время программа делала запросы в БД, собирая всю необходимую информацию.
2. Информация отправляется в рабочий час в виде одного большого отчета.
3. Хотя мы теряем возможность быстрого реагирования на возникшую проблему, практика показала, что пара часов не играли значительной роли.
```python
# 
# ----main.py-----
# Управление расписанием теперь из main файла
schedule.every(QUERY_UPDATE_PERIOD_SECONDS).hours.do(
        alert_system.run_monitorings)

# ----alertsystem.py-----
# Убираем задержку в основном классе системы уведомлений
class AlertSystem:
    def __init__(self, monitorings: List[Monitoring]) -> None:
        self.monitorings = monitorings

    def run_monitorings(self) -> None:
        for m in self.monitorings:
            m.run()

# -----Пример одного из мониторингов
# Убираем всю логику с внесением задержки
class CountryMonitoring(Monitoring):
    query = query
    PLATFORMS_COUNTRIES = PLATFORMS_COUNTRIES

    def __init__(self, db_client: DB, message_client: Client) -> None:
        super().__init__(db_client, message_client)
        ...

    def eval_data(self, data) -> str:
        if not data:
            log.debug("no data")
            return ""

        current_time = datetime.utcnow()
        monitoring_date = (datetime.utcnow() - timedelta(days=1)).strftime("%d-%m")
        alert_text = f"*ALERT*: The database time is: _{current_time.strftime('%d.%m %H:%M')}_\nOne or more countries are missing from database in _{monitoring_date}_:\n"
        text_is_changed = False

        currect_platform_coutries = defaultdict(set)
        for app, country in data:
            currect_platform_coutries[app].add(country)
        
        for app in currect_platform_coutries:
            if app not in self.PLATFORMS_COUNTRIES:
                log.warning(f"App {app} not in default platform list")
                continue

            default_country_set = self.PLATFORMS_COUNTRIES[app] 
            current_country_set = currect_platform_coutries[app]
            is_country_missig =  default_country_set != current_country_set

            if is_country_missig:
                missing_countries = default_country_set - current_country_set
                alert_text += f"\n*{app}*:\n"
                alert_text += "\n".join(missing_countries)
                alert_text += "\n----------------------------"
                text_is_changed = True
        
        if text_is_changed:
            self.time_to_check = self.time_to_check + timedelta(seconds=self.alert_delay)
            return alert_text
```

### Границы и способ их задания
Модуль main теперь берет на себя ответственность за время расписания мониторингов (ранее это решалось в классе мониторинга). Интерфейс 
Удалены все константы и части, где рассчитывалось, нужно ли предоставлять информацию сейчас, или отложить ее.

### Выводы
В целом логика программы сместилась в сторону упрощения, лишние части программы были удалены, логика поведения уведомлений стала прозрачной и понятной для других коллег.

## Общие Выводы
В отдельных случаях внесение значительных нелокальных изменений сопровождается увеличением количества кода (как в первом примере), в других случаях имеет место даже удаление лишнего кода. 
Однако неизменно то, что такие, на первый взгляд, рискованные изменения, затрагивающие многие части программы, могут дать существенный выигрыш в упрощении работы программы, улучшают ее сопровождаемость, делают проще рассуждения о ее работе.
В целом, при осторожном и осмысленном подходе, не стоит бояться вносить нелокальные изменения в программу, так как переработка дает значительные преимущества и окупает затраченные усилия.