'''
Serveless function for telegram bot
'''

import os
import logging
import random
import base64
import json
import io
import asyncio
import requests
import telebot
import telebot.async_telebot


API_TOKEN = os.environ['TELEGRAM_TOKEN']
API_SECRET = os.environ['TELEGRAM_SECRET']

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)
bot = telebot.async_telebot.AsyncTeleBot(API_TOKEN)
FOLDER_ID = None
AIM_HEADER = None
LOGGER_INTERFACE = None


def logging_configuration(logger_object):
    logger_object.setLevel(logging.DEBUG)
    sh_formatter = logging.Formatter(fmt='%(asctime)s %(process)d %(name)s %(levelname)s %(funcName)s %(message)s',
                                     datefmt='%d-%b-%y %H:%M:%S')
    sh = logging.StreamHandler()
    sh.setLevel(level=logging.INFO)
    sh.setFormatter(sh_formatter)

    logger_object.addHandler(sh)


def get_folder_id(iam_token, function_id):
    global AIM_HEADER, FOLDER_ID
    AIM_HEADER = {'Authorization': f'Bearer {iam_token}'}
    # function_id_req = requests.get(f'https://serverless-functions.api.cloud.yandex.net/functions/v1/versions/{version_id}',
    #                                headers=AIM_HEADER)
    # function_id_data = function_id_req.json()
    # function_id = function_id_data['functionId']
    FOLDER_ID_req = requests.get(f'https://serverless-functions.api.cloud.yandex.net/functions/v1/functions/{function_id}',
                                 headers=AIM_HEADER)
    FOLDER_ID_data = FOLDER_ID_req.json()
    FOLDER_ID = FOLDER_ID_data['folderId']
    return FOLDER_ID

async def handler(event, context):
    if event['headers'].get('X-Telegram-Bot-Api-Secret-Token') != API_SECRET:
        logging.warning('Suspicious reauest: %s', event)
        return {
            'statusCode': 401
        }

    global LOGGER_INTERFACE
    LOGGER_INTERFACE = logging.getLogger('bot')
    logging_configuration(LOGGER_INTERFACE)
    iam_token = context.token["access_token"]
    function_id = context.function_name
    FOLDER_ID = get_folder_id(iam_token, function_id)
    try:
        message = telebot.types.Update.de_json(event['body'])
        LOGGER_INTERFACE.info('\rMessage text: %s,\rSender: %s', message.message.text, message.message.from_user.username)
        await bot.process_new_updates([message])
    except Exception as e:
        LOGGER_INTERFACE.warning(event)
        LOGGER_INTERFACE.error('Telebot problem: %s', e)
    return {
        'statusCode': 200
    }


@bot.message_handler(commands=['start',])
async def start_message(message):
    message_text = "Во славу императора!"
    await bot.reply_to(message, message_text)


@bot.message_handler(commands=['genimage',])
async def yandex_art(message):
    prompt = {
        "modelUri": f"art://{FOLDER_ID}/yandex-art/latest",
        "generationOptions": {
            "seed": random.randint(0, 2**62),
            "aspectRatio": {
                "widthRatio": "2",
                "heightRatio": "1",
            }
        },
        "messages": [
            {
                "weight": "1",
                "text": message.text.replace('/genimage ', '')
            }
        ]
    }

    result = requests.post('https://llm.api.cloud.yandex.net/foundationModels/v1/imageGenerationAsync', data=json.dumps(prompt), headers=AIM_HEADER)
    if result.status_code != 200:
        LOGGER_INTERFACE.error(result.text)
        await bot.reply_to(message, "Не могу сгенерировать изображение")
        return None
    result = result.json()
    while True:
        result = requests.get('https://llm.api.cloud.yandex.net:443/operations/' + result['id'], headers=AIM_HEADER)
        result = result.json()
        LOGGER_INTERFACE.info('Image was ready: %s', result['done'])
        await bot.reply_to(message, "Шедевр рисуется.", disable_notification=True)
        if result['done']:
            encoded = result['response']['image']
            data = base64.b64decode(encoded)
            await bot.send_photo(message.chat.id, telebot.types.InputFile(io.BytesIO(data)), reply_parameters=telebot.types.ReplyParameters(message.message_id, message.chat.id, allow_sending_without_reply=True))
            break

        await asyncio.sleep(10)


@bot.message_handler(commands=['assystent',])
async def yandex_gpt(message):
    prompt = {
        "modelUri": f"gpt://{FOLDER_ID}/yandexgpt-lite/latest",
        "completionOptions": {
            "stream": False,
            "temperature": 0.6,
            "maxTokens": "2000"
        },
        "messages": [
            {
            "role": "system",
            "text": "Представь что ты из вселенной Warhammer 4000 и отвечай в подобном стиле"
            },
            {
            "role": "user",
            "text": message.text.replace('/assystent ', '')
            }
        ]
    }
    AIM_HEADER.update(
        {
            'x-folder-id': FOLDER_ID,
            'Content-Type': 'application/json'
        }
    )

    result = requests.post('https://llm.api.cloud.yandex.net/foundationModels/v1/completion', data=json.dumps(prompt), headers=AIM_HEADER)
    if result.status_code != 200:
        LOGGER_INTERFACE.error(result.text)
        await bot.reply_to(message, "Не могу сгенерировать текст")
        return None
    result = result.json()
    for alternatives in result['result']['alternatives']:
        await bot.reply_to(message, alternatives['message']['text'])
