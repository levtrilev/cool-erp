import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SectionCreateSchema(BaseModel):
    """Создание произвольного раздела (только админ/суперадмин)."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class SectionUpdateSchema(BaseModel):
    """Обновление произвольного раздела."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


class SectionResponseSchema(BaseModel):
    """Ответ API для раздела."""

    # ✅ Правило №1: чтение из ORM-атрибутов, включая @property
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID | None = None
    name: str
    description: str | None = None
    section_type: str
    is_protected: bool = False
    section_type_label: str = ""
    # ✅ Правило №42: денормализованное имя организации
    tenant_name: str | None = None
    created_at: datetime
    created_by_user_id: uuid.UUID | None = None
    updated_at: datetime
    updated_by_user_id: uuid.UUID | None = None