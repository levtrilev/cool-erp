import uuid
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict

class PermissionBaseSchema(BaseModel):
    doctype: str
    role_id: uuid.UUID
    tenant_id: uuid.UUID
    
    # Флаги
    full_access: bool = False
    author: bool = False
    reader: bool = False
    editor: bool = False
    can_delete: bool = False
    access_by_tags: bool = False
    
    # Теги
    or_tags: Optional[dict[str, Any]] = None
    and_tags: Optional[dict[str, Any]] = None
    no_tags: Optional[dict[str, Any]] = None
    
    # Денормализованные поля
    doctype_name: Optional[str] = None
    role_name: Optional[str] = None
    tenant_name: Optional[str] = None

class PermissionCreateSchema(PermissionBaseSchema):
    pass

class PermissionUpdateSchema(BaseModel):
    full_access: Optional[bool] = None
    author: Optional[bool] = None
    reader: Optional[bool] = None
    editor: Optional[bool] = None
    can_delete: Optional[bool] = None
    access_by_tags: Optional[bool] = None
    or_tags: Optional[dict[str, Any]] = None
    and_tags: Optional[dict[str, Any]] = None
    no_tags: Optional[dict[str, Any]] = None
    doctype_name: Optional[str] = None
    role_name: Optional[str] = None
    tenant_name: Optional[str] = None

class PermissionResponseSchema(PermissionBaseSchema):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID