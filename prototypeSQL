import telebot
import requests
import sqlite3
import re

bot = telebot.TeleBot(".............................")

help_message = """
/wind - пришлите координаты и узнайте информацию о ветре
/favorite быстрый доступ к избранным локациям
/settings настройки"""

start_message = """
/wind - пришлите координаты и узнайте информацию о ветре
/favorite быстрый доступ к избранным локациям
/settings настройки
/help список команд
"""

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
    #bot.send_message(message.chat.id, f"{message.from_user.last_name}")
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
        obrab_location(lat, lon, message_id)

def is_coord(text):
    pattern = r'^[\s]*[-+]?\d+\.?\d*[\s,;]+[-+]?\d+\.?\d*[\s]*$'
    return bool(re.match(pattern, text.strip()))

def parse_coord(text):
    numbers = re.findall(r'[-+]?\d+\.?\d*', text)
    return float(numbers[0]), float(numbers[1])


@bot.message_handler(commands=['favorite'])
def otvet_favorite(message):
    bot.send_message(message.chat.id, "В разработке")

@bot.message_handler(commands=['settings'])
def otvet_settings(message):
    bot.send_message(message.chat.id, "Guess what? В разработке")

@bot.message_handler(commands=['help'])
def otvet_help(message):
    bot.send_message(message.chat.id, help_message)


@bot.message_handler(content_types=['location'])
def otvet_location(message):
    lat = float(message.location.latitude)
    lon = float(message.location.longitude)
    message_id = message.chat.id
    obrab_location(lat, lon, message_id)


@bot.message_handler(content_types=['venue'])
def handle_venue(message):
    lat = float(message.venue.location.latitude)
    lon = float(message.venue.location.longitude)
    message_id = message.chat.id

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
