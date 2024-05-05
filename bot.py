import os
import telebot
import logging
import psycopg2
from flask import Flask, request
from uuid import uuid4

BOT_TOKEN = os.getenv('BOT_TOKEN')
APP_URL = os.getenv('APP_URL') + BOT_TOKEN
DB_URI = os.getenv('DB_URI')

bot = telebot.TeleBot(BOT_TOKEN)
server = Flask(__name__)
logger = telebot.logger
logger.setLevel(logging.DEBUG)

db_connection = psycopg2.connect(DB_URI, sslmode="require")
db_object = db_connection.cursor()


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id,
                     'Привет! Я бот для управления задачами. Используй '
                     'команду /add чтобы добавить новую задачу или /tsk для '
                     'вывода всех задач.')


@bot.message_handler(commands=["tsk"])
def get_tasks(message):
    user_id = message.from_user.id
    db_object.execute(f"SELECT * FROM task"
                      f" WHERE user_id={user_id} ORDER BY message")
    tasks = db_object.fetchall()
    if tasks:
        task_list = "\n\n".join(
            [f"{index + 1}. {task[0]}" for index, task in enumerate(tasks)])
        bot.send_message(message.chat.id, f"Список задач:\n\n{task_list}")
    else:
        bot.send_message(message.chat.id, "Список задач пуст.")


@bot.message_handler(commands=["add"])
def create_task(message):
    bot.send_message(message.chat.id, 'Введите новую задачу')
    bot.register_next_step_handler(message, new_task)


def new_task(message):
    user_id = message.from_user.id
    task_id = uuid4()
    db_object.execute(
        "INSERT INTO task(id, user_id, message) "
        "VALUES (%s, %s, %s)",
        (task_id, user_id, message.text))
    db_connection.commit()
    bot.send_message(message.chat.id,
                     'Задача успешно добавлена:\n' + message.text)


@server.route(f"/{BOT_TOKEN}", methods=["POST"])
def redirect_message():
    json_string = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200


if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=APP_URL)
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
