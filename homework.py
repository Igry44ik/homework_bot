import json
import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PR_TOKEN')
TELEGRAM_TOKEN = os.getenv('TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')
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
    filename='program.log',
    filemode='w',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def send_message(bot, message):
    """Отправляет сообщение в телеграм чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение успешно отправлено')
    except telegram.TelegramError as telegramerror:
        logger.error(
            f'Сообщение не отправлено: {telegramerror}')


def get_api_answer(current_timestamp):
    """Производит запрос к API-сервису."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except requests.exceptions.ConnectTimeout as error:
        logger.error(f'Сервер долго не отвечает. Ошибка: {error}')
        raise error
    except requests.exceptions.ConnectionError as connectionerror:
        logger.error(f'Проблема с сетью. Ошибка: {connectionerror}')
    if response.status_code != HTTPStatus.OK:
        logger.error('API недоступен')
        raise requests.HTTPError(f'API недоступен'
                                 f'Код ответа: {response.status_code}')
    try:
        return response.json()
    except json.JSONDecodeError as jsonerror:
        logger.error(f'Не верный JSON. Ошибка: {jsonerror}')


def check_response(response):
    """Проверяет ответ API на корректность."""
    if response['homeworks'] is None:
        raise TypeError('Отсутствуют данные')
    if type(response['homeworks']) != list:
        raise TypeError(' Домашки приходят не в виде списка')
    if len(response) == 0:
        raise Exception('Словарь пустой')
    if 'homeworks' not in response.keys():
        raise KeyError('Не существуетключа: "homeworks"')
    homeworks = response.get('homeworks')
    return homeworks


def parse_status(homework):
    """Извлекает информацию о статусе конретной сданной работы."""
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
    """Проверяет доступность переменных окружения."""
    tokens = True
    if PRACTICUM_TOKEN is None:
        tokens = False
        logger.critical
        (f'Проверьте доступность переменной окружения {PRACTICUM_TOKEN}')
    if TELEGRAM_TOKEN is None:
        tokens = False
        logger.critical
        (f'Проверьте доступность переменной окружения {TELEGRAM_TOKEN}')
    if TELEGRAM_CHAT_ID is None:
        tokens = False
        logger.critical
        (f'Проверьте доступность переменной окружения {TELEGRAM_CHAT_ID}')
    else:
        return tokens


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствуют необходимые переменные окружения')
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if homework:
                if homework == homework[0]:
                    message = parse_status(homework)
                    if homework != homework:
                        message = homework
                        send_message(bot, message)
                    else:
                        logger.info(f'Работа еще не проверена.'
                                    f'Попробую снова через {RETRY_TIME} секунд'
                                    )
                    time.sleep(RETRY_TIME)
            else:
                raise Exception('Новых сданных работ нет')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.critical(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
