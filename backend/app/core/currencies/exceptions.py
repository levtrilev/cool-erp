"""Специфичные исключения модуля валют."""


class CurrencyNotFoundError(Exception):
    """Валюта не найдена (404)."""


class CurrencyCodeAlreadyExistsError(Exception):
    """Валюта с таким кодом уже существует (409)."""


class CurrencyInUseError(Exception):
    """Валюта используется в документах и не может быть удалена (400)."""