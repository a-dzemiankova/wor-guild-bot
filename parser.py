from gspread import service_account
import os
from dotenv import load_dotenv


load_dotenv()
serv_acc = os.getenv('SERVICE_ACCOUNT_FILE')

if not serv_acc:
    raise FileNotFoundError('Файл с конфигурациями сервисного аккаунта не найден')

table_link = 'https://docs.google.com/spreadsheets/d/1vjeqBcC2iK4BDRvwElzu_K0ECLwIgdxsj_XgRoZAR6Q/edit?gid=0#gid=0'


class Table:
    def __init__(self, link):
        self.link = link
        self.client = self.client_init_json()
        self.table = self.get_table_by_url(self.client)

    @staticmethod
    def client_init_json():
        """Создание клиента для работы с Google Sheets."""
        return service_account(filename=serv_acc)

    def get_table_by_url(self, client):
        """Получение таблицы из Google Sheets по ссылке."""
        return client.open_by_url(self.link)

    def get_worksheets(self):
        """Получение списка листов таблицы"""
        return self.table.worksheets()

    def extract_data_from_sheet(self, sheet_name):
        """
        Извлекает данные из указанного листа таблицы Google Sheets и возвращает список словарей.
        """
        worksheet = self.table.worksheet(sheet_name)
        data = worksheet.get_all_records()
        return data

    @staticmethod
    def get_user_config(config, user_data):
        """Возвращает данные по пробудам искомых героев у конкретного игрока"""
        keys = list(config.keys())
        user_config = dict()
        for k in keys:
            user_config[k] = user_data[k]
        return user_config

    @staticmethod
    def get_players(config, data):
        """Сравнивает конфигурации игроков с искомой и возвращает игроков соответствующих указанным конфигурациям"""
        players = []
        for row in data:
            fl = True
            for k in config.keys():
                if row[k] == '' or row[k] < config[k]:
                    fl = False
                    break
            if fl:
                players.append((row['Ник'], row['тэг тг']))
        return players


table = Table(table_link)
data = table.extract_data_from_sheet('феникс')
config = {'Аякс': 0, 'Саргак': 0, 'Претус': 3, 'Брокир': 1}
players = table.get_players(config, data)
print(players)