from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional
# from datetime import datetime


class TenantBase(BaseModel):
    name: str = Field(..., max_length=128, description="Название организации")
    active: bool = Field(default=True, description="Активна ли организация")
    description: Optional[str] = Field(None, max_length=255, description="Описание")


class TenantCreate(TenantBase):
    """Схема для создания tenant"""
    pass


class TenantUpdate(BaseModel):
    """Схема для обновления tenant (все поля опциональны)"""
    name: Optional[str] = Field(None, max_length=128)
    active: Optional[bool] = None
    description: Optional[str] = Field(None, max_length=255)


class TenantResponse(TenantBase):
    """Схема ответа с tenant"""
    id: UUID
    # created_at: datetime
    # updated_at: datetime

    model_config = {"from_attributes": True}