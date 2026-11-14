# backend/app/modules/sales/item_types/exceptions.py
"""Исключения модуля типов номенклатуры (Правило №40, часть 7.3)."""


class SalesItemTypeNotFoundError(Exception):
    """Запись не найдена или недоступна в текущем тенанте (404)."""


class SalesItemTypeVersionConflictError(Exception):
    """Ожидаемая версия не совпала (409)."""


class SalesItemTypeEditingLockedError(Exception):
    """Документ редактируется другим пользователем (423)."""


class SalesItemTypePermissionError(Exception):
    """Недостаточно прав на операцию (403)."""


class SectionNotInTenantError(Exception):
    """Раздел не существует или не принадлежит организации (400)."""