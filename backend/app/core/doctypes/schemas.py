import uuid
from pydantic import BaseModel, ConfigDict


class DoctypeBaseSchema(BaseModel):
    domain_id: uuid.UUID
    doctype: str
    doctype_name: str
    description: str | None = None
    is_active: bool = True


class DoctypeCreateSchema(DoctypeBaseSchema):
    # ✅ Список ID тенантов для синхронизации M2M (Правило №30)
    tenant_ids: list[uuid.UUID] = []


class DoctypeUpdateSchema(BaseModel):
    domain_id: uuid.UUID | None = None
    doctype: str | None = None
    doctype_name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    tenant_ids: list[uuid.UUID] | None = None


class DoctypeResponseSchema(DoctypeBaseSchema):
    # ✅ Правило №1: Разрешаем чтение из ORM-атрибутов (включая @property)
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID

    # ✅ Правило №33: Обычные поля — Pydantic прочитает их из @property модели
    # НЕ присваиваем значения в @property — они вычисляются автоматически
    domain_name: str | None = None
    tenant_ids: list[uuid.UUID] = []