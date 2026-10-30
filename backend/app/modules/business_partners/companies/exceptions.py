"""Специфичные исключения подмодуля companies (Правило №40, часть 7.3)."""


class CompanyNotFoundError(Exception):
    """Компания не найдена или недоступна в текущем тенанте (404)."""


class CompanyVersionConflictError(Exception):
    """Ожидаемая версия не совпадает с версией в БД (409)."""


class CompanyEditingLockedError(Exception):
    """Компания редактируется другим пользователем (423)."""