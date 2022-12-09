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
from telegram import Bot

from exceptions import (
    ConnectionError, EmptyAPIResponseError,
    WrongApiResponseCodeError, NotForTelegramError,
)

load_dotenv()


logging.basicConfig(
    level=logging.DEBUG,
    handlers=[logging.FileHandler(
    filename='main.log',
    mode='w')],
    format='%(asctime)s, %(levelname)s, %(message)s',
)

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
handler = RotatingFileHandler(
    'Bot.log',
    maxBytes=50000000,
    backupCount=5,
    encoding='utf-8',
)


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


def check_tokens() -> bool:
    """Проверка доступности переменных окружения."""
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot: Bot, message: str) -> None:
    """Отправка сообщений в Telegram чат."""
    logger.info('Попытка отправки сообщения')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError:
        logging.error('Ошибка отправки сообщения в Telegram')
    else:
        logging.debug(f'Сообщение успешно отправленно: {message}')


def get_api_answer(current_timestamp: int) -> dict:
    """Запрос к эндпоинту API-сервиса."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params=params)
        if response.status_code != http.HTTPStatus.OK:
            raise WrongApiResponseCodeError(f'Ошибка {response.status_code}')
        return response.json()
    except requests.exceptions.ConnectionError:
        raise ConnectionError('Ошибка подключения')
    except requests.RequestException as request_error:
        raise Exception(f'Ошибка запроса {request_error}')
    except JSONDecodeError:
        raise Exception('JSON не сформирован')


def check_response(response: dict) -> dict:
    """Проверка ответа API."""
    if not isinstance(response, dict):
        raise TypeError('В функцию "check_response" поступил не словарь')
    if not response.get('homeworks'):
        raise KeyError("в запросе нет ключа с домашками")
    if not isinstance(response['homeworks'], list):
        raise TypeError("в значаниях словаря не список")
    if response.get('homeworks'):
        return response


def parse_status(homework: dict) -> str:
    """Информации о конкретном статусе домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if not homework_name:
        raise KeyError('У домашней работы отсутствует ключ homework_name')
    if not homework_status:
        raise EmptyAPIResponseError(f'Неизвестный статус работы:'
                                    f' {homework_status}')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if not verdict:
        raise EmptyAPIResponseError(f'Неожиданный статус домашней работы:,'
                                    f'{homework_status}')
    return f'Изменился статус проверки работы "{homework_name}".' \
           f'{verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Проблема с токенами!!!')
        sys.exit(0)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            timestamp = response.get('current_date')
            homeworks = response.get('homeworks')
            if homeworks:
                homework = homeworks[0]
                message = parse_status(homework)
                send_message(bot, message)
                logging.debug('Сообщение о новом статусе было отправлено')
            else:
                logger.debug('Новых статусов нет')
        except NotForTelegramError as err:
            logging.error(f'Что то сломалось при отправке, {err}',
                          exc_info=True)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message, exc_info=True)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
