import uuid

from pydantic import BaseModel, ConfigDict, Field


class SectionBaseSchema(BaseModel):
    """Базовая схема с общими полями."""
    name: str = Field(
        ..., 
        min_length=1, 
        max_length=128, 
        description="Название раздела"
    )


class SectionCreateSchema(SectionBaseSchema):
    """Схема для создания нового раздела."""
    tenant_id: uuid.UUID | None = Field(
        None, 
        description="ID организации (обычно подставляется из сессии)"
    )


class SectionUpdateSchema(BaseModel):
    """Схема для обновления раздела (все поля опциональны)."""
    name: str | None = Field(
        None, 
        min_length=1, 
        max_length=128, 
        description="Название раздела"
    )


class SectionResponseSchema(BaseModel):
    """Схема ответа API (используется для возврата данных из ORM)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    tenant_id: uuid.UUID
    tenant_name: str