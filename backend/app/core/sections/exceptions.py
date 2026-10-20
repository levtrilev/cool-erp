class SectionNotFoundError(Exception):
    """Раздел не найден или недоступен в текущем тенанте."""


class SectionProtectedError(Exception):
    """Раздел защищён от удаления или переименования (403)."""


class SectionHasDocumentsError(Exception):
    """Раздел содержит документы и не может быть удалён (409)."""


class SectionNotInTenantError(Exception):
    """Раздел не принадлежит текущей организации (400)."""


class SectionNotAdminError(Exception):
    """Операция доступна только администратору или суперадмину (403)."""