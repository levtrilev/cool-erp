class NoteNotFoundError(Exception):
    """Документ не найден или недоступен в текущем тенанте."""


class NoteVersionConflictError(Exception):
    """Ожидаемая версия не совпадает с версией в БД (409)."""


class NoteEditingLockedError(Exception):
    """Документ редактируется другим пользователем (423)."""


class SectionNotInTenantError(Exception):
    """Раздел не существует или не принадлежит организации (400)."""