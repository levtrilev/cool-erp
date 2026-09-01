# backend/app/core/tenant/schemas.py
from pydantic import BaseModel, Field
import uuid
from typing import Optional


# ==========================================
# БАЗОВЫЕ СХЕМЫ
# ==========================================
class TenantBaseSchema(BaseModel):
    """Базовая схема организации (для наследования)"""
    name: str = Field(..., min_length=2, max_length=128)
    description: Optional[str] = Field(None, max_length=255)


# ==========================================
# СХЕМЫ ДЛЯ СОЗДАНИЯ/ОБНОВЛЕНИЯ
# ==========================================
class TenantCreateSchema(TenantBaseSchema):
    """Схема для создания новой организации"""
    active: bool = Field(True, description="Активна ли организация")


class TenantUpdateSchema(BaseModel):
    """Схема для обновления организации (все поля опциональны)"""
    name: Optional[str] = Field(None, min_length=2, max_length=128)
    description: Optional[str] = Field(None, max_length=255)
    active: Optional[bool] = Field(None, description="Активна ли организация")


# ==========================================
# СХЕМЫ ОТВЕТА (используются в response_model)
# ==========================================
class TenantResponseSchema(BaseModel):
    """Схема ответа с данными организации"""
    id: uuid.UUID
    name: str
    active: bool
    description: Optional[str] = None

    model_config = {"from_attributes": True}  # Pydantic v2 стиль