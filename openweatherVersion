#все работает но без впна получить json файл не получится поэтому надо бота развертывать где-то на удаленном сервере 
№это бесплатно но все равно пока что не, оставляю эту версию иду работать с другими погодными сервисами



import telebot
import requests

bot = telebot.TeleBot("........................")

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
    bot.send_message(message.chat.id, f"{message.from_user.last_name}")

@bot.message_handler(commands=['wind'])
def otvet_wind(message):
    bot.send_message(message.chat.id, "Пришли свои координаты пж")

@bot.message_handler(commands=['favorite'])
def otvet_favorite(message):
    bot.send_message(message.chat.id, "IFAVORIIIITE")

@bot.message_handler(commands=['settings'])
def otvet_settings(message):
    bot.send_message(message.chat.id, "IM TOO 000000000000LAZY")

@bot.message_handler(commands=['help'])
def otvet_help(message):
    bot.send_message(message.chat.id, help_message)

@bot.message_handler(content_types=['location'])
def otvet_location(message):
    API = ".................."
    lat = float(message.location.latitude)
    lon = float(message.location.longitude)
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={API}&units=metric&lang=ru"

    data = requests.get(url, timeout=40)
    weather_data = data.json()
    wind_data = weather_data.get("wind", {})

    bot.send_message(message.chat.id, wind_data)
