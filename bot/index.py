import telebot
import os
import logging


API_TOKEN = os.environ['TELEGRAM_TOKEN']

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)
bot = telebot.TeleBot(API_TOKEN, threaded=False)


def handler(event, context):
    message = telebot.types.Update.de_json(event['body'])
    bot.process_new_updates([message])
    return {
        'statusCode': 200
    }


@bot.message_handler(commands=['start',])
def start_message(message):
    message_text = "Во славу императора!"
    bot.reply_to(message, message_text)
