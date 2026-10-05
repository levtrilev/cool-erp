import uuid
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict

class PermissionBaseSchema(BaseModel):
    """Базовые поля полномочия (БЕЗ id)."""
    doctype: str
    role_id: Optional[uuid.UUID] = None
    tenant_id: uuid.UUID
    
    full_access: bool = False
    author: bool = False
    reader: bool = False
    editor: bool = False
    can_delete: bool = False
    access_by_tags: bool = False
    
    or_tags: Optional[list[str] | dict[str, Any]] = None
    and_tags: Optional[list[str] | dict[str, Any]] = None
    no_tags: Optional[list[str] | dict[str, Any]] = None
    
    doctype_name: Optional[str] = None
    role_name: Optional[str] = None
    tenant_name: Optional[str] = None


class PermissionCreateSchema(PermissionBaseSchema):
    """Схема для создания/обновления через /roles/save.
    
    Поле id опционально:
    - Если id передан — обновляем существующую запись
    - Если id не передан — создаём новую
    """
    id: Optional[uuid.UUID] = None


class PermissionUpdateSchema(BaseModel):
    """Схема для частичного обновления (если понадобится отдельный эндпоинт)."""
    full_access: Optional[bool] = None
    author: Optional[bool] = None
    reader: Optional[bool] = None
    editor: Optional[bool] = None
    can_delete: Optional[bool] = None
    access_by_tags: Optional[bool] = None
    or_tags: Optional[list[str] | dict[str, Any]] = None
    and_tags: Optional[list[str] | dict[str, Any]] = None
    no_tags: Optional[list[str] | dict[str, Any]] = None
    doctype_name: Optional[str] = None
    role_name: Optional[str] = None
    tenant_name: Optional[str] = None


class PermissionResponseSchema(PermissionBaseSchema):
    """Схема ответа — id всегда присутствует."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID  # ✅ Обязательно, так как базовый класс НЕ содержит id

# class PermissionCreateSchema(PermissionBaseSchema):
#     pass

# class PermissionUpdateSchema(BaseModel):
#     full_access: Optional[bool] = None
#     author: Optional[bool] = None
#     reader: Optional[bool] = None
#     editor: Optional[bool] = None
#     can_delete: Optional[bool] = None
#     access_by_tags: Optional[bool] = None
#     or_tags: Optional[dict[str, Any]] = None
#     and_tags: Optional[dict[str, Any]] = None
#     no_tags: Optional[dict[str, Any]] = None
#     doctype_name: Optional[str] = None
#     role_name: Optional[str] = None
#     tenant_name: Optional[str] = None

# class PermissionResponseSchema(PermissionBaseSchema):
#     model_config = ConfigDict(from_attributes=True)
#     id: uuid.UUID