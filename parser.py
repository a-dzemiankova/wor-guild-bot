from gspread import service_account, client, spreadsheet
import os
from dotenv import load_dotenv
from settings import TableSettings as ts

load_dotenv()


class Table:
    def __init__(self, link: str):
        self.link = link
        self.client = self.client_init_json()
        self.table = self.get_table_by_url(self.client)

    def client_init_json(self) -> client.Client:
        """Создание клиента для работы с Google Sheets."""
        return service_account(filename=self.get_service_acc())

    def get_table_by_url(self, client: client.Client) -> spreadsheet.Spreadsheet:
        """Получение таблицы из Google Sheets по ссылке."""
        return client.open_by_url(self.link)

    def get_worksheets(self) -> list:
        """Получение списка листов таблицы"""
        worksheets_raw = self.table.worksheets()
        worksheets = [str(ws).split()[1].strip("'") for ws in worksheets_raw]
        return worksheets

    def extract_data_from_sheet(self, sheet_name: str) -> list[dict]:
        """
        Извлекает данные из указанного листа таблицы Google Sheets и возвращает список словарей.
        """
        worksheet = self.table.worksheet(sheet_name)
        table_data = worksheet.get_all_records()
        return table_data

    def get_players(self, config: dict, table_data: list[dict]) -> list[tuple]:
        """Сравнивает конфигурации игроков с искомой и возвращает игроков соответствующих указанным конфигурациям"""
        self.players = []
        for row in table_data:
            fl = True
            for k in config.keys():
                if row[k] == '' or int(row[k]) < int(config[k]):
                    fl = False
                    break
            if fl:
                self.players.append((row[ts.NICK], row[ts.TAG]))
        return self.players

    def get_alternative_players(self, config: dict, table_data: list[dict]) -> list[tuple]:
        """При отсутствии игроков с искомыми пробудами и выше, возвращает список игроков,
        у которых искомые герои в наличии (пробуда 0 и выше)"""
        alt_players = []
        for row in table_data:
            fl = True
            for k in config.keys():
                if row[k] != '':
                    continue
                else:
                    fl = False
                    break
            if fl and (row[ts.NICK], row[ts.TAG]) not in self.players:
                alt_players.append((row[ts.NICK], row[ts.TAG]))
        return alt_players

    @staticmethod
    def get_service_acc() -> str:
        """Получение сервисного аккаунта для работы с Google Spreadsheet"""
        serv_acc = os.getenv('SERVICE_ACCOUNT_FILE')
        if not serv_acc:
            raise FileNotFoundError('Файл с конфигурациями сервисного аккаунта не найден')
        return serv_acc

    @staticmethod
    def get_user_config(config: dict, user_data: dict) -> dict:
        """Возвращает данные по пробудам искомых героев у конкретного игрока"""
        keys = list(config.keys())
        user_config = dict()
        for k in keys:
            user_config[k] = user_data[k]
        return user_config

    @staticmethod
    def get_characters_list(table_data: list[dict]) -> list[str]:
        """Возвращает список всех героев."""
        characters = list(table_data[ts.CHARACTER_NAME_ROW].keys())[ts.CHARACTER_COLUMN_FIRST:ts.CHARACTER_COLUMN_LAST]
        return characters