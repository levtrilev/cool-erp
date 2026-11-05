"""Специфичные исключения подмодуля regions (Правило №40, часть 7.3)."""


class RegionNotFoundError(Exception):
    """Регион не найден или недоступен в текущем тенанте (404)."""


class RegionVersionConflictError(Exception):
    """Ожидаемая версия не совпадает с версией в БД (409)."""


class RegionEditingLockedError(Exception):
    """Регион редактируется другим пользователем (423)."""