from pydantic import BaseModel, EmailStr, Field
import uuid
from typing import Optional


# ==========================================
# БАЗОВЫЕ СХЕМЫ
# ==========================================
class UserBaseSchema(BaseModel):
    name: str
    email: str
    tenant_id: uuid.UUID
    role_ids: Optional[list[uuid.UUID]] = None
    # ⚠️ role_names — ПРОИЗВОДНОЕ поле (вычисляется сервером из role_ids
    #    через CRUDUser._sync_role_names). НЕ должно приходить от клиента.
    #    В схемах запроса (UserRegisterSchema, UserUpdateSchema) его быть не должно.
    #    В UserResponseSchema — нужен (ответ клиенту с уже вычисленными именами).
    role_names: Optional[list[str]] = None
    tags: Optional[list[str]] = None

# ==========================================
# СХЕМЫ ДЛЯ СОЗДАНИЯ/ОБНОВЛЕНИЯ
# ==========================================
class UserRegisterSchema(UserBaseSchema):
    """Схема для регистрации нового пользователя"""
    #   ⚠️ role_names НЕ должен передаваться клиентом — это производное поле.
    #    Наследуется из UserBaseSchema для совместимости с UserResponseSchema,
    #   но при регистрации CRUDUser.register_new_user всегда пишет role_ids=[],
    #    а role_names вычисляется сервером при первом обновлении ролей.
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

    """⚠️ ВАЖНО: role_names здесь НЕТ и быть не должно.
    -------------------------------------------------
    role_names — ПРОИЗВОДНОЕ поле. Клиент передаёт только role_ids,
    а имена ролей вычисляются на сервере в CRUDUser.update_user
    через _sync_role_names() и записываются в модель.

    Почему нельзя вернуть role_names в эту схему:
      1. Клиент мог бы подделать имена ролей (например, передать
         role_names=["Хакер"] при role_ids=[uuid-обычного-пользователя]).
         В БД _sync_role_names перезапишет значение, но в АУДИТ
         (audit_service.log_data_update) попадёт то, что прислал клиент —
         аудит начнёт врать.
      2. Производные поля не должны приходить от клиента — это ловушка
         для будущих разработчиков.
      3. При аудите (комплаенс, расследование инцидентов) diff должен
         отражать реальные изменения в БД, а не то, что прислал клиент.

    Если нужно отфильтровать role_names из new_values для аудита —
    это делается в роутере, но правильнее — не иметь поля в схеме.
    """
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    tenant_id: Optional[uuid.UUID] = None
    is_admin: Optional[bool] = None
    is_superadmin: Optional[bool] = None
    role_ids: Optional[list[uuid.UUID]] = None
    role_names: Optional[list[str]] = None
    tags: Optional[list[str]] = None

# ==========================================
# СХЕМЫ ОТВЕТА (используются в response_model)
# ==========================================
class UserResponseSchema(BaseModel):
    """Схема ответа с данными пользователя"""
    id: uuid.UUID
    name: str
    email: str
    tenant_id: uuid.UUID
    tenant_name: Optional[str] = None
    is_admin: bool
    is_superadmin: bool = False
    role_ids: Optional[list[uuid.UUID]] = None
    role_names: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    
    model_config = {"from_attributes": True}  # Pydantic v2 стиль


class PublicRegisterResponseSchema(BaseModel):
    """Схема ответа для публичной регистрации (включает информацию о создании организации)"""
    id: uuid.UUID
    name: str
    email: str
    tenant_id: uuid.UUID
    is_admin: bool
    is_superadmin: bool = False
    is_new_tenant: bool = Field(..., description="True, если организация была создана заново")
    tenant_name: str = Field(..., description="Название организации для отображения в UI")
                             
class PaginatedUserResponse(BaseModel):
    """Конкретная схема пагинации для пользователей (Orval это любит)"""
    items: list[UserResponseSchema]
    total: int
    
    model_config = {"from_attributes": True}

class TagUserResponseSchema(BaseModel):
    """Пользователь, имеющий тег доступа."""
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    email: str
    tenant_id: uuid.UUID
    tenant_name: Optional[str] = None
    tags: Optional[list[str]] = None

class TagWithUsersResponseSchema(BaseModel):
    """Тег доступа и пользователи, которым он присвоен."""
    model_config = {"from_attributes": True}

    tag: str
    users: list[TagUserResponseSchema]