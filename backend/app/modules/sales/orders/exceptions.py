"""Специфичные исключения модуля заказов продаж (Правило №40, часть 7.3)."""


class SalesOrderNotFoundError(Exception):
    """Заказ не найден или недоступен пользователю (404)."""


class SalesOrderVersionConflictError(Exception):
    """Ожидаемая версия не совпадает с версией в БД (409)."""


class SalesOrderEditingLockedError(Exception):
    """Заказ редактируется другим пользователем (423)."""


class SalesOrderAccessDeniedError(Exception):
    """Недостаточно прав на операцию с заказом (403)."""


class SalesOrderPermissionError(Exception):
    """Нет права на создание/изменение заказа (403)."""


class SectionNotInTenantError(Exception):
    """Раздел не существует или недоступен в организации (400)."""


class DeliveryMethodInvalidError(Exception):
    """Недопустимое значение способа доставки (400)."""