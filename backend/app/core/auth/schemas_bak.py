from pydantic import BaseModel, EmailStr
import uuid
from typing import Optional
from pydantic import BaseModel


class UserBaseSchema(BaseModel):
    name: str
    email: str


# class UserCreateSchema(UserBaseSchema):
#     password: str


class UserUpdateSchema(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    tenant_id: Optional[uuid.UUID] = None
    is_admin: Optional[bool] = None
    is_superadmin: Optional[bool] = None
    role_ids: Optional[list[uuid.UUID]] = None

class UserResponseSchema(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    tenant_id: uuid.UUID
    is_admin: bool
    is_superadmin: bool = False

    class Config:
        from_attributes = True


# ==========================================
# 5. СХЕМЫ ВАЛИДАЦИИ PYDANTIC (Payload)
# ==========================================
class UserRegisterSchema(BaseModel):
    name: str
    email: EmailStr
    password: str
    tenant_id: uuid.UUID
    is_admin: bool = False
    is_superadmin: bool = False


class UserLoginSchema(BaseModel):
    email: EmailStr
    password: str

class UserInfoResponse(BaseModel):
    """Схема данных пользователя для ответа"""
    id: uuid.UUID
    name: str
    email: str
    tenant_id: uuid.UUID
    is_admin: bool
    is_superadmin: bool = False

    class Config:
        from_attributes = True
#     model_config = {"from_attributes": True}  # Позволяет создавать из ORM-объекта


class GetUserResponse(BaseModel):
    """Схема ответа эндпоинта GET /user"""
    status: str
    user: UserInfoResponse

# class UserResponse(BaseModel):
#     """Схема данных пользователя для ответа"""
#     id: uuid.UUID
#     name: str
#     email: str
#     tenant_id: uuid.UUID
#     is_admin: bool
#     is_superadmin: bool = False

#     class Config:
#         from_attributes = True
    # model_config = {"from_attributes": True}  # Позволяет создавать из ORM-объекта
