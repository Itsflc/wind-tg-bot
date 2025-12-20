import telebot
import requests
import sqlite3
import re
import json

bot = telebot.TeleBot("...................................")

def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

MSG = load_json("messages.json")

help_message = MSG["help"]
start_message = MSG["start"]

@bot.message_handler(commands=['start'])
def otvet_start(message):
    baza = sqlite3.connect("bazadannih.sql")
    cursor = baza.cursor()
    user_id = message.from_user.id

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name1 TEXT, lat1 REAL, lon1 REAL,
        name2 TEXT, lat2 REAL, lon2 REAL,
        name3 TEXT, lat3 REAL, lon3 REAL,
        name4 TEXT, lat4 REAL, lon4 REAL,
        name5 TEXT, lat5 REAL, lon5 REAL, 
        speed_setting INTEGER DEFAULT 0, 
        direction_setting INTEGER DEFAULT 0)
    """)

    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'speed_setting' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN speed_setting INTEGER DEFAULT 0")

    if 'direction_setting' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN direction_setting INTEGER DEFAULT 0")

    cursor.execute("""
    INSERT OR IGNORE INTO users (id, speed_setting, direction_setting) 
    VALUES (?, ?, ?)""", (user_id, 0, 0))

    baza.commit()
    cursor.close()
    baza.close()
    bot.send_message(message.chat.id, start_message)


@bot.message_handler(commands=['wind'])
def otvet_wind(message):
    bot.send_message(message.chat.id, "Пришлите свои координаты")


@bot.message_handler(func=lambda message: is_coord(message.text))
def handle_text_coordinates(message):
    lat, lon = parse_coord(message.text)

    if lat > 90 or lat < -90 or lon > 180 or lon < -180:
        bot.send_message(message.chat.id, "Некорректные координаты")
    else:
        user_id = message.from_user.id
        message_id = message.chat.id
        obrab_location(lat, lon, message_id, user_id)


def is_coord(text):
    text = text.replace(',', '.')
    pattern = r'^[\s]*[-+]?\d+\.?\d*[\s,;]+[-+]?\d+\.?\d*[\s]*$'
    return bool(re.match(pattern, text.strip()))


def parse_coord(text):
    text = text.replace(',', '.')
    numbers = re.findall(r'[-+]?\d+\.?\d*', text)
    return float(numbers[0]), float(numbers[1])


@bot.message_handler(commands=['favorite'])
def otvet_favorite(message):
    user_id = message.from_user.id
    baza = sqlite3.connect("bazadannih.sql")
    cursor = baza.cursor()

    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()

    if not user_data:
        bot.send_message(message.chat.id, "У вас нет избранных локаций")
        cursor.close()
        baza.close()
        return

    favorites_text = "Ваши избранные локации:\n\n"
    has_favorites = False

    for i in range(1, 6):
        name = user_data[i * 3 - 2]
        lat = user_data[i * 3 - 1]
        lon = user_data[i * 3]

        if name and lat and lon:
            has_favorites = True
            favorites_text += f"{i}. {name}\nКоординаты: {lat}, {lon}\n"

    if not has_favorites:
        favorites_text = "У вас нет избранных локаций"

    markup = telebot.types.InlineKeyboardMarkup()
    if has_favorites:
        for i in range(1, 6):
            name = user_data[i * 3 - 2]
            if name:
                button = telebot.types.InlineKeyboardButton(f"{name}", callback_data=f"fav_{i}")
                markup.add(button)

    bot.send_message(message.chat.id, favorites_text, reply_markup=markup)
    cursor.close()
    baza.close()


@bot.callback_query_handler(func=lambda call: call.data.startswith("fav_"))
def handle_favorite_select(call):
    user_id = call.from_user.id
    fav_index = int(call.data.split("_")[1])

    baza = sqlite3.connect("bazadannih.sql")
    cursor = baza.cursor()

    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()

    if not user_data:
        bot.answer_callback_query(call.id, "Локация не найдена")
        return

    name_col = f"name{fav_index}"
    lat_col = f"lat{fav_index}"
    lon_col = f"lon{fav_index}"

    cursor.execute(f"SELECT {name_col}, {lat_col}, {lon_col} FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()

    if result and result[1] and result[2]:
        name, lat, lon = result
        obrab_location_from_favorite(lat, lon, call.message.chat.id, user_id, fav_index, name)

    cursor.close()
    baza.close()
    bot.answer_callback_query(call.id)


@bot.message_handler(commands=['settings'])
def otvet_settings(message):
    user_id = message.from_user.id
    text, setting_markup = find_settings(user_id)
    bot.send_message(message.chat.id, text, reply_markup=setting_markup)


@bot.callback_query_handler(func=lambda call: call.data == "speed_change")
def handle_speed_change(call):
    user_id = call.from_user.id
    baza = sqlite3.connect("bazadannih.sql")
    cursor = baza.cursor()

    cursor.execute("SELECT speed_setting FROM users WHERE id = ?", (user_id,))
    speed = cursor.fetchone()[0]
    new_speed = 1 - speed

    cursor.execute("UPDATE users SET speed_setting = ? WHERE id = ?", (new_speed, user_id))
    baza.commit()

    text, setting_markup = find_settings(user_id)

    bot.edit_message_text(
        text=text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=setting_markup)

    bot.answer_callback_query(call.id)
    cursor.close()
    baza.close()


@bot.callback_query_handler(func=lambda call: call.data == "direction_change")
def handle_direction_change(call):
    user_id = call.from_user.id
    baza = sqlite3.connect("bazadannih.sql")
    cursor = baza.cursor()

    cursor.execute("SELECT direction_setting FROM users WHERE id = ?", (user_id,))
    direction = cursor.fetchone()[0]
    new_direction = 1 - direction

    cursor.execute("UPDATE users SET direction_setting = ? WHERE id = ?", (new_direction, user_id))
    baza.commit()

    text, setting_markup = find_settings(user_id)

    bot.edit_message_text(
        text=text,
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=setting_markup)

    bot.answer_callback_query(call.id)
    cursor.close()
    baza.close()


@bot.message_handler(commands=['help'])
def otvet_help(message):
    bot.send_message(message.chat.id, help_message)


@bot.message_handler(content_types=['location'])
def otvet_location(message):
    lat = float(message.location.latitude)
    lon = float(message.location.longitude)
    message_id = message.chat.id
    user_id = message.from_user.id
    obrab_location(lat, lon, message_id, user_id)


@bot.message_handler(content_types=['venue'])
def handle_venue(message):
    lat = float(message.venue.location.latitude)
    lon = float(message.venue.location.longitude)
    message_id = message.chat.id
    user_id = message.from_user.id

    obrab_location(lat, lon, message_id, user_id)


@bot.message_handler(content_types=['photo', 'video', 'audio', 'contact', 'document', 'voice', 'animation'])
def otvet_notlocation(message):
    bot.reply_to(message, "Бот может обработать только локацию")


@bot.message_handler()
def otvet_notcommand(message):
    bot.reply_to(message, "Команда не найдена.\n/help - список доступных команд")


def obrab_location(lat: float, lon: float, message_id: int, user_id: int):
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "relative_humidity_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m",
        "timezone": "auto",
    }
    response = requests.get(url, params=params, timeout=15)
    weather_data = response.json()["current"]

    openmeteo_humidity = weather_data.get('relative_humidity_2m', 'Нет данных')
    openmeteo_wind_speed = weather_data.get('wind_speed_10m', 'Нет данных')
    openmeteo_wind_dir = weather_data.get('wind_direction_10m', 'Нет данных')
    openmeteo_wind_gust = weather_data.get('wind_gusts_10m', 'Нет данных')

    baza = sqlite3.connect("bazadannih.sql")
    cursor = baza.cursor()

    cursor.execute("SELECT speed_setting FROM users WHERE id = ?", (user_id,))
    speed_setting = cursor.fetchone()[0]
    speed = "м/с" if speed_setting == 0 else "км/ч"
    if speed_setting != 0:
        openmeteo_wind_speed *= 3.6
        openmeteo_wind_speed = openmeteo_wind_speed - openmeteo_wind_speed % 0.01
        openmeteo_wind_gust *= 3.6
        openmeteo_wind_gust = openmeteo_wind_gust - openmeteo_wind_gust % 0.01

    cursor.execute("SELECT direction_setting FROM users WHERE id = ?", (user_id,))
    direction_setting = cursor.fetchone()[0]

    DIRECTIONS = ["Север", "Северо-восток", "Восток", "Юго-восток", "Юг", "Юго-запад", "Запад", "Северо-запад"]
    wind_direction = DIRECTIONS[int((openmeteo_wind_dir + 22.5) / 45) % 8]

    direction_data = f"{openmeteo_wind_dir}°" if direction_setting == 0 else wind_direction

    wind_data = f"""
    Широта: {lat}
