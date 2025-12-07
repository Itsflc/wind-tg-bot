#не окончательный вариант, нужно, чтобы новые команды бота отображались в меню команд


import telebot
import requests
import sqlite3
import re

bot = telebot.TeleBot("8383669473:AAFap3PPNxnyzN3KMaZazJPZAzPSjpo27qc")

help_message = """
/wind - пришлите координаты и узнайте информацию о ветре
/add_to_favorites - сохранить последнюю локацию в избранное
/favorites - показать избранные локации
/delete_favorite - удалить локацию из избранного
/help - список команд"""

start_message = """
/wind - пришлите координаты и узнайте информацию о ветре
/add_to_favorites - сохранить последнюю локацию в избранное
/favorites - показать избранные локации
/delete_favorite - удалить локацию из избранного
/help - список команд
"""

# Словарь для хранения последних координат каждого пользователя
last_coordinates = {}


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
        name5 TEXT, lat5 REAL, lon5 REAL
    ) """)

    cursor.execute("INSERT OR IGNORE INTO users(id) VALUES(?)", (user_id,))
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
        message_id = message.chat.id
        # Сохраняем координаты как последние для этого пользователя
        last_coordinates[message.from_user.id] = (lat, lon)
        obrab_location(lat, lon, message_id)


def is_coord(text):
    pattern = r'^[\s]*[-+]?\d+\.?\d*[\s,;]+[-+]?\d+\.?\d*[\s]*$'
    return bool(re.match(pattern, text.strip()))


def parse_coord(text):
    numbers = re.findall(r'[-+]?\d+\.?\d*', text)
    return float(numbers[0]), float(numbers[1])


# ========== ИЗБРАННОЕ ==========

@bot.message_handler(commands=['add_to_favorites'])
def add_to_favorites(message):
    """Сохранить последнюю локацию в избранное"""
    user_id = message.from_user.id

    # Проверяем, есть ли последние координаты
    if user_id not in last_coordinates:
        bot.send_message(message.chat.id,
                         "❌ Ошибка: сначала отправьте координаты командой /wind")
        return

    lat, lon = last_coordinates[user_id]

    # Запрашиваем название для сохранения
    bot.send_message(message.chat.id,
                     f"Координаты для сохранения: {lat:.4f}, {lon:.4f}\n"
                     "Введите название для этой локации:")

    # Регистрируем следующий шаг - обработку названия
    bot.register_next_step_handler(message, process_save_favorite, lat, lon, user_id)


def process_save_favorite(message, lat, lon, user_id):
    """Обработать название и сохранить в БД"""
    name = message.text.strip()

    if not name:
        bot.send_message(message.chat.id, "Название не может быть пустым.")
        return

    baza = sqlite3.connect("bazadannih.sql")
    cursor = baza.cursor()

    # Ищем первый свободный слот
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()

    if user_data:
        free_slot = None
        for i in range(1, 6):
            name_idx = 1 + (i - 1) * 3
            if user_data[name_idx] is None:
                free_slot = i
                break

        if free_slot:
            # Сохраняем в свободный слот
            cursor.execute(f"""
                UPDATE users 
                SET name{free_slot} = ?, lat{free_slot} = ?, lon{free_slot} = ?
                WHERE id = ?
            """, (name, lat, lon, user_id))

            baza.commit()
            bot.send_message(message.chat.id,
                             f"✅ Локация '{name}' сохранена в избранное (слот {free_slot})")
        else:
            bot.send_message(message.chat.id,
                             "❌ Все 5 слотов заняты!")
    else:
        bot.send_message(message.chat.id, "❌ Ошибка сохранения")

    baza.close()


@bot.message_handler(commands=['favorites'])
def show_favorites(message):
    """Показать избранные локации"""
    user_id = message.from_user.id

    baza = sqlite3.connect("bazadannih.sql")
    cursor = baza.cursor()

    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()

    baza.close()

    if not user_data:
        bot.send_message(message.chat.id, "У вас нет избранных локаций.")
        return

    # Проверяем, есть ли сохраненные локации
    has_favorites = False
    for i in range(1, 6):
        name_idx = 1 + (i - 1) * 3
        if user_data[name_idx] is not None:
            has_favorites = True
            break

    if not has_favorites:
        bot.send_message(message.chat.id, "У вас нет избранных локаций.")
        return

    # Показываем список с кнопками
    response = "📌 Выберите избранную локацию:\n\n"

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

    for i in range(1, 6):
        name_idx = 1 + (i - 1) * 3
        lat_idx = name_idx + 1
        lon_idx = name_idx + 2

        name = user_data[name_idx]
        if name:
            response += f"{i}. {name}\n"
            # Добавляем кнопку с номером
            markup.add(telebot.types.KeyboardButton(f"📍 {i}. {name}"))

    markup.add(telebot.types.KeyboardButton("❌ Отмена"))

    bot.send_message(message.chat.id, response, reply_markup=markup)


@bot.message_handler(commands=['delete_favorite'])
def delete_favorite(message):
    """Удалить локацию из избранного"""
    user_id = message.from_user.id

    baza = sqlite3.connect("bazadannih.sql")
    cursor = baza.cursor()

    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()

    baza.close()

    if not user_data:
        bot.send_message(message.chat.id, "У вас нет избранных локаций.")
        return

    # Проверяем, есть ли сохраненные локации
    favorites = []
    for i in range(1, 6):
        name_idx = 1 + (i - 1) * 3
        lat_idx = name_idx + 1
        lon_idx = name_idx + 2

        name = user_data[name_idx]
        if name:
            lat = user_data[lat_idx]
            lon = user_data[lon_idx]
            favorites.append((i, name, lat, lon))

    if not favorites:
        bot.send_message(message.chat.id, "У вас нет избранных локаций.")
        return

    # Показываем список для удаления с кнопками
    response = "🗑️ Выберите локацию для удаления:\n\n"

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

    for slot_num, name, lat, lon in favorites:
        response += f"{slot_num}. {name}\n"
        # Добавляем кнопку для удаления
        markup.add(telebot.types.KeyboardButton(f"🗑️ Удалить {slot_num}. {name}"))

    markup.add(telebot.types.KeyboardButton("❌ Отмена удаления"))

    bot.send_message(message.chat.id, response, reply_markup=markup)


# ========== ОБРАБОТКА ВЫБОРА ИЗБРАННОЙ ЛОКАЦИИ ==========

@bot.message_handler(func=lambda message: message.text and message.text.startswith("📍 "))
def handle_favorite_selection(message):
    """Обработать выбор избранной локации"""
    user_id = message.from_user.id

    if message.text == "❌ Отмена":
        bot.send_message(message.chat.id, "Отменено.",
                         reply_markup=telebot.types.ReplyKeyboardRemove())
        return

    # Извлекаем номер из текста "📍 1. Дом"
    try:
        match = re.search(r'(\d+)', message.text)
        if match:
            slot_num = int(match.group(1))
        else:
            bot.send_message(message.chat.id, "Ошибка выбора")
            return
    except:
        bot.send_message(message.chat.id, "Ошибка выбора")
        return

    # Получаем данные из БД
    baza = sqlite3.connect("bazadannih.sql")
    cursor = baza.cursor()

    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user_data = cursor.fetchone()

    baza.close()

    if not user_data:
        bot.send_message(message.chat.id, "Локация не найдена")
        return

    name_idx = 1 + (slot_num - 1) * 3
    lat_idx = name_idx + 1
    lon_idx = name_idx + 2

    name = user_data[name_idx]
    if not name:
        bot.send_message(message.chat.id, f"Слот {slot_num} пуст")
        return

    lat = user_data[lat_idx]
    lon = user_data[lon_idx]

    # Сохраняем как последние координаты (чтобы можно было снова сохранить)
    last_coordinates[user_id] = (lat, lon)

    # Убираем клавиатуру
    bot.send_message(message.chat.id, f"Выбрано: {name}",
                     reply_markup=telebot.types.ReplyKeyboardRemove())

    # Показываем погоду
    obrab_location(lat, lon, message.chat.id)


# ========== ОБРАБОТКА УДАЛЕНИЯ ЛОКАЦИИ ==========

@bot.message_handler(func=lambda message: message.text and message.text.startswith("🗑️ Удалить "))
def handle_delete_favorite(message):
    """Обработать удаление избранной локации"""
    user_id = message.from_user.id

    if message.text == "❌ Отмена удаления":
        bot.send_message(message.chat.id, "Удаление отменено.",
                         reply_markup=telebot.types.ReplyKeyboardRemove())
        return

    # Извлекаем номер из текста "🗑️ Удалить 1. Дом"
    try:
        match = re.search(r'Удалить (\d+)', message.text)
        if match:
            slot_num = int(match.group(1))
        else:
            bot.send_message(message.chat.id, "Ошибка удаления")
            return
    except:
        bot.send_message(message.chat.id, "Ошибка удаления")
        return

    # Получаем название перед удалением
    baza = sqlite3.connect("bazadannih.sql")
    cursor = baza.cursor()

    # Получаем название локации
    cursor.execute(f"SELECT name{slot_num} FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()

    if not result or result[0] is None:
        bot.send_message(message.chat.id, f"Слот {slot_num} уже пуст",
                         reply_markup=telebot.types.ReplyKeyboardRemove())
        baza.close()
        return

    name = result[0]

    # Удаляем локацию (очищаем слот)
    cursor.execute(f"""
        UPDATE users 
        SET name{slot_num} = NULL, lat{slot_num} = NULL, lon{slot_num} = NULL 
        WHERE id = ?
    """, (user_id,))

    baza.commit()
    baza.close()

    bot.send_message(message.chat.id,
                     f"✅ Локация '{name}' удалена из избранного",
                     reply_markup=telebot.types.ReplyKeyboardRemove())


@bot.message_handler(commands=['help'])
def otvet_help(message):
    bot.send_message(message.chat.id, help_message)


# ========== ОБРАБОТЧИКИ ЛОКАЦИЙ ==========

@bot.message_handler(content_types=['location'])
def otvet_location(message):
    lat = float(message.location.latitude)
    lon = float(message.location.longitude)
    message_id = message.chat.id

    # Сохраняем как последние координаты
    last_coordinates[message.from_user.id] = (lat, lon)

    obrab_location(lat, lon, message_id)


@bot.message_handler(content_types=['venue'])
def handle_venue(message):
    lat = float(message.venue.location.latitude)
    lon = float(message.venue.location.longitude)
    message_id = message.chat.id

    # Сохраняем как последние координаты
    last_coordinates[message.from_user.id] = (lat, lon)

    obrab_location(lat, lon, message_id)


@bot.message_handler(content_types=['photo', 'video', 'audio', 'contact', 'document', 'voice', 'animation'])
def otvet_notlocation(message):
    bot.reply_to(message, "Бот может обработать только локацию")


@bot.message_handler()
def otvet_notcommand(message):
    bot.reply_to(message, "Команда не найдена.\n/help - список доступных команд")


def obrab_location(lat: float, lon: float, message_id: int):
    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "relative_humidity_2m,wind_speed_10m,wind_direction_10m,wind_gusts_10m",
        "timezone": "auto",
    }
    response = requests.get(url, params=params, timeout=15)
    weather_data = response.json()["current"]

    humidity = weather_data.get('relative_humidity_2m', 'Нет данных')
    wind_speed = weather_data.get('wind_speed_10m', 'Нет данных')
    wind_dir = weather_data.get('wind_direction_10m', 'Нет данных')
    wind_gust = weather_data.get('wind_gusts_10m', 'Нет данных')

    wind_data = f"""
    Широта: {lat}
Долгота: {lon}

Ветер:
    Скорость: {wind_speed} м/с
    Направление: {wind_dir}°
    Порывы: {wind_gust} м/с

Влажность: {humidity}%
"""
    bot.send_message(message_id, wind_data)


bot.polling(none_stop=True)
