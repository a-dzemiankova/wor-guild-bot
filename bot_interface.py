from telebot import TeleBot, types
from dotenv import load_dotenv
import os
from parser import Table
from settings import TableSettings as ts
import time


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

user_configs = dict()
user_messages_id = dict()
user_timers = dict()
user_states = dict()


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    if user_states.get(user_id) == "active":
        warning_message = bot.send_message(user_id, "Вы уже начали взаимодействие с ботом. Завершите текущий сценарий "
                                                    "перед повторным вызовом /start.")
        user_messages_id[user_id]['warning_message'] = warning_message.message_id
        bot.delete_message(user_id, message.id)
        return
    if user_id in user_messages_id and user_messages_id[user_id]:
        for v in user_messages_id[user_id].values():
            bot.delete_message(user_id, v)
    user_states[user_id] = "active"
    user_configs[user_id] = dict()
    user_messages_id[user_id] = dict()
    markup = types.InlineKeyboardMarkup(row_width=3)
    btn1 = types.InlineKeyboardButton('Начать поиск', callback_data='search')
    markup.add(btn1)
    first_message = bot.send_message(user_id, 'Привет!')
    second_message = bot.send_message(user_id, 'Давай найдем нужных тебе игроков.', reply_markup=markup)
    user_messages_id[user_id]['first_message'] = first_message.message_id
    user_messages_id[user_id]['second_message'] = second_message.message_id
    bot.delete_message(user_id, message.id)


def check_for_warning(user_id):
    if 'warning_message' in user_messages_id[user_id]:
        bot.delete_message(user_id, user_messages_id[user_id]['warning_message'])
        user_messages_id[user_id].pop('warning_message')


def edit_characters_list(call, markup=None):
    user_id = call.message.chat.id
    current_list = '\n'.join(f"{k} - {v}" for k, v in user_configs[user_id].items()) \
        if user_configs[user_id] else '**Пока пусто**'
    try:
        bot.edit_message_text(chat_id=user_id, message_id=user_messages_id[user_id]['first_message'],
                          text=f'Список героев: \n\n{current_list}\n\n', reply_markup=markup)
    except Exception as e:
        if 'message is not modified' in str(e):
            pass
        else:
            raise


def handle_too_fast_click(call, user_id):
    current_time = time.time()
    if user_id in user_timers and current_time - user_timers[user_id] < 1:
        return bot.answer_callback_query(call.id, "Слишком быстро! Подождите немного.")
    user_timers[user_id] = current_time
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == 'search')
def choose_character(call):
    user_id = call.message.chat.id
    handle_too_fast_click(call, user_id)
    check_for_warning(user_id)
    markup = types.InlineKeyboardMarkup(row_width=3)
    btns = []
    for character in characters:
        if character not in user_configs[user_id]:
            callback = CallbackData(fl='id', character=character)
            callback_str = callback.to_str()
            btns.append(types.InlineKeyboardButton(character, callback_data=callback_str))
    markup.add(*btns)
    try:
        bot.edit_message_text(chat_id=user_id, message_id=user_messages_id[user_id]['second_message'],
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
        bot.edit_message_text(chat_id=user_id, message_id=user_messages_id[user_id]['second_message'],
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
    user_configs[user_id][character] = evo
    markup = types.InlineKeyboardMarkup(row_width=2)
    callback = CallbackData(fl='change', character=character)
    callback_str = callback.to_str()
    btn1 = types.InlineKeyboardButton('Закончить', callback_data='finish')
    btn2 = types.InlineKeyboardButton(f'Отменить: {character}', callback_data=callback_str)
    btn3 = types.InlineKeyboardButton('Продолжить', callback_data='continue')
    markup.add(btn1, btn2)
    if len(user_configs[user_id]) < 5:
        markup.add(btn3)
    edit_characters_list(call, markup=markup)
    bot.delete_message(user_id, user_messages_id[user_id]['second_message'])
    user_messages_id[user_id].pop('second_message')


@bot.callback_query_handler(func=lambda call: call.data.startswith('change'))
def change_last_choice(call):
    user_id = call.message.chat.id
    check_for_warning(user_id)
    handle_too_fast_click(call, user_id)
    callback_data = CallbackData.str_to_callback(call.data)
    character = callback_data.character
    user_configs[user_id].pop(character)
    continue_search(call)


@bot.callback_query_handler(func=lambda call: call.data == 'continue')
def continue_search(call):
    user_id = call.message.chat.id
    check_for_warning(user_id)
    handle_too_fast_click(call, user_id)
    second_message = bot.send_message(user_id, "Загружаю список героев...")
    user_messages_id[user_id]['second_message'] = second_message.id
    choose_character(call)


@bot.callback_query_handler(func=lambda call: call.data == 'finish')
def find_players(call):
    user_id = call.message.chat.id
    check_for_warning(user_id)
    handle_too_fast_click(call, user_id)
    players = table.get_players(user_configs[user_id], table_data)
    alt_players = table.get_alternative_players(user_configs[user_id], table_data)
    players_str = '\n'.join(f"{players[i][0]} - {players[i][1]}" for i in range(len(players))) if players else \
        '**Точных совпадений не найдено.**'
    alt_players_str = '\n'.join(f"{alt_players[i][0]} - {alt_players[i][1]}" for i in range(len(alt_players))) if \
        alt_players else "**Пусто**."
    final_list = '\n'.join(f"{k} - {v}" for k, v in user_configs[user_id].items())
    text = f'Итоговый список:\n\n{final_list}\n\nИгроки с нужными пробудами (указанная или выше):\n\n{players_str}\n\n' \
           f'Игроки с наличием искомых героев:\n\n' \
           f'{alt_players_str}\n\nНажми /start чтобы начать заново.' if user_configs[user_id] else \
        '\nВы не выбрали ни одного героя.\n\nНажми /start чтобы начать заново.'
    try:
        bot.edit_message_text(chat_id=user_id, message_id=user_messages_id[user_id]['first_message'], text=text)
    except Exception as e:
        if 'message is not modified' in str(e):
            pass
        else:
            raise
    user_states[user_id] = "idle"


bot.infinity_polling()
