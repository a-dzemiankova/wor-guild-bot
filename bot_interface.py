from telebot import TeleBot, types
from dotenv import load_dotenv
import os
from parser import Table
from settings import TableSettings as ts, backup_messages_filename
import time
import pickle
import logging


load_dotenv()
token = os.getenv('TOKEN')
table_link = os.getenv('TABLE_LINK')

logging.basicConfig(
    level=logging.DEBUG if os.getenv('DEBUG') == '1' else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info('Сервер запущен.')

bot = TeleBot(token)
logger.info('Бот создан.')


table = Table(table_link)
guilds = table.get_worksheets()
table_data = {}
for guild in guilds:
    table_data[guild] = {}
    table_data[guild].setdefault('data', table.extract_data_from_sheet(guild))
    table_data[guild].setdefault('last_extract_date', time.time())


def data_from_sheet(guild):
    if table_data[guild]['last_extract_date'] < time.time() - ts.UPDATE_RANGE:
        logger.info(f"Данные по гильдии {guild} обновлены")
        table_data[guild].setdefault('data', table.extract_data_from_sheet(guild))
        table_data[guild]['last_extract_date'] = time.time()

    return table_data[guild]['data']


# <user_id>: {
#       'messages_ids': {'first_message': 01, 'second_message': 02},
#       'characters_config': {'<character>': 0, '<character>': 1},
#       'state': 'active' | 'idle,
#       'timer': 000321
#       'guild': 'феникс'
#       }
# <user_id_2> : ...
users_data = {}
messages_to_delete = {}

if os.path.exists(backup_messages_filename):
    with open(backup_messages_filename, 'rb') as f:
        messages_to_delete = pickle.load(f)
        logger.info("Получены messages_to_delete из файла")

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
                        if 'message to delete not found' in str(e) or "message can't be deleted for everyone" in str(e):
                            pass
                        else:
                            logger.error(str(e))
                            raise

                messages_to_delete[user_id] = list()
                messages_to_delete[user_id].append(warning_message.message_id)


def dump_data_to_file(messages):
    with open(backup_messages_filename, 'wb') as f:
        pickle.dump(messages, f)


def check_for_warning(user_id):
    if users_data.get(user_id, {}).get('messages_ids', {}).get('warning_message', {}):
        try:
            bot.delete_message(user_id, users_data[user_id]['messages_ids']['warning_message'])
        except Exception as e:
            if 'message is not modified' in str(e):
                pass
            else:
                logger.error(str(e))
                raise
        finally:
            users_data[user_id]['messages_ids'].pop('warning_message')


def edit_characters_list(call, markup=None):
    user_id = call.message.chat.id
    current_list = '\n'.join(f"{k} - {v}" for k, v in users_data[user_id]['characters_config'].items()) \
        if users_data[user_id]['characters_config'] else '**Пока пусто**'

    try:
        bot.edit_message_text(chat_id=user_id, message_id=users_data[user_id]['messages_ids']['first_message'],
                          text=f"Список героев: \n\n{current_list}\n\n", reply_markup=markup)
    except Exception as e:
        if 'message is not modified' in str(e):
            pass
        else:
            logger.error(str(e))
            raise


def warning_too_fast_click(call, user_id):
    try:
        current_time = time.time()

        if users_data.get(user_id, {}).get('timer', None) and current_time - users_data[user_id]['timer'] < 1:
            return bot.answer_callback_query(call.id, "Слишком быстро! Подождите немного.")

        users_data[user_id]['timer'] = current_time
        bot.answer_callback_query(call.id)

    except Exception as e:
        if 'query is too old' in str(e):
            pass
        else:
            logger.error(str(e))
            raise


def clear_previous_messages(user_id):
    if users_data.get(user_id, {}).get('messages_ids', {}):
        for v in users_data[user_id]['messages_ids'].values():
            try:
                bot.delete_message(user_id, v)
            except Exception as e:
                if 'message to delete not found' in str(e) or "message can't be deleted for everyone" in str(e):
                    pass
                else:
                    logger.error(str(e))
                    raise


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    logger.debug(f"Бот запущен пользователем {user_id}")
    messages_to_delete[user_id] = list()
    messages_to_delete[user_id].append(message.id)
    check_for_warning(user_id)

    if users_data.get(user_id, {}).get('state', None) == "active":
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
    btn1 = types.InlineKeyboardButton('Начать поиск', callback_data='guild')
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
    logger.debug(f"Бот перезапущен пользователем {user_id}")
    messages_to_delete[user_id].append(message.id)

    dump_data_to_file(messages_to_delete)
    clear_previous_messages(user_id)

    users_data[user_id]['state'] = "idle"
    users_data[user_id]['characters_config'] = {}
    users_data[user_id]['messages_ids'] = {}

    start(message)


@bot.callback_query_handler(func=lambda call: call.data == 'guild')
def choose_guild(call):
    user_id = call.message.chat.id
    warning_too_fast_click(call, user_id)
    check_for_warning(user_id)

    markup = types.InlineKeyboardMarkup(row_width=1)
    btns = []
    for guild in guilds:
        btns.append(types.InlineKeyboardButton(guild, callback_data=f"search_{guild}"))
    markup.add(*btns)
    try:
        bot.edit_message_text(chat_id=user_id, message_id=users_data[user_id]['messages_ids']['second_message'],
                              text="Выберите гильдию:", reply_markup=markup)
    except Exception as e:
        if 'message is not modified' in str(e):
            pass
        else:
            logger.error(str(e))
            raise


@bot.callback_query_handler(func=lambda call: call.data.startswith('search'))
def choose_character(call):
    user_id = call.message.chat.id
    warning_too_fast_click(call, user_id)
    check_for_warning(user_id)

    if 'guild' not in users_data[user_id]:
        guild = call.data.split('_')[1]
        users_data[user_id]['guild'] = guild
        logger.debug(f"Пользователь {user_id} начал работу с гильдией {guild}")

    markup = types.InlineKeyboardMarkup(row_width=3)
    btns = []
    guild_data = data_from_sheet(users_data[user_id]['guild'])
    if not guild_data:
        clear_previous_messages(user_id)
        warning_message = bot.send_message(user_id, f"Нет данных по гильдии \"{users_data[user_id]['guild']}\"."
                                                    f" Нажмите /restart чтобы начать заново.")
        if 'messages_ids' not in users_data[user_id]:
            users_data[user_id]['messages_ids'] = {}
        users_data[user_id]['messages_ids']['warning_message'] = warning_message.message_id
        messages_to_delete[user_id].append(warning_message.message_id)
        dump_data_to_file(messages_to_delete)
        return
    characters = table.get_characters_list(guild_data)
    for character in characters:
        if character not in users_data[user_id]['characters_config']:
            btns.append(types.InlineKeyboardButton(character, callback_data=f"id_{character}"))
    markup.add(*btns)

    try:
        bot.edit_message_text(chat_id=user_id, message_id=users_data[user_id]['messages_ids']['second_message'],
                          text="Выберите героя для добавления в список:", reply_markup=markup)
    except Exception as e:
        if 'message is not modified' in str(e):
            pass
        else:
            logger.error(str(e))
            raise

    edit_characters_list(call)


@bot.callback_query_handler(func=lambda call: call.data.startswith('id'))
def choose_evo(call):
    user_id = call.message.chat.id
    check_for_warning(user_id)
    warning_too_fast_click(call, user_id)

    character = call.data.split('_')[1]
    logger.debug(f"Пользователь {user_id} выбрал героя {character}")
    markup = types.InlineKeyboardMarkup(row_width=2)
    btns = []
    for evo in ts.EVOS:
        btns.append(types.InlineKeyboardButton(f"{evo}", callback_data=f"evo_{character}_{evo}"))
    markup.add(*btns)

    try:
        bot.edit_message_text(chat_id=user_id, message_id=users_data[user_id]['messages_ids']['second_message'],
                              text=f"Выберите пробуду для {character}:")
        bot.edit_message_reply_markup(user_id, call.message.id, reply_markup=markup)
    except Exception as e:
        if 'message is not modified' in str(e):
            pass
        else:
            logger.error(str(e))
            raise


@bot.callback_query_handler(func=lambda call: call.data.startswith('evo'))
def manage_config(call):
    user_id = call.message.chat.id
    check_for_warning(user_id)
    warning_too_fast_click(call, user_id)

    character = call.data.split('_')[1]
    evo = call.data.split('_')[2]
    logger.debug(f"Пользователь {user_id} выбрал пробуду {evo} для героя {character}")
    users_data[user_id]['characters_config'][character] = evo

    markup = types.InlineKeyboardMarkup(row_width=2)

    btn1 = types.InlineKeyboardButton('Закончить', callback_data='finish')
    btn2 = types.InlineKeyboardButton(f"Отменить: {character}", callback_data=f"change_{character}")
    markup.add(btn1, btn2)

    if len(users_data[user_id]['characters_config']) < ts.MAX_HEROES_TO_CHOSE:
        btn3 = types.InlineKeyboardButton('Продолжить', callback_data='continue')
        markup.add(btn3)

    edit_characters_list(call, markup=markup)
    bot.delete_message(user_id, users_data[user_id]['messages_ids']['second_message'])
    users_data[user_id]['messages_ids'].pop('second_message')


@bot.callback_query_handler(func=lambda call: call.data.startswith('change'))
def change_last_choice(call):
    user_id = call.message.chat.id
    check_for_warning(user_id)
    warning_too_fast_click(call, user_id)
    character = call.data.split('_')[1]
    logger.debug(f"Пользователь {user_id} отменил выбор героя {character}")
    users_data[user_id]['characters_config'].pop(character)

    continue_search(call)


@bot.callback_query_handler(func=lambda call: call.data == 'continue')
def continue_search(call):
    user_id = call.message.chat.id
    check_for_warning(user_id)
    warning_too_fast_click(call, user_id)

    second_message = bot.send_message(user_id, "Загружаю список героев...")
    messages_to_delete[user_id].append(second_message.message_id)
    dump_data_to_file(messages_to_delete)
    users_data[user_id]['messages_ids']['second_message'] = second_message.message_id

    choose_character(call)


@bot.callback_query_handler(func=lambda call: call.data == 'finish')
def find_players(call):
    user_id = call.message.chat.id
    logger.debug(f"Пользователь {user_id} получил итоговый список")
    check_for_warning(user_id)
    warning_too_fast_click(call, user_id)

    try:
        bot.delete_message(user_id, users_data[user_id]['messages_ids']['first_message'])
    except Exception as e:
        if 'message to delete not found' in str(e) or "message can't be deleted for everyone" in str(e):
            pass
        else:
            logger.error(str(e))
            raise

    guild_data = data_from_sheet(users_data[user_id]['guild'])
    players = table.get_players(users_data[user_id]['characters_config'], guild_data)
    alt_players = table.get_alternative_players(users_data[user_id]['characters_config'], guild_data)
    players_str = '\n'.join(f"{players[i][0]} - {players[i][1]}" for i in range(len(players))) if players else \
        '**Точных совпадений не найдено.**'
    alt_players_str = '\n'.join(f"{alt_players[i][0]} - {alt_players[i][1]}" for i in range(len(alt_players))) if \
        alt_players else "**Пусто**."
    final_list = '\n'.join(f"{k} - {v}" for k, v in users_data[user_id]['characters_config'].items())
    text = f"Итоговый список:\n\n{final_list}\n\nИгроки с нужными пробудами (указанная или выше):\n\n{players_str}\n\n" \
           f"Игроки с наличием искомых героев:\n\n" \
           f"{alt_players_str}\n\nНажми /start чтобы начать заново." if users_data[user_id]['characters_config'] else \
        "\nВы не выбрали ни одного героя.\n\nНажмите /start чтобы начать заново."

    bot.send_message(user_id, text)
    messages_to_delete[user_id] = list()
    dump_data_to_file(messages_to_delete)
    users_data[user_id]['state'] = "idle"
    users_data[user_id].pop('guild')


logger.info("Бот запущен.")
bot.infinity_polling()

