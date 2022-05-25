import logging
import os
import requests
import sys
import time as t

from dotenv import load_dotenv
from http import HTTPStatus
from json.decoder import JSONDecodeError
from telegram import Bot
from requests.exceptions import ConnectionError, ConnectTimeout
from requests.exceptions import HTTPError, ReadTimeout, Timeout

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
    resp = []
    timestamp = current_timestamp
    # try:
    #    t.time(timestamp)
    # except Exception('Неправильный формат времени'):
    #    logger.error('Неправильный формат времени')
    # else:
    params = {'from_date': timestamp}
    try:
        params['from_date'] == current_timestamp
        response = requests.get(url=ENDPOINT, headers=HEADERS, params=params)
        if response.status_code == HTTPStatus.OK:
            resp = response.json()
        else:
            raise SystemError(
                f'Недоступен API Практикум.Домашка {response.status_code}'
            )
    except ConnectTimeout:
        logger.error('Connect Timeout')
    except ConnectionError:
        logger.error('Connection Error')
    except ReadTimeout:
        logger.error('Read Timeout')
    except Timeout:
        logger.error('Timeout')
    except HTTPError:
        logger.error('HTTP Error')
    except JSONDecodeError:
        logger.error('JSON Decode Error')
    else:
        logger.info('Сайт API Практикум.Домашка доступен')
        return resp


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
        else:
            return []


def parse_status(homework):
    """Извлечение данных из ответа API сайта Практикум.Домашка."""
    if homework['id'] == 0:
        logger.error('Работа на проверку не загружена')
        return KeyError('Пустой список работ')
    else:
        homework_name_1 = homework.get('homework_name')
        if homework_name_1 is None:
            logger.error('Нет данных о работе')
            return KeyError('Нет данных о работе')
        else:
            homework_status = homework.get('status')
            if homework_status is None:
                logger.error('Статус работы - пустой')
                return KeyError('Статс работы неизвестен')
            else:
                homework_status = homework.get('status')
                if homework_status in HOMEWORK_STATUSES:
                    verdict = HOMEWORK_STATUSES.get(homework_status)
                    text = 'Изменился статус проверки работы '
                    logger.info(f'{text}"{homework_name_1}": {verdict}')
                    return (f'{text}"{homework_name_1}": {verdict}')


def check_tokens():
    """Проверяем доступность переменных окружения."""
    TOKEN_DICT = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    token_error = ('Отсутствует переменная окружения: ')
    result = None
    for token in TOKEN_DICT.keys():
        if (TOKEN_DICT[token] is None):
            logger.critical(f'{token_error}{token}')
            result = False
        else:
            result = True
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
