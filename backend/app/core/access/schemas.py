from enum import Enum
from typing import Protocol
import uuid
from pydantic import BaseModel


class AccessSource(str, Enum):
    """Источник доступа к документу."""
    ROLE = "ROLE"
    DELEGATION = "DELEGATION"
    NONE = "NONE"


class AccessResult(BaseModel):
    """
    Результат вычисления доступа к документу (ТЗ §8.1).
    """
    visible: bool
    level: int  # 0-4
    can_delete: bool
    source: AccessSource
    
    class Config:
        use_enum_values = True


# ✅ Protocol для пользователя (используется в AccessService и CRUD)
# Описывает контракт полей, необходимых для проверки доступа.
# Совместим как с UserModel (ORM), так и с UserSession (Pydantic).
class UserProtocol(Protocol):
    """Контракт пользователя для проверки доступа."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    is_superadmin: bool
    is_admin: bool
    role_ids: list[uuid.UUID] | None
    tags: list[str] | None


# Уровни доступа (ТЗ §5.1)
ACCESS_LEVEL_NONE = 0
ACCESS_LEVEL_READER = 1
ACCESS_LEVEL_EDITOR = 2
ACCESS_LEVEL_AUTHOR = 3
ACCESS_LEVEL_FULL = 4