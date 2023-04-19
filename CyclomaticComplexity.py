# 1
# 1.1.1 Оригинальный метод
# 1.1.2 Начальная Цикломатическая сложность send_report_to_email - C (15)

def send_report_to_email(self, recipient_address):
        """
        Метод отправляет на почту recipient_address письмо с ссылками на отчеты
        """
        # количество попыток для отправки письма на один адрес
        attempt_count = 5

        # в текст письма добавляем ссылки на отчеты
        text = ""
        if self.writers_xlsx:
            if self.language == "ru":
                text = "<b>Отчеты в формате xlsx:</b><br><br>"
            else:
                text = "<b>Reports in xlsx format:</b><br><br>"
            for file_name in self.writers_xlsx:
                if self.writers_xlsx[file_name]["count"] > 1:
                    text += (
                        f'<a href="sample/reports/v2/{file_name}">'
                        f'{self.writers_xlsx[file_name]["platform"]} - {self.writers_xlsx[file_name]["count"]}</a><br>'
                    )
                else:
                    text += (
                        f'<a href="sample/reports/v2/{file_name}">'
                        f'{self.writers_xlsx[file_name]["platform"]}</a><br>'
                    )

        if self.writers_csv:
            if self.language == "ru":
                text += "<br><b>Отчеты в формате csv:</b><br><br>"
            else:
                text += "<br><b>Reports in csv format:</b><br><br>"
            for file_name in self.writers_csv:
                if (
                    "count" in self.writers_csv[file_name]
                    and self.writers_csv[file_name]["count"] > 1
                ):
                    text += (
                        f'<a href="sample/reports/v2/{file_name}">'
                        f'{self.writers_csv[file_name]["platform"]} - {self.writers_csv[file_name]["count"]}</a><br>'
                    )
                else:
                    text += (
                        f'<a href="sample/reports/v2/{file_name}">'
                        f'{self.writers_csv[file_name]["platform"]}</a><br>'
                    )

        message = MIMEText(text, "html")
        message["From"] = SENDER_ADDR
        message["To"] = recipient_address
        message["Date"] = formatdate(localtime=True)
        if self.email_subject:
            message["Subject"] = self.email_subject
        else:
            if self.language == "ru":
                message["Subject"] = (
                    f"Отчеты за {self.start_date.date()} - {self.end_date.date()} "
                    f"по сервисам экспресс доставки"
                )
            else:
                message["Subject"] = (
                    f"Reports for {self.start_date.date()} - {self.end_date.date()} "
                    f"for express delivery services"
                )

        # пытаемся отправить письмо
        email_is_send = False
        while attempt_count > 0 and email_is_send is False:
            try:
                smtp = smtplib.SMTP_SSL("smtp.yandex.ru", 465)
                smtp.login(SENDER_ADDR, SENDER_PASS)
                smtp.sendmail(SENDER_ADDR, recipient_address, message.as_string())
                smtp.quit()
                email_is_send = True
                log.info(f"Письмо отправлено на адрес {recipient_address}")
            except Exception as ex:
                log.error(ex)
                attempt_count -= 1


# 1.2.1 Исправленный метод

# 1.2.2
# Метод имеет слишком много ответственности
# Вводим отдельный метод для отправки сообщений на русском языке и отдельный на английском
# Выводим вспомогательные методы:
#   get_email_body_text (7) - создает ссылки с текстом на файлы
#   try_to_send_email (3) - пытается отправить письмо за определенное число попыток
# избавляемся от else, циклов, вложенных в условия, вложенных условий
# включаем также возвращение функциями bool типа
# избавляемся от if заменой на nullable or alternative

# 1.2.3 Конечная Цикломатическая сложность 
# ru_send_report_to_email (6)
# en_send_report_to_email (6)
# get_email_body_text (7)
# try_to_send_email (3)
    
def get_email_body_text(self, writer: dict) -> str:
    text = ''
    writer_with_count = {k: v for k, v in writer.items() if "count" in v}
    writer_no_count = {k: v for k, v in writer.items() if "count" not in v}

    for file_name in writer_no_count:
        text += f'<a href="sample/reports/v2/{file_name}">{writer[file_name]["platform"]}</a><br>'

    for file_name in writer_with_count:
        text += f'<a href="sample/reports/v2/{file_name}">{writer[file_name]["platform"]} - {writer[file_name]["count"]}</a><br>'

    return text


def ru_send_report_to_email(self, recipient_address) -> bool:
    """
    Метод отправляет на почту recipient_address письмо с ссылками на отчеты
    """
    # количество попыток для отправки письма на один адрес
    if not (self.xlsx_writers or self.csv_writers):
        return False

    if self.xlsx_writers:
        text = "<b>Отчеты в формате xlsx:</b><br><br>"
        text += self.get_email_body_text(self.xslx_writers)
    
    if self.csv_writers:
        text += "<b>Отчеты в формате csv:</b><br><br>"
        text += self.get_email_body_text(self.csv_writers)

    message = MIMEText(text, "html")
    message["From"] = SENDER_ADDR
    message["To"] = recipient_address
    message["Date"] = formatdate(localtime=True)
    message["Subject"] = self.email_subject or f"Отчеты для {self.start_date.date()} - {self.end_date.date()} " 
    # пытаемся отправить письмо
    return self.try_to_send_email(message)

def en_send_report_to_email(self, recipient_address) -> bool:
    """
    Метод отправляет на почту recipient_address письмо с ссылками на отчеты
    """
    # количество попыток для отправки письма на один адрес
    if not (self.xlsx_writers or self.csv_writers):
        return False

    if self.xlsx_writers:
        text = "<b>Reports in xlsx format:</b><br><br>"
        text += self.get_email_body_text(self.xslx_writers)
    
    if self.csv_writers:
        text += "<b>Reports in csv format:</b><br><br>"
        text += self.get_email_body_text(self.csv_writers)

    message = MIMEText(text, "html")
    message["From"] = SENDER_ADDR
    message["To"] = recipient_address
    message["Date"] = formatdate(localtime=True)
    message["Subject"] = self.email_subject or f"Reports for {self.start_date.date()} - {self.end_date.date()} " 
    # пытаемся отправить письмо
    return self.try_to_send_email(message)


def try_to_send_email(self, message, attempts=5):
    if attempts <= 0:
        return False
    try:
        smtp = smtplib.SMTP_SSL("smtp.yandex.ru", 465)
        smtp.login(SENDER_ADDR, SENDER_PASS)
        smtp.sendmail(SENDER_ADDR, message["To"], message.as_string())
        smtp.quit()
        return True
    except Exception as ex:
        log.error(ex)
        return try_to_send_email(self, message, attempts - 1)


# 2
# 2.1.1 Оригинальный метод
# 2.1.2 Начальная Цикломатическая сложность filter_conditions - C (16)

def filter_conditions(self):
    platforms = []
    if self.config['platforms']:
        platforms = [platform for platform in list(self.updates_df['darkstore_group_platform'].unique())
                        if platform in self.config['platforms']]

    # фильтруем доставки в площадках
    deliveries = defaultdict(lambda: defaultdict(list))
    if 'platform_deliveries' in self.config and self.config['platform_deliveries']:
        for delivery, platform in self.updates_df[['darkstore_group_delivery',
                                                    'darkstore_group_platform']].value_counts().index.values:
            if platform in self.config['platform_deliveries'].keys():
                for query_delivery_name in self.config['platform_deliveries'][platform]:
                    if query_delivery_name.lower().strip() in delivery.lower().strip():
                        deliveries[platform][query_delivery_name].append(delivery)

        # Если есть разбивка по доставкам, делаем отчеты отдельно для каждой доставки
        if deliveries:
            for platform in deliveries.keys():
                if platform in platforms:
                    platforms.remove(platform)
                for query_delivery_name in deliveries[platform].keys():
                    delivery_names = deliveries[platform][query_delivery_name]
                    
                    self.prepare_reports(
                        platform=f'{platform} {query_delivery_name}',
                        platform_df=self.updates_df[(self.updates_df['darkstore_group_platform'] == platform) &
                                                    (self.updates_df['darkstore_group_delivery'].isin(
                                                        delivery_names))])

    # иначе отчеты отдельно по площадкам, без разбивки по доставкам
    if platforms:
        for platform in platforms:
            self.prepare_reports(
                platform=f'{platform}',
                platform_df=self.updates_df.query('darkstore_group_platform == @platform'))


# 2.2.1 Начальная Цикломатическая сложность filter_conditions - (16)

# 2.2.2
# избавляемся от if в условиях типа когда something может быть либо пустым листом, либо содержать информацию:
# if something:
#     for i in something:
#         do things
# ->
#  for i in something:
#         do things

# избавляемся от вложенных if с помощью списковых включений и фильтрации

# Пробуем использовать полиморфизм подтипов
# Задаем абстрактный класс с реализацией подготовки отчетов
# Для 2 типов отчетов переопределяем метод для фильтрации (фильтрация только по площадкам, и фильтрация по площадкам + доставкам)

# 2.2.3
# Конечная сложность введенных Классов и методов
#  ReportPlatformDelivery - A (5)
#  ReportPlatformDelivery.filter_conditions - A (4)
#  ReportPlatform - A (4)
#  ReportPlatform.filter_conditions - A (3)
#  Report - A (2)
#  Report.__init__ - A (1)
#  Report.prepare_reports - A (1)
#  Report.filter_conditions - A (1)

class Report(ABC):
    def __init__(self, config, updates_df: pd.DataFrame): 
        self.config = config
        self.updates_df = updates_df

    def prepare_reports(self, platform, platform_df):
        # Метод общий для отчетов, опускаю реализацию
        pass
        
    @abstractmethod 
    def filter_conditions(self):
        pass

class ReportPlatformDelivery(Report):
    def filter_conditions(self):
        platforms = [
            platform for platform in list(self.df_categories['darkstore_group_platform'].unique())
            if platform in self.platforms
        ]
        deliveies_before_filter = [platform[query_delivery_name] for platform in updates_df['darkstore_group_delivery']]
        deliveies = deliveies_before_filter.filter(lambda delivery: delivery in self.config['platform_deliveries'].values())

        self.prepare_reports(
            platform=f'{platform} {deliveies}',
            platform_df=self.updates_df[
                (self.updates_df['darkstore_group_platform'] == platform) &
                (self.updates_df['darkstore_group_delivery'].isin(deliveies))
            ]
        )
    
class ReportPlatform(Report):
    def filter_conditions(self):
        self.platforms = [
            platform for platform in list(self.df_categories['darkstore_group_platform'].unique())
            if platform in self.platforms
        ]

        self.prepare_reports(
            platform=f'{platform} {query_delivery_name}',
            platform_df=self.updates_df[
                (self.updates_df['darkstore_group_platform'] == platform)
            ]
        )

# 3
# 3.1.1 Оригинальный метод
# 3.1.2 Начальная Цикломатическая сложность filter_conditions - B (8)

@api_view(["GET", "PUT", "DELETE"])
def vehicle_detail(request, pk: int):
    if not (hasattr(request.user, "manager") or request.user.is_superuser):
        return Response({"message": "Forbidden"}, status=403)

    try:
        vehicle = Vehicle.objects.get(pk=pk)
    except Vehicle.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == "GET":
        serializer = VehicleSerializer(vehicle)
        return Response(serializer.data)

    elif request.method == "PUT":
        serializer = VehicleSerializer(vehicle, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == "DELETE":
        vehicle.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# 3
# 3.2.1 Оригинальный метод
# 3.2.2 Начальная Цикломатическая сложность filter_conditions - B (8)
# избавляемся от проверки на доступ менеджера при помощи декоратора 
# заменяем получения объекта автомобиля встроенным методом get_object_or_404 вместо try / except
# избавляемся от elif, так как после каждой проверки следует выход из функции return
# так как все доступные методы проверяются в дектораторе api_view, метод PUT можно вынести из под if

# 3.2.3 Конечная Цикломатическая сложность better_filter_conditions - B (4) 

@permission_classes([IsAuthenticated, IsManager])
@api_view(["GET", "PUT", "DELETE"])
def better_vehicle_detail(request, pk: int):

    vehicle = get_object_or_404(Vehicle, pk=pk)

    if request.method == "GET":
        serializer = VehicleSerializer(vehicle)
        return Response(serializer.data)

    if request.method == "DELETE":
        vehicle.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    # PUT
    serializer = VehicleSerializer(vehicle, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)