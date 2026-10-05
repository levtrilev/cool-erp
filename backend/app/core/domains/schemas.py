import uuid
from pydantic import BaseModel, ConfigDict


class DomainBaseSchema(BaseModel):
    name: str
    description: str | None = None


class DomainCreateSchema(DomainBaseSchema):
    pass


class DomainUpdateSchema(BaseModel):
    name: str | None = None
    description: str | None = None


class DomainResponseSchema(DomainBaseSchema):
    # ✅ Правило №1: Разрешаем чтение из ORM-атрибутов (включая @property)
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID

    # ✅ Правило №33: Обычное поле — Pydantic прочитает его из @property модели
    # НЕ присваиваем значение — оно вычисляется автоматически
    doctypes_count: int = 0