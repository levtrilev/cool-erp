"""Pydantic-схемы справочника валют (Правило №21)."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CurrencyCreateSchema(BaseModel):
    """Создание валюты."""
    code: str = Field(..., min_length=3, max_length=3)
    name: str = Field(..., min_length=1, max_length=255)
    symbol: str | None = Field(default=None, max_length=10)
    numeric_code: int | None = None
    is_active: bool = True


class CurrencyUpdateSchema(BaseModel):
    """Обновление валюты (все поля опциональны)."""
    code: str | None = Field(default=None, min_length=3, max_length=3)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    symbol: str | None = Field(default=None, max_length=10)
    numeric_code: int | None = None
    is_active: bool | None = None


class CurrencyResponseSchema(BaseModel):
    """Ответ: валюта с временными метками."""
    model_config = ConfigDict(from_attributes=True)  # Правило №1

    id: uuid.UUID
    code: str
    name: str
    symbol: str | None = None
    numeric_code: int | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime