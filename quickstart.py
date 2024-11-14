import gspread
from google.oauth2.service_account import Credentials
import os

# Задаем путь к JSON файлу с ключами сервисного аккаунта
serv_acc = os.getenv('SERVICE_ACCOUNT_FILE')

if not serv_acc:
    raise FileNotFoundError('Файл с конфигурациями сервисного аккаунта не найден')

# Определяем область доступа (scope) для Google Sheets API
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly", "https://www.googleapis.com/auth/drive"]

# Создаем объект учетных данных

creds = Credentials.from_service_account_file(serv_acc, scopes=SCOPES)

# Подключаемся к Google Sheets через gspread
client = gspread.authorize(creds)


# Открываем таблицу и выберите лист
sheet = client.open("пул феникс").worksheet('феникс')

# Получаем данные из таблицы
data = sheet.get_all_records()
print(data)