Долгота: {lon}

Ветер:
    Скорость: {openmeteo_wind_speed} {speed}
    Направление: {direction_data}
    Порывы: {openmeteo_wind_gust} {speed}

Влажность: {openmeteo_humidity}%
"""

    markup = telebot.types.InlineKeyboardMarkup()
    add_button = telebot.types.InlineKeyboardButton("Добавить в избранное", callback_data=f"addfav_{lat}_{lon}")
    markup.add(add_button)

    bot.send_message(message_id, wind_data, reply_markup=markup)


def obrab_location_from_favorite(lat: float, lon: float, message_id: int, user_id: int, fav_index: int, name: str):
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "relative_humidity_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m",
        "timezone": "auto",
    }
    response = requests.get(url, params=params, timeout=15)
    weather_data = response.json()["current"]

    openmeteo_humidity = weather_data.get('relative_humidity_2m', 'Нет данных')
    openmeteo_wind_speed = weather_data.get('wind_speed_10m', 'Нет данных')
    openmeteo_wind_dir = weather_data.get('wind_direction_10m', 'Нет данных')
    openmeteo_wind_gust = weather_data.get('wind_gusts_10m', 'Нет данных')

    baza = sqlite3.connect("bazadannih.sql")
    cursor = baza.cursor()

    cursor.execute("SELECT speed_setting FROM users WHERE id = ?", (user_id,))
    speed_setting = cursor.fetchone()[0]
    speed = "м/с" if speed_setting == 0 else "км/ч"
    if speed_setting != 0:
        openmeteo_wind_speed *= 3.6
        openmeteo_wind_speed = openmeteo_wind_speed - openmeteo_wind_speed % 0.01
        openmeteo_wind_gust *= 3.6
        openmeteo_wind_gust = openmeteo_wind_gust - openmeteo_wind_gust % 0.01

    cursor.execute("SELECT direction_setting FROM users WHERE id = ?", (user_id,))
    direction_setting = cursor.fetchone()[0]

    DIRECTIONS = ["Север", "Северо-восток", "Восток", "Юго-восток", "Юг", "Юго-запад", "Запад", "Северо-запад"]
    wind_direction = DIRECTIONS[int((openmeteo_wind_dir + 22.5) / 45) % 8]

    direction_data = f"{openmeteo_wind_dir}°" if direction_setting == 0 else wind_direction

    wind_data = f"""
    Избранная локация: {name}
    Широта: {lat}
