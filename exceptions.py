class HomeworkExceptionError(Exception):
    """Базовый класс для исключений уровня Error."""

    pass


class ApiNotAvailable(HomeworkExceptionError):
    """API практикума недоступно."""

    pass


class ApiJsonErorr(HomeworkExceptionError):
    """Ошибка преобразования в методе json."""

    pass