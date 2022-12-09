import http
import logging
import os
import sys
import time
from json.decoder import JSONDecodeError

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
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
    except requests.RequestException as error:
        logging.error(f'Ошибка подключения к API: {error},'
                      f' exc_info=True')
        raise ConnectionError(f'Ошибка подключения к API: {error},'
                              f' exc_info=True')

    if response.status_code != http.HTTPStatus.OK:
        logging.error(WrongApiResponseCodeError(response),
                      exc_info=True)
        raise WrongApiResponseCodeError(response)
    try:
        response = response.json()
    except JSONDecodeError as error:
        logging.error(f'Ошибка преобразования из JSON: {error}',
                      exc_info=True)
        raise JSONDecodeError(f'Ошибка преобразования из JSON: {error}')
    return response


def check_response(response: dict) -> dict:
    """Проверка ответа API."""
    if not isinstance(response, dict):
        raise TypeError('В функцию "check_response" поступил не словарь')
    if 'homeworks' not in response or 'current_date' not in response:
        raise KeyError('в запросе нет ключа с домашками')
    if not isinstance(response['homeworks'], list):
        raise TypeError('в значаниях словаря не список')


def parse_status(homework: dict) -> str:
    """Информации о конкретном статусе домашней работы."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if not homework_name:
        raise KeyError('У домашней работы отсутствует ключ homework_name')
    if not homework_status:
        raise EmptyAPIResponseError('Неизвестный статус работы')
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    if not verdict:
        raise EmptyAPIResponseError(f'Неожиданный статус домашней работы:,'
                                    f'{homework_status}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


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
            if not response.get('homeworks'):
                continue
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
            send_message(bot, message)
            logger.error(message, exc_info=error)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
