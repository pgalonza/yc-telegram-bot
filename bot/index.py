import telebot
import telebot.async_telebot
import os
import logging
import random
import requests
import base64
import json
import io
import time
import asyncio


API_TOKEN = os.environ['TELEGRAM_TOKEN']

logger = telebot.logger
telebot.logger.setLevel(logging.INFO)
bot = telebot.async_telebot.AsyncTeleBot(API_TOKEN)
folder_id = None
aim_header = None
logger_interface = None


def logging_configuration(logger):
    logger.setLevel(logging.DEBUG)
    sh_formatter = logging.Formatter(fmt='%(asctime)s %(process)d %(name)s %(levelname)s %(funcName)s %(message)s',
                                     datefmt='%d-%b-%y %H:%M:%S')
    sh = logging.StreamHandler()
    sh.setLevel(level=logging.INFO)
    sh.setFormatter(sh_formatter)

    logger.addHandler(sh)


def get_folder_id(iam_token, version_id):
    global aim_header
    headers = {'Authorization': f'Bearer {iam_token}'}
    aim_header = headers
    function_id_req = requests.get(f'https://serverless-functions.api.cloud.yandex.net/functions/v1/versions/{version_id}',
                                   headers=headers)
    function_id_data = function_id_req.json()
    function_id = function_id_data['functionId']
    folder_id_req = requests.get(f'https://serverless-functions.api.cloud.yandex.net/functions/v1/functions/{function_id}',
                                 headers=headers)
    folder_id_data = folder_id_req.json()
    folder_id = folder_id_data['folderId']
    return folder_id

async def handler(event, context):
    global folder_id, logger_interface
    logger_interface = logging.getLogger('bot')
    logging_configuration(logger_interface)
    iam_token = context.token["access_token"]
    version_id = context.function_version
    folder_id = get_folder_id(iam_token, version_id)

    message = telebot.types.Update.de_json(event['body'])
    logger_interface.info('\rMessage text: %s,\rSender: %s', message.message.text, message.message.from_user.username)
    await bot.process_new_updates([message])
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
        "modelUri": f"art://{folder_id}/yandex-art/latest",
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
    result = requests.post('https://llm.api.cloud.yandex.net/foundationModels/v1/imageGenerationAsync', data=json.dumps(prompt), headers=aim_header)
    if result.status_code != 200:
        logger_interface.error(result.text)
        await bot.reply_to(message, "Не могу сгенерировать изображение")
        return None
    result = result.json()
    while True:
        result = requests.get('https://llm.api.cloud.yandex.net:443/operations/' + result['id'], headers=aim_header)
        result = result.json()
        logger_interface.info('Image was ready: %s', result['done'])
        await bot.reply_to(message, "Шедевр рисуется.", disable_notification=True)
        if result['done']:
            encoded = result['response']['image']
            data = base64.b64decode(encoded)
            await bot.send_photo(message.chat.id, telebot.types.InputFile(io.BytesIO(data)), reply_parameters=telebot.types.ReplyParameters(message.message_id, message.chat.id, allow_sending_without_reply=True))
            break

        time.sleep(10)