from typing import TypeVar, Generic, List, Optional
from pydantic import BaseModel, ConfigDict

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """Универсальная схема пагинации"""
    items: List[T]
    total: int
    page: int = 1
    size: int = 10
    
    # КРИТИЧЕСКИ ВАЖНО для Pydantic v2 и Orval
    model_config = ConfigDict(from_attributes=True)


class ApiResponse(BaseModel, Generic[T]):
    """Универсальная обертка ответа (Envelope pattern)"""
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None
    
    model_config = ConfigDict(from_attributes=True)