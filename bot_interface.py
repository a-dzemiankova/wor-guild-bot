from telebot import TeleBot, types
from dotenv import load_dotenv
import os
from parser import Table
from settings import TableSettings as ts, backup_messages_filename
import time
import pickle


load_dotenv()
token = os.getenv('TOKEN')
table_link = os.getenv('TABLE_LINK')

bot = TeleBot(token)


class CallbackData:
    def __init__(self, fl=None, character=None, evo=None):
        self.fl = fl
        self.character = character
        self.evo = evo

    def to_str(self):
        return '_'.join([str(v) for v in self.__dict__.values() if v is not None])

    @staticmethod
    def str_to_callback(callback_data: str):
        if '_' in callback_data:
            evo = None
            parts = callback_data.split("_")
            fl = parts[0]
            character = parts[1]
            if len(parts) > 2:
                evo = parts[2]
            return CallbackData(fl=fl, character=character, evo=evo)
        return CallbackData(character=callback_data)


table = Table(table_link)
table_data = table.extract_data_from_sheet(ts.SHEET_1)
characters = table.get_characters_list(table_data)


# <user_id>: {
#       'messages_ids': {'first_message': 01, 'second_message': 02},
#       'characters_config': {'<character>': 0, '<character>': 1},
#       'state': 'active' | 'idle,
#       'timer': 000321
#       }
# <user_id_2> : ...
users_data = {}
messages_to_delete = {}

if os.path.exists(backup_messages_filename):
    with open(backup_messages_filename, 'rb') as f:
        messages_to_delete = pickle.load(f)
        for user_id, messages_ids in messages_to_delete.items():
            if messages_ids:
                warning_message = bot.send_message(user_id, 'Сервер был перезапущен. Нажмите /start, чтобы начать заново.')
                users_data[user_id] = {}
                users_data[user_id]['messages_ids'] = {}
                users_data[user_id]['messages_ids']['warning_messages'] = warning_message.message_id
                for message_id in messages_ids:
                    try:
                        bot.delete_message(user_id, message_id)
                    except Exception as e:
                        if 'message to delete not found' in str(e):
                            pass
                        else:
                            raise
                messages_to_delete[user_id] = list()
                messages_to_delete[user_id].append(warning_message.message_id)


def dump_data_to_file(messages):
    with open(backup_messages_filename, 'wb') as f:
        pickle.dump(messages, f)


def check_for_warning(user_id):
    if 'messages_ids' in users_data[user_id] and 'warning_message' in users_data[user_id]['messages_ids']:
        try:
            bot.delete_message(user_id, users_data[user_id]['messages_ids']['warning_message'])
        except Exception as e:
            if 'message is not modified' in str(e):
                pass
            else:
                raise
        finally:
            users_data[user_id]['messages_ids'].pop('warning_message')


def edit_characters_list(call, markup=None):
    user_id = call.message.chat.id
    current_list = '\n'.join(f"{k} - {v}" for k, v in users_data[user_id]['characters_config'].items()) \
        if users_data[user_id]['characters_config'] else '**Пока пусто**'
    try:
        bot.edit_message_text(chat_id=user_id, message_id=users_data[user_id]['messages_ids']['first_message'],
                          text=f'Список героев: \n\n{current_list}\n\n', reply_markup=markup)
    except Exception as e:
        if 'message is not modified' in str(e):
            pass
        else:
            raise


def handle_too_fast_click(call, user_id):
    try:
        current_time = time.time()
        if 'timer' in users_data[user_id] and current_time - users_data[user_id]['timer'] < 1:
            return bot.answer_callback_query(call.id, "Слишком быстро! Подождите немного.")
        users_data[user_id]['timer'] = current_time
        bot.answer_callback_query(call.id)
    except Exception as e:
        if 'query is too old' in str(e):
            pass
        else:
            raise


