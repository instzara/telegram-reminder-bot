import telebot
from telebot import types
import threading
import time
from datetime import datetime, timedelta

API_TOKEN = '7681576222:AAHyEhQBqKQzutLFgUO8XFabsBtrloX_4uU'
bot = telebot.TeleBot(API_TOKEN)

user_data = {}

def reminder_job(chat_id, medicine, reminder_time, frequency, day_of_week):
    try:
        now = datetime.now()
        days_of_week = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        day_index = days_of_week.index(day_of_week)
        next_day = now + timedelta(days=(day_index - now.weekday()) % 7)
        reminder_datetime = datetime.strptime(reminder_time, "%H:%M").replace(year=next_day.year, month=next_day.month, day=next_day.day)

        if reminder_datetime < now:
            reminder_datetime += timedelta(weeks=1)

        delay = (reminder_datetime - now).total_seconds()
        time.sleep(delay)

        bot.send_message(chat_id, f"Вы приняли {medicine}?", reply_markup=reminder_keyboard())

        if frequency == "Каждый день":
            next_day = reminder_datetime + timedelta(days=1)
        elif frequency == "Через день":
            next_day = reminder_datetime + timedelta(days=2)
        else:
            return

        threading.Thread(target=reminder_job, args=(chat_id, medicine, reminder_time, frequency, day_of_week)).start()

    except Exception as e:
        print(f"Ошибка в reminder_job: {e}")

def reminder_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Да", "Нет")
    return keyboard

@bot.message_handler(commands=['start'])
def cmd_start(message):
    bot.send_message(message.chat.id, "Привет! Я бот для напоминания о приеме лекарств. Какое лекарство вы хотите добавить?")
    bot.register_next_step_handler(message, process_medicine)

def process_medicine(message):
    medicine_name = message.text.strip()
    if not medicine_name:
        bot.send_message(message.chat.id, "Название лекарства не может быть пустым. Пожалуйста, введите название.")
        bot.register_next_step_handler(message, process_medicine)
        return

    user_data[message.chat.id] = {'medicine': medicine_name}
    bot.send_message(message.chat.id, "Выберите день недели:", reply_markup=days_keyboard())
    bot.register_next_step_handler(message, process_day)

def days_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    for day in days:
        date = (datetime.now() + timedelta(days=(days.index(day) - datetime.now().weekday()) % 7)).strftime("%d.%m")
        keyboard.add(f"{day} ({date})")
    return keyboard

def process_day(message):
    day = message.text.strip()
    if not any(day.startswith(d) for d in ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]):
        bot.send_message(message.chat.id, "Пожалуйста, выберите корректный день недели.")
        bot.register_next_step_handler(message, process_day)
        return

    user_data[message.chat.id]['day'] = day.split(' ')[0]
    bot.send_message(message.chat.id, "Введите время приема лекарства (например, 09:00):")
    bot.register_next_step_handler(message, process_time)

def process_time(message):
    time_input = message.text.strip()
    if not validate_time(time_input):
        bot.send_message(message.chat.id, "Некорректное время. Пожалуйста, введите время от 00:00 до 23:59.")
        bot.register_next_step_handler(message, process_time)
        return

    user_data[message.chat.id]['time'] = time_input
    bot.send_message(message.chat.id, "Как часто вы хотите принимать это лекарство?", reply_markup=periodicity_keyboard())
    bot.register_next_step_handler(message, process_periodicity)

def periodicity_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Каждый день", "Через день", "Единовременно")
    return keyboard

def process_periodicity(message):
    frequency = message.text.strip()
    if frequency not in ["Каждый день", "Через день", "Единовременно"]:
        bot.send_message(message.chat.id, "Пожалуйста, выберите корректную периодичность.")
        bot.register_next_step_handler(message, process_periodicity)
        return

    user_data[message.chat.id]['periodicity'] = frequency
    confirmation_text = (
        f"Вы указали:\n"
        f"Лекарство: {user_data[message.chat.id]['medicine']}\n"
        f"День приема: {user_data[message.chat.id]['day']}\n"
        f"Время приема: {user_data[message.chat.id]['time']}\n"
        f"Периодичность: {user_data[message.chat.id]['periodicity']}\n\n"
        f"Все верно?"
    )

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Верно", "Неверно")
    bot.send_message(message.chat.id, confirmation_text, reply_markup=keyboard)
    bot.register_next_step_handler(message, confirm_details)

def validate_time(time_str):
    try:
        time_obj = datetime.strptime(time_str, "%H:%M")
        return 0 <= time_obj.hour < 24 and 0 <= time_obj.minute < 60
    except ValueError:
        return False

def confirm_details(message):
    if message.text == "Верно":
        chat_id = message.chat.id
        medicine = user_data[chat_id]['medicine']
        time_to_remind = user_data[chat_id]['time']
        frequency = user_data[chat_id]['periodicity']
        day_of_week = user_data[chat_id]['day']
        threading.Thread(target=reminder_job, args=(chat_id, medicine, time_to_remind, frequency, day_of_week)).start()
        bot.send_message(chat_id, "Спасибо! Я буду напоминать вам о приеме лекарства.", reply_markup=types.ReplyKeyboardRemove())
        bot.send_message(chat_id, "Если хотите добавить новое, используйте команду /addmed.")

    elif message.text == "Неверно":
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add("Изменить лекарство", "Изменить время", "Изменить день недели")
        bot.send_message(message.chat.id, "Что хотите изменить?", reply_markup=keyboard)
        bot.register_next_step_handler(message, change_data)

def change_data(message):
    if message.text == "Изменить лекарство":
        bot.send_message(message.chat.id, "Какое новое лекарство вы хотите добавить?")
        bot.register_next_step_handler(message, process_medicine)
    elif message.text == "Изменить время":
        bot.send_message(message.chat.id, "Введите новое время приема лекарства (например, 09:00):")
        bot.register_next_step_handler(message, process_time)
    elif message.text == "Изменить день недели":
        bot.send_message(message.chat.id, "Выберите новый день недели:", reply_markup=days_keyboard())
        bot.register_next_step_handler(message, process_day)

@bot.message_handler(commands=['addmed'])
def add_medication_command(message):
    bot.send_message(message.chat.id, "Какое лекарство хотите добавить?")
    bot.register_next_step_handler(message, process_medicine)

@bot.message_handler(func=lambda message: message.text in ["Да", "Нет"])
def process_reminder_response(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        bot.send_message(chat_id, "Пожалуйста, сначала добавьте лекарство через /addmed")
        return
    if message.text == "Да":
        praise_user(chat_id)
    elif message.text == "Нет":
        send_reminder(chat_id)

def praise_user(chat_id):
    bot.send_message(chat_id, "Отлично! Вы молодец! Если хотите добавить новое лекарство позже, используйте команду /addmed.")

def send_reminder(chat_id):
    medicine = user_data.get(chat_id, {}).get('medicine', 'лекарство')
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Я принял лекарство")
    bot.send_message(chat_id, f"Не забудьте принять {medicine}. После этого нажмите 'Я принял лекарство'.", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Я принял лекарство")
def handle_accepted_medicine(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        bot.send_message(chat_id, "Пожалуйста, сначала добавьте лекарство через /addmed")
        return
    praise_user(chat_id)

if __name__ == '__main__':
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Ошибка в polling: {e}")
