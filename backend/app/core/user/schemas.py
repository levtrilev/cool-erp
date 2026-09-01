from pydantic import BaseModel, EmailStr, Field
import uuid
from typing import Optional


# ==========================================
# БАЗОВЫЕ СХЕМЫ
# ==========================================
class UserBaseSchema(BaseModel):
    """Базовая схема пользователя (для наследования)"""
    name: str
    email: EmailStr


# ==========================================
# СХЕМЫ ДЛЯ СОЗДАНИЯ/ОБНОВЛЕНИЯ
# ==========================================
class UserRegisterSchema(UserBaseSchema):
    """Схема для регистрации нового пользователя"""
    password: str
    tenant_id: uuid.UUID
    is_admin: bool = False
    is_superadmin: bool = False

class PublicRegisterSchema(BaseModel):
    """Схема для публичной регистрации гостя (создает новый тенант)"""
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    tenant_name: str = Field(..., min_length=2, max_length=128, description="Название новой организации")

class UserLoginSchema(BaseModel):
    """Схема для входа в систему"""
    email: EmailStr
    password: str


class UserUpdateSchema(BaseModel):
    """Схема для обновления пользователя (все поля опциональны)"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    tenant_id: Optional[uuid.UUID] = None
    is_admin: Optional[bool] = None
    is_superadmin: Optional[bool] = None
    role_ids: Optional[list[uuid.UUID]] = None


# ==========================================
# СХЕМЫ ОТВЕТА (используются в response_model)
# ==========================================
class UserResponseSchema(BaseModel):
    """Схема ответа с данными пользователя"""
    id: uuid.UUID
    name: str
    email: str
    tenant_id: uuid.UUID
    is_admin: bool
    is_superadmin: bool = False

    model_config = {"from_attributes": True}  # Pydantic v2 стиль

class PaginatedUserResponse(BaseModel):
    """Конкретная схема пагинации для пользователей (Orval это любит)"""
    items: list[UserResponseSchema]
    total: int
    
    model_config = {"from_attributes": True}