def clear_previous_messages(user_id):
    if user_id in users_data and users_data[user_id]['messages_ids']:
        for v in users_data[user_id]['messages_ids'].values():
            try:
                bot.delete_message(user_id, v)
            except Exception as e:
                if 'message to delete not found' in str(e):
                    pass
                else:
                    raise


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    messages_to_delete[user_id] = list()
    messages_to_delete[user_id].append(message.id)
    if user_id in users_data:
        check_for_warning(user_id)
    if user_id in users_data and 'state' in users_data[user_id] and users_data[user_id]['state'] == "active":
        warning_message = bot.send_message(user_id, "Вы уже начали взаимодействие с ботом. Завершите текущий сценарий "
                                                    "или нажмите /restart, чтобы очистить список и начать заново")
        messages_to_delete[user_id].append(warning_message.message_id)
        dump_data_to_file(messages_to_delete)
        if 'messages_ids' not in users_data[user_id]:
            users_data[user_id]['messages_ids'] = {}
        users_data[user_id]['messages_ids']['warning_message'] = warning_message.message_id
        bot.delete_message(user_id, message.id)
        return
    clear_previous_messages(user_id)
    users_data[user_id] = {}
    users_data[user_id]['state'] = "active"
    users_data[user_id]['characters_config'] = {}
    users_data[user_id]['messages_ids'] = {}
    markup = types.InlineKeyboardMarkup(row_width=3)
    btn1 = types.InlineKeyboardButton('Начать поиск', callback_data='search')
    markup.add(btn1)
    first_message = bot.send_message(user_id, 'Привет!')
    second_message = bot.send_message(user_id, 'Давай найдем нужных тебе игроков.', reply_markup=markup)
    users_data[user_id]['messages_ids']['first_message'] = first_message.message_id
    users_data[user_id]['messages_ids']['second_message'] = second_message.message_id
    messages_to_delete[user_id].append(first_message.message_id)
    messages_to_delete[user_id].append(second_message.message_id)
    dump_data_to_file(messages_to_delete)
    bot.delete_message(user_id, message.id)


@bot.message_handler(commands=['restart'])
def restart(message):
    user_id = message.chat.id
    messages_to_delete[user_id].append(message.id)
    dump_data_to_file(messages_to_delete)
    clear_previous_messages(user_id)
    users_data[user_id]['state'] = "idle"
    users_data[user_id]['characters_config'] = {}
    users_data[user_id]['messages_ids'] = {}
    start(message)


@bot.callback_query_handler(func=lambda call: call.data == 'search')
def choose_character(call):
    user_id = call.message.chat.id
    handle_too_fast_click(call, user_id)
    check_for_warning(user_id)
    markup = types.InlineKeyboardMarkup(row_width=3)
    btns = []
    for character in characters:
        if character not in users_data[user_id]['characters_config']:
            callback = CallbackData(fl='id', character=character)
            callback_str = callback.to_str()
            btns.append(types.InlineKeyboardButton(character, callback_data=callback_str))
    markup.add(*btns)
    try:
        bot.edit_message_text(chat_id=user_id, message_id=users_data[user_id]['messages_ids']['second_message'],
                          text="Выберите героя для добавления в список:", reply_markup=markup)
    except Exception as e:
        if 'message is not modified' in str(e):
            pass
        else:
            raise
    edit_characters_list(call)


@bot.callback_query_handler(func=lambda call: call.data.startswith('id'))
def choose_evo(call):
    user_id = call.message.chat.id
    check_for_warning(user_id)
    handle_too_fast_click(call, user_id)
    callback_data = CallbackData.str_to_callback(call.data)
    character = callback_data.character
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = []
    for evo in ts.EVOS:
        callback = CallbackData(fl='evo', character=character, evo=evo)
        callback_str = callback.to_str()
        btns.append(types.InlineKeyboardButton(f"{evo}", callback_data=callback_str))
    markup.add(*btns)
    try:
        bot.edit_message_text(chat_id=user_id, message_id=users_data[user_id]['messages_ids']['second_message'],
                              text=f'Выберите пробуду для {character}:')
        bot.edit_message_reply_markup(user_id, call.message.id, reply_markup=markup)
    except Exception as e:
        if 'message is not modified' in str(e):
            pass
        else:
            raise


