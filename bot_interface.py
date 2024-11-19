import telebot
from telebot import TeleBot, types
from dotenv import load_dotenv
import os
from parser import Table
from settings import TableSettings, CallbackData

load_dotenv()
token = os.getenv('TOKEN')
table_link = os.getenv('TABLE_LINK')

bot = TeleBot(token)

table = Table(table_link)
table_data = table.extract_data_from_sheet(TableSettings.SHEET_1)
characters = table.get_characters_list(table_data)

messages_id = dict()
config = dict()


@bot.message_handler(commands=['start'])
def start(message):
    config.clear()
    markup = types.InlineKeyboardMarkup(row_width=3)
    btn1 = types.InlineKeyboardButton('Начать поиск', callback_data='search')
    markup.add(btn1)
    first_message = bot.send_message(message.chat.id, 'Привет!')
    second_message = bot.send_message(message.chat.id, 'Давай найдем нужных тебе игроков.', reply_markup=markup)
    messages_id['first_message'] = first_message.message_id
    messages_id['second_message'] = second_message.message_id


@bot.callback_query_handler(func=lambda call: call.data in ['search', 'restart'])
def choose_character(call):
    if call.data == 'restart':
        config.clear()
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup1 = types.InlineKeyboardMarkup(row_width=1)
    btns = []
    for character in characters:
        if character not in config:
            callback = CallbackData(fl='id', character=character)
            callback_str = callback.encode()
            btns.append(types.InlineKeyboardButton(character, callback_data=callback_str))
    btn1 = types.InlineKeyboardButton('Закончить ввод', callback_data='finish')
    markup.add(*btns)
    markup1.add(btn1)
    current_list = '\n'.join(f"{k} - {v}" for k, v in config.items()) if config else '**Пока пусто**'
    try:
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=messages_id['second_message'],
                              text="Выберите героя для добавления в список:", reply_markup=markup)
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=messages_id['first_message'],
                              text=f'Список героев: \n\n{current_list}\n\n', reply_markup=markup1)
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise


@bot.callback_query_handler(func=lambda call: call.data.startswith('id'))
def choose_evo(call):
    callback_data = CallbackData.decode(call.data)
    character = callback_data.character
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = []
    for evo in TableSettings.EVOS:
        callback = CallbackData(fl= 'evo', character=character, evo=evo)
        callback_str = callback.encode()
        btns.append(types.InlineKeyboardButton(f"{evo}", callback_data=callback_str))
    markup.add(*btns)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=messages_id['second_message'],
                          text=f'Выберите пробуду для {character}:')
    bot.edit_message_reply_markup(call.message.chat.id, call.message.id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('evo'))
def manage_config(call):
    callback_data = CallbackData.decode(call.data)
    character = callback_data.character
    evo = callback_data.evo
    markup = types.InlineKeyboardMarkup(row_width=2)
    callback = CallbackData(fl='continue', character=character, evo=evo)
    callback_str = callback.encode()
    btn1 = types.InlineKeyboardButton('Добавить в список', callback_data=callback_str)
    btn2 = types.InlineKeyboardButton('Изменить выбор', callback_data='search')
    markup.add(btn1, btn2)
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=messages_id['second_message'],
                          text=f'Ваш выбор:\n{character} - {evo}')
    bot.edit_message_reply_markup(call.message.chat.id, call.message.id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('continue'))
def continue_search(call):
    callback_data = CallbackData.decode(call.data)
    character = callback_data.character
    evo = callback_data.evo
    config[character] = evo
    choose_character(call)


@bot.callback_query_handler(func=lambda call: call.data == 'finish')
def find_players(call):
    players = table.get_players(config, table_data)
    players_str = '\n'.join(f"{players[i][0]} - {players[i][1]}" for i in range(len(players))) if players else \
        'Точных совпадений не найдено.'
    alt_players = table.get_alternative_players(config, table_data)
    alt_players_str = '\n'.join(f"{alt_players[i][0]} - {alt_players[i][1]}" for i in range(len(alt_players))) if \
        alt_players else "**Пусто**."
    final_list = '\n'.join(f"{k} - {v}" for k, v in config.items())
    text = f'Итоговый список:\n\n{final_list}\n\nИгроки с нужными пробудами (указанная или выше):\n\n{players_str}\n\n' \
           f'Игроки с наличием искомых героев (пробуда 0 и выше):\n\n' \
           f'{alt_players_str}\n\nНажми /start чтобы начать заново.' if config else \
        '\nВы не выбрали ни одного героя.\n\nНажми /start чтобы начать заново.'
    bot.delete_message(call.message.chat.id, messages_id['first_message'])
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=messages_id['second_message'], text=text)


bot.infinity_polling()