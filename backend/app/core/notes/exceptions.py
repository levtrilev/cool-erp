class NoteNotFoundError(Exception):
    """Документ не найден или недоступен в текущем тенанте (404)."""


class NoteVersionConflictError(Exception):
    """Ожидаемая версия не совпадает с версией в БД (409)."""


class NoteEditingLockedError(Exception):
    """Документ редактируется другим пользователем (423)."""


class SectionNotInTenantError(Exception):
    """Раздел не существует или не принадлежит организации (400)."""


class NoteAccessDeniedError(Exception):
    """
    Доступ к документу запрещён согласно алгоритму resolve_access (403).
    """


class NotePermissionError(Exception):
    """Недостаточно прав для операции с заметкой (403)."""