@bot.callback_query_handler(func=lambda call: call.data.startswith('evo'))
def manage_config(call):
    user_id = call.message.chat.id
    check_for_warning(user_id)
    handle_too_fast_click(call, user_id)
    callback_data = CallbackData.str_to_callback(call.data)
    character = callback_data.character
    evo = callback_data.evo
    users_data[user_id]['characters_config'][character] = evo
    markup = types.InlineKeyboardMarkup(row_width=2)
    callback = CallbackData(fl='change', character=character)
    callback_str = callback.to_str()
    btn1 = types.InlineKeyboardButton('Закончить', callback_data='finish')
    btn2 = types.InlineKeyboardButton(f'Отменить: {character}', callback_data=callback_str)
    btn3 = types.InlineKeyboardButton('Продолжить', callback_data='continue')
    markup.add(btn1, btn2)
    if len(users_data[user_id]['characters_config']) < 5:
        markup.add(btn3)
    edit_characters_list(call, markup=markup)
    bot.delete_message(user_id, users_data[user_id]['messages_ids']['second_message'])
    users_data[user_id]['messages_ids'].pop('second_message')


@bot.callback_query_handler(func=lambda call: call.data.startswith('change'))
def change_last_choice(call):
    user_id = call.message.chat.id
    check_for_warning(user_id)
    handle_too_fast_click(call, user_id)
    callback_data = CallbackData.str_to_callback(call.data)
    character = callback_data.character
    users_data[user_id]['characters_config'].pop(character)
    continue_search(call)


@bot.callback_query_handler(func=lambda call: call.data == 'continue')
def continue_search(call):
    user_id = call.message.chat.id
    check_for_warning(user_id)
    handle_too_fast_click(call, user_id)
    second_message = bot.send_message(user_id, "Загружаю список героев...")
    messages_to_delete[user_id].append(second_message.message_id)
    dump_data_to_file(messages_to_delete)
    users_data[user_id]['messages_ids']['second_message'] = second_message.message_id
    choose_character(call)


@bot.callback_query_handler(func=lambda call: call.data == 'finish')
def find_players(call):
    user_id = call.message.chat.id
    check_for_warning(user_id)
    handle_too_fast_click(call, user_id)
    players = table.get_players(users_data[user_id]['characters_config'], table_data)
    alt_players = table.get_alternative_players(users_data[user_id]['characters_config'], table_data)
    players_str = '\n'.join(f"{players[i][0]} - {players[i][1]}" for i in range(len(players))) if players else \
        '**Точных совпадений не найдено.**'
    alt_players_str = '\n'.join(f"{alt_players[i][0]} - {alt_players[i][1]}" for i in range(len(alt_players))) if \
        alt_players else "**Пусто**."
    final_list = '\n'.join(f"{k} - {v}" for k, v in users_data[user_id]['characters_config'].items())
    text = f'Итоговый список:\n\n{final_list}\n\nИгроки с нужными пробудами (указанная или выше):\n\n{players_str}\n\n' \
           f'Игроки с наличием искомых героев:\n\n' \
           f'{alt_players_str}\n\nНажми /start чтобы начать заново.' if users_data[user_id]['characters_config'] else \
        '\nВы не выбрали ни одного героя.\n\nНажмите /start чтобы начать заново.'
    try:
        bot.delete_message(user_id, users_data[user_id]['messages_ids']['first_message'])
    except Exception as e:
        if 'message to delete not found' in str(e):
            pass
        else:
            raise
    bot.send_message(user_id, text)
    messages_to_delete[user_id] = list()
    dump_data_to_file(messages_to_delete)
    users_data[user_id]['state'] = "idle"


bot.infinity_polling()