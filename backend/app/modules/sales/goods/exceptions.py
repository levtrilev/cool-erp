"""Специфичные исключения домена sales.goods (Правило №40, часть 7.3)."""


class GoodsNotFoundError(Exception):
    """Товар не найден или недоступен в текущем тенанте (404)."""


class GoodsVersionConflictError(Exception):
    """Ожидаемая версия не совпадает с версией в БД (409)."""


class GoodsEditingLockedError(Exception):
    """Товар редактируется другим пользователем (423)."""