Долгота: {lon}

Ветер:
    Скорость: {openmeteo_wind_speed} {speed}
    Направление: {direction_data}
    Порывы: {openmeteo_wind_gust} {speed}

Влажность: {openmeteo_humidity}%
"""

    markup = telebot.types.InlineKeyboardMarkup()
    delete_button = telebot.types.InlineKeyboardButton("Удалить из избранного", callback_data=f"delfav_{fav_index}")
    markup.add(delete_button)

    bot.send_message(message_id, wind_data, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("addfav_"))
def handle_add_favorite(call):
    user_id = call.from_user.id
    data_parts = call.data.split("_")
    lat = float(data_parts[1])
    lon = float(data_parts[2])

    baza = sqlite3.connect("bazadannih.sql")
    cursor = baza.cursor()

    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()

    if not user_data:
        bot.answer_callback_query(call.id, "Ошибка")
        return

    free_slot = None
    for i in range(1, 6):
        name_col = f"name{i}"
        cursor.execute(f"SELECT {name_col} FROM users WHERE id = ?", (user_id,))
        name = cursor.fetchone()[0]

        if not name:
            free_slot = i
            break

    if free_slot is None:
        bot.answer_callback_query(call.id, "Достигнут лимит в 5 избранных локаций")
        cursor.close()
        baza.close()
        return

    msg = bot.send_message(call.message.chat.id, "Введите название для этой локации:")
    bot.register_next_step_handler(msg, save_favorite_name, user_id, lat, lon, free_slot)

    bot.answer_callback_query(call.id)
    cursor.close()
    baza.close()


def save_favorite_name(message, user_id, lat, lon, slot):
    name = message.text.strip()

    if not name:
        bot.send_message(message.chat.id, "Название не может быть пустым")
        return

    baza = sqlite3.connect("bazadannih.sql")
    cursor = baza.cursor()

    cursor.execute(f"""
        UPDATE users 
        SET name{slot} = ?, lat{slot} = ?, lon{slot} = ?
        WHERE id = ?
    """, (name, lat, lon, user_id))

    baza.commit()
    cursor.close()
    baza.close()

    bot.send_message(message.chat.id, f"Локация '{name}' добавлена в избранное")


@bot.callback_query_handler(func=lambda call: call.data.startswith("delfav_"))
def handle_delete_favorite(call):
    user_id = call.from_user.id
    fav_index = int(call.data.split("_")[1])

    baza = sqlite3.connect("bazadannih.sql")
    cursor = baza.cursor()

    cursor.execute(f"""
        UPDATE users 
        SET name{fav_index} = NULL, lat{fav_index} = NULL, lon{fav_index} = NULL
        WHERE id = ?
    """, (user_id,))

    baza.commit()
    cursor.close()
    baza.close()

    bot.edit_message_text(
        text="Локация удалена из избранного",
        chat_id=call.message.chat.id,
        message_id=call.message.message_id
    )
    bot.answer_callback_query(call.id, "Локация удалена")


def find_settings(user_id):
    baza = sqlite3.connect("bazadannih.sql")
    cursor = baza.cursor()

    cursor.execute("SELECT speed_setting FROM users WHERE id = ?", (user_id,))
    speed_setting = cursor.fetchone()[0]
    speed = "м/с" if speed_setting == 0 else "км/ч"

    cursor.execute("SELECT direction_setting FROM users WHERE id = ?", (user_id,))
    direction_setting = cursor.fetchone()[0]
    direction = "в градусах" if direction_setting == 0 else "в направлениях"

    text = f"Ваши текущие настройки:\nФормат отображения скорости - {speed}\nФормат отображения направления - {direction}"

    speed_data = "м/с ➜ км/ч" if speed_setting == 0 else "км/ч ➜ м/с"
    direction_data = "° ➜ направления" if direction_setting == 0 else "направления ➜ °"

    setting_markup = telebot.types.InlineKeyboardMarkup()
    speed_button = telebot.types.InlineKeyboardButton(speed_data, callback_data="speed_change")
    direction_button = telebot.types.InlineKeyboardButton(direction_data, callback_data="direction_change")
    setting_markup.add(speed_button, direction_button)

    cursor.close()
    baza.close()

    return text, setting_markup


bot.polling(none_stop=True)
