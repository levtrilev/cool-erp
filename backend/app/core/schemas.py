# app/core/schemas.py
from typing import Generic, List, TypeVar
from pydantic import BaseModel

# Объявляем переменную типа для генерализации ответа
T = TypeVar("T")


# Универсальная схема ответа с пагинацией для фронтенда
class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
