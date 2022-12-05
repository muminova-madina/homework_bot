import http
import logging
import os
import sys
import time
from json.decoder import JSONDecodeError
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600

ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступности переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправка сообщений в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение успешно отправленно: {message}')
    except Exception as error:
        logging.error(f'Ошибка отправки сообщения в Telegram - {error}')
        raise Exception(f'Ошибка при отправке сообщения-статус: {error}')


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    current_timestamp = timestamp
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params=params)
        if response.status_code != http.HTTPStatus.OK:
            logger.error('Страница недоступна')
            raise requests.exceptions.HTTPError()
        return response.json()
    except requests.exceptions.ConnectionError:
        logger.error('Ошибка подключения')
    except requests.exceptions.RequestException as request_error:
        logger.error(f'Ошибка запроса {request_error}')
    except JSONDecodeError:
        logger.error('JSON не сформирован')


def check_response(response):
    """Проверка ответа API."""
    if type(response) is not dict:
        raise TypeError('В функцию "check_response" поступил не словарь')
    if 'homeworks' not in response:
        raise KeyError('Ключ homeworks отсутствует')
    if type(response['homeworks']) is not list:
        raise TypeError('Объект homeworks не является списком')
    if response['homeworks'] == []:
        return {}
    return response.get('homeworks')[0]


def parse_status(homework):
    """Информации о конкретном статусе домашней работы."""
    if 'status' not in homework or type(homework) is str:
        logger.error('Ключ status отсутствует в homework')
        raise KeyError('Ключ status отсутствует в homework')
    if 'homework_name' not in homework:
        raise KeyError('Ключ homework_name отсутствует в homework')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS.keys():
        raise ValueError('Значение не соответствует справочнику статусов')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Проблема с токенами!!!')
        sys.exit(0)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework)
                send_message(bot, message)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.error(message)
        time.sleep(RETRY_PERIOD)
        timestamp = int(time.time() - RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        handlers=[logging.FileHandler(
        filename="main.log",
        mode='w')],
        format='%(asctime)s, %(levelname)s, %(message)s',
        level=logging.DEBUG,
    )

    logger = logging.getLogger(__name__)
    logger.addHandler(logging.StreamHandler())
    handler = RotatingFileHandler(
        'Bot.log',
        maxBytes=50000000,
        backupCount=5,
        encoding='utf-8',
    )

    main()
