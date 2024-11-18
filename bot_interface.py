from telebot import TeleBot, types
from dotenv import load_dotenv
import os
from parser import Table

load_dotenv()
token = os.getenv('TOKEN')
bot = TeleBot(token)
table_link = os.getenv('TABLE_LINK')
table = Table(table_link)
config = dict()

table_data = table.extract_data_from_sheet('феникс')
characters = table.get_characters_list(table_data)



@bot.message_handler(commands=['start'])
def start(message):
    config.clear()
    markup = types.InlineKeyboardMarkup(row_width=3)
    btn1 = types.InlineKeyboardButton('Начать поиск', callback_data='search')
    markup.add(btn1)
    bot.send_message(message.chat.id, 'Привет! Давай найдем нужных тебе игроков.', reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data in ['search', 'restart'])
def choose_character(call):
    if call.data == 'restart':
        config.clear()
    markup = types.InlineKeyboardMarkup(row_width=3)
    btns = []
    for character in characters:
        btns.append(types.InlineKeyboardButton(character, callback_data=f"id_{character}"))
    markup.add(*btns)
    current_list = '\n'.join(f"{k} - {v}" for k, v in config.items()) if config else '**Пока пусто**'
    bot.send_message(call.message.chat.id, "Выберите героя для добавления в список:",
                     reply_markup=markup)
    bot.edit_message_text(f'Список героев: \n\n{current_list}\n\n', call.message.chat.id, call.message.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('id'))
def choose_evo(call):
    character = call.data.split('_')[1]
    config.setdefault(character, None)
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = []
    for i in range(6):
        btns.append(types.InlineKeyboardButton(f"{i}", callback_data=f'evo_{character}_{i}'))
    markup.add(*btns)
    bot.edit_message_text(f'Выберите пробуду для {character}:', call.message.chat.id, call.message.id)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('evo'))
def manage_config(call):
    data = call.data.split('_')
    character = data[1]
    evo = data[2]
    config[character] = evo
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton('Продолжить', callback_data='continue')
    btn2 = types.InlineKeyboardButton('Изменить выбор', callback_data=f'change_{character}')
    btn3 = types.InlineKeyboardButton('Закончить ввод', callback_data='finish')
    markup.add(btn1, btn2, btn3)
    bot.edit_message_text(f'Ваш выбор:\n{character} - {evo}', call.message.chat.id, call.message.id)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'continue')
def continue_search(call):
    bot.delete_message(call.message.chat.id, call.message.id - 1)
    choose_character(call)


@bot.callback_query_handler(func=lambda call: call.data.startswith('change'))
def change_choice(call):
    data = call.data.split('_')
    character = data[1]
    config.pop(character)
    bot.delete_message(call.message.chat.id, call.message.id - 1)
    choose_character(call)


@bot.callback_query_handler(func=lambda call: call.data == 'finish')
def find_players(call):
    players = table.get_players(config, table_data)
    players_str = '\n'.join(f"{players[i][0]} - {players[i][1]}" for i in range(len(players))) if players else \
        'Точных совпадений не найдено.'
    alt_players = table.get_alternative_players(config, table_data)
    alt_players_str = '\n'.join(f"{alt_players[i][0]} - {alt_players[i][1]}" for i in range(len(alt_players)))
    final_list = '\n'.join(f"{k} - {v}" for k, v in config.items())
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.id,
                          text=f'Итоговый список:\n\n{final_list}\n\nИгроки с нужными пробудами (указанная или выше):'
                               f'\n\n{players_str}\n\nИгроки с наличием искомых героев (пробуда 0 и выше):\n\n'
                               f'{alt_players_str}\n\nНажми /start чтобы начать заново')


bot.infinity_polling()
