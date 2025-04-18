from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from logic import *
import schedule
import threading
import time
from config import *
import os

# Создание необходимых директорий
os.makedirs('img', exist_ok=True)
os.makedirs('hidden_img', exist_ok=True)

bot = TeleBot(API_TOKEN)
manager = DatabaseManager(DATABASE)
manager.create_tables()

# Кнопка "Получить!"
def gen_markup(id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton("Получить!", callback_data=str(id)))
    return markup

# Обработка нажатия кнопки "Получить!"
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        prize_id = int(call.data)
        user_id = call.message.chat.id

        # Проверка, не получал ли пользователь этот приз
        if manager.add_winner(user_id, prize_id):
            img = manager.get_prize_img(prize_id)
            if img:
                with open(f'img/{img}', 'rb') as photo:
                    bot.send_photo(user_id, photo, caption="Поздравляем! Ты успел первым 🎉")
            else:
                bot.send_message(user_id, "Изображение не найдено.")
        else:
            bot.send_message(user_id, "Увы! Приз уже забрали.")
    except Exception as e:
        print(f"Ошибка в callback_query: {e}")
        bot.send_message(call.message.chat.id, "Произошла ошибка при обработке.")

# Рассылка спрятанных призов
def send_message():
    prize = manager.get_random_prize()
    if not prize:
        print("Нет доступных призов.")
        return

    prize_id, img = prize[:2]
    manager.mark_prize_used(prize_id)
    hide_img(img)

    winners_sent = 0
    for user in manager.get_users():
        if winners_sent >= 3:
            break
        try:
            with open(f'hidden_img/{img}', 'rb') as photo:
                bot.send_photo(user, photo, reply_markup=gen_markup(prize_id))
                winners_sent += 1
        except Exception as e:
            print(f"Ошибка при отправке пользователю {user}: {e}")

# Поток для расписания
def schedule_thread():
    schedule.every().second.do(send_message)  # Меняй на every().second для теста
    while True:
        schedule.run_pending()
        time.sleep(1)

# Обработка команды /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    if user_id in manager.get_users():
        bot.reply_to(message, "Ты уже зарегистрирован!")
    else:
        manager.add_user(user_id, message.from_user.username)
        bot.reply_to(message, """Привет! Добро пожаловать! 
Ты успешно зарегистрирован!
Каждый час тебе будут приходить новые картинки и у тебя будет шанс их получить!
Для этого нужно быстрее всех нажать на кнопку 'Получить!'

Только три первых пользователя получат картинку!""")

# Поток бота
def polling_thread():
    bot.polling(none_stop=True)

# Запуск
if __name__ == '__main__':
    polling_thread = threading.Thread(target=polling_thread)
    polling_schedule = threading.Thread(target=schedule_thread)

    polling_thread.start()
    polling_schedule.start()