from gspread import service_account
import os
from dotenv import load_dotenv

load_dotenv()

class Table:
    def __init__(self, link):
        self.link = link
        self.client = self.client_init_json()
        self.table = self.get_table_by_url(self.client)

    @staticmethod
    def get_service_acc():
        serv_acc = os.getenv('SERVICE_ACCOUNT_FILE')
        if not serv_acc:
            raise FileNotFoundError('Файл с конфигурациями сервисного аккаунта не найден')
        return serv_acc

    def client_init_json(self):
        """Создание клиента для работы с Google Sheets."""
        sv = self.get_service_acc()
        return service_account(filename=sv)

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


    def get_players(self, config, data):
        """Сравнивает конфигурации игроков с искомой и возвращает игроков соответствующих указанным конфигурациям"""
        self.players = []
        for row in data:
            fl = True
            for k in config.keys():
                if row[k] == '' or int(row[k]) < int(config[k]):
                    fl = False
                    break
            if fl:
                self.players.append((row['Ник'], row['тэг тг']))
        return self.players

    def get_characters_list(self, data):
        """Возвращает список всех героев"""
        characters = list(data[0].keys())[2: -1]
        return characters

    def get_alternative_players(self, config, data):
        """При отсутствии игроков с искомыми пробудами и выше, возвращает список игроков,
        у которых искомые герои в наличии (пробуда 0 и выше)"""
        alt_players = []
        for row in data:
            fl = True
            for k in config.keys():
                if row[k] != '':
                    continue
                else:
                    fl = False
                    break
            if fl and (row['Ник'], row['тэг тг']) not in self.players:
                alt_players.append((row['Ник'], row['тэг тг']))
        return alt_players



# table_link = os.getenv('TABLE_LINK')
# table = Table(table_link)
# data = table.extract_data_from_sheet('феникс')
# config = {'Арача': 5, 'Выс': 5, 'Ган': 4}
# print(table.get_alternative_players(config, data))
