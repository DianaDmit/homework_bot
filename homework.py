import logging
import os
import requests
import sys
import time as t
import time

from dotenv import load_dotenv
from http import HTTPStatus
from telegram import Bot
from exceptions import (ApiJsonErorr, ApiNotAvailable)

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN_ENV')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN_ENV')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID_ENV')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, %(levelname)s, %(message)s'
)

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)


def send_message(bot, message):
    """Отправка сообщения в Телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception('Телеграм сервис недоступен'):
        logger.error('Телеграм сервис недоступен')
    else:
        logger.info('Сообщение для sat0304_bot отправлено')


def get_api_answer(current_timestamp):
    """Получение ответа API Практикум.Домашка."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except Exception as error:
        raise ApiNotAvailable(
            'Общая ошибка API.'
        ) from error
    if response.status_code != HTTPStatus.OK:
        raise ApiNotAvailable(
            f'Код ответа API: {response.status_code}'
        )
    logger.debug(
        f'API практикума доступно. Код: {response.status_code}'
    )
    try:
        return response.json()
    except Exception as error:
        raise ApiJsonErorr(f'Ошибка преобразования json {error}')


def check_response(response):
    """Проверка ответа API сайта Практикум.Домашка."""
    try:
        if type(response) == dict:
            cur_date = response['current_date']
            logger.info(f'Дата проверки API Практикум.Домашка {cur_date}')
            homeworks = response['homeworks']
    except TypeError('Получен неправильный результат'):
        logger.error('Получен неправильный результат')
    else:
        try:
            if type(homeworks) == list:
                logger.info('Получен список от API Практикум.Домашка')
                return homeworks
        except TypeError('Получен пустой список'):
            logger.error('Получен пустой список от API Практикум.Домашка')
    return []


def parse_status(homework):
    """Извлечение данных из ответа API сайта Практикум.Домашка."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        logger.error(f'Нет значения {homework_name}')
    if homework_status is None:
        logger.error(f'Нет значения {homework_status}')
    if homework_status in HOMEWORK_STATUSES:
        verdict = HOMEWORK_STATUSES[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    raise KeyError('Неверное значение статуса')


def check_tokens():
    """Проверяем доступность переменных окружения."""
    TOKEN_DICT = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    token_error = ('Отсутствует переменная окружения: ')
    result = True
    for token, value in TOKEN_DICT.items():
        if value is None:
            result = False
            logger.critical(f'{token_error}{token}')
    return result


def main():
    """Основная логика работы бота."""
    old_error = '1'
    if check_tokens():
        bot = Bot(token=TELEGRAM_TOKEN)
        current_timestamp = int(t.time()) - RETRY_TIME
        old_homework = None
    else:
        sys.exit(1)
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date')
            homework = check_response(response)
            if len(homework) > 0:
                homework_1 = parse_status(homework[0])
                if homework_1 != old_homework:
                    logger.info(
                        f'Изменился статус проверки работы {homework_1}'
                    )
                    old_homework = homework_1
                    send_message(bot, f'{homework_1}')
            t.sleep(RETRY_TIME)
        except Exception as error:
            logger.error(f'Сбой в работе программы: {error}')
            if error != old_error:
                old_error = error
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                t.sleep(RETRY_TIME)
        else:
            logger.debug('Ошибок нет: бот работает')
            logger.debug(f'Прежняя информация: {old_homework}')


if __name__ == '__main__':
    main()
