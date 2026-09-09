import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict

# Импортируем схемы полномочий для вложенного массива

from app.core.permissions.schemas import PermissionResponseSchema
from app.core.permissions.schemas import PermissionCreateSchema

# Базовая схема
class RoleBaseSchema(BaseModel):
    name: str
    description: Optional[str] = None
    section_ids: Optional[list[uuid.UUID]] = None
    section_names: Optional[list[str]] = None

# Схема для создания
class RoleCreateSchema(RoleBaseSchema):
    tenant_id: uuid.UUID

# Схема для обновления (все поля опциональны)
class RoleUpdateSchema(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    section_ids: Optional[list[uuid.UUID]] = None
    section_names: Optional[list[str]] = None

# Схема для ответа (с from_attributes=True - Правило №1)
class RoleResponseSchema(RoleBaseSchema):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    tenant_id: uuid.UUID
    # Денормализованное имя тенанта для UI
    tenant_name: Optional[str] = None
    permissions: Optional[list[PermissionResponseSchema]] = None 


# Для агрегированного сохранения
class RoleSaveSchema(BaseModel):
    name: str
    description: Optional[str] = None
    tenant_id: uuid.UUID
    
    # Разделы
    section_ids: Optional[list[uuid.UUID]] = None
    section_names: Optional[list[str]] = None
    
    # Полномочия (массив объектов для создания/обновления)
    permissions: Optional[list[PermissionCreateSchema]] = None
    
    # Пользователи, которым назначается эта роль (массив ID)
    user_ids: Optional[list[uuid.UUID]] = None

# =========================================================================    




