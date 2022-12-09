class NotForTelegramError(Exception):
    """Не нужно отправлять в телегу."""

class TelegramError(Exception):
    """Вылетает когда не получилось выслать в телеграмм."""


class EmptyAPIResponseError(Exception):
    """Вылетает когда нет домашек."""


class WrongApiResponseCodeError(Exception):
    """Вылетает когда ответ сервера != 200."""


class RequestException(NotForTelegramError):
    """Вылетает при ошибке запроса."""


class JSONDecodeError(NotForTelegramError):
    """Вылетает когда не сформирован JSON."""


class ConnectionError(Exception):
    """Вылетает, когда произошла ошибка при подключении к серверу."""
