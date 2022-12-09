class NotForTelegramError(Exception):
    """Не нужно отправлять в телегу."""

class TelegramError(Exception):
    """Вылетает когда не получилось выслать в телеграмм."""
    pass


class EmptyAPIResponseError(Exception):
    """Вылетает когда нет домашек."""
    pass


class WrongApiResponseCodeError(Exception):
    """Вылетает когда ответ сервера != 200."""
    pass


class RequestException(NotForTelegramError):
    """Вылетает при ошибке запроса."""
    pass


class JSONDecodeError(NotForTelegramError):
    """Вылетает когда не сформирован JSON."""
    pass


class ConnectionError(Exception):
    """Вылетает, когда произошла ошибка при подключении к серверу."""
    pass


