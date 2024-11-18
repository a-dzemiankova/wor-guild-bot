from telebot import TeleBot, types
from dotenv import load_dotenv
import os

load_dotenv()
token = os.getenv('TOKEN')
bot = TeleBot(token)

config = dict()


@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton('Начать поиск', callback_data='search')
    markup.add(btn1)
    bot.send_message(message.chat.id, 'Привет! Давай найдем нужных тебе игроков.', reply_markup=markup)
    print(f"Певрое сообщение - {message.chat.id}")


@bot.callback_query_handler(func=lambda call: call.data in ['search', 'restart'])
def choose_character(call):
    if len(config) == 3 and call.data == 'continue':
        res = '\n'.join(f"{k} - {v}" for k, v in config.items())
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn1 = types.InlineKeyboardButton('Подтвердить', callback_data='confirm')
        btn2 = types.InlineKeyboardButton('Начать заново', callback_data='restart')
        markup.add(btn1, btn2)
        bot.delete_message(call.message.chat.id, call.message.id)
        bot.send_message(call.message.chat.id, f" Итоговый список:\n\n{res}", reply_markup=markup)
    else:
        if call.data == 'restart':
            config.clear()
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton('Ингрид', callback_data='id_Ингрид')
        btn2 = types.InlineKeyboardButton('Аякс', callback_data='id_Аякс')
        btn3 = types.InlineKeyboardButton('Саргак', callback_data='id_Саргак')
        btn4 = types.InlineKeyboardButton('Претус', callback_data='id_Претус')
        btn5 = types.InlineKeyboardButton('Кир', callback_data='id_Кир')
        btn6 = types.InlineKeyboardButton('Хамет', callback_data='id_Хамет')
        markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
        current_list = '\n'.join(f"{k} - {v}" for k, v in config.items()) if config else '**Пока пусто**'
        bot.send_message(call.message.chat.id, "Выберите героя для добавления в список:",
                         reply_markup=markup)
        bot.edit_message_text(f'Список героев: \n\n{current_list}\n\n', call.message.chat.id, call.message.id)



@bot.callback_query_handler(func=lambda call: call.data.startswith('id'))
def choose_evo(call):
    character = call.data.split('_')[1]
    config.setdefault(character, None)
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton('1', callback_data=f'evo_{character}_1')
    btn2 = types.InlineKeyboardButton('2', callback_data=f'evo_{character}_2')
    btn3 = types.InlineKeyboardButton('3', callback_data=f'evo_{character}_3')
    markup.add(btn1, btn2, btn3)
    bot.edit_message_text(f'Выберите пробуду для {character}:', call.message.chat.id, call.message.id)
    bot.edit_message_reply_markup(call.message.chat.id, call.message.id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('evo'))
def manage_config(call):
    data = call.data.split('_')
    character = data[1]
    evo = data[2]
    config[character] = evo
    print(config)
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton('Продолжить', callback_data='continue')
    btn2 = types.InlineKeyboardButton('Изменить выбор', callback_data=f'change_{character}')
    markup.add(btn1, btn2)
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


@bot.callback_query_handler(func=lambda call: call.data == 'confirm')
def find_players(call):
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.id, text='Text')
    # логика с фильтром подсходящих игроков + кнопка "Начать заново" через колбэк restart
    config.clear()


bot.infinity_polling()
