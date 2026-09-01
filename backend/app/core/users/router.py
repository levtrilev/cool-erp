from typing import Optional
# from datetime import datetime, timedelta, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, status   #, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import delete

from app.core.database import get_db
from app.core.users.schemas import (
    PublicRegisterSchema,
    UserRegisterSchema,
    UserUpdateSchema,
    UserResponseSchema,
)
from app.core.users.crud import crud_user
# from app.core.auth.dependencies import require_admin
# from app.core.auth.security import get_current_session
# from app.core.user.models import UserModel  as User
from app.core.schemas import PaginatedResponse  # , ApiResponse
from app.core.tenant.crud import crud_tenant
# from app.core.admin.models import TenantModel
from app.core.users.schemas import PublicRegisterResponseSchema

# Создаем роутер для авторизации
router = APIRouter(prefix="/users", tags=["Users"])

SESSION_LIFETIME_DAYS = 7

# ==========================================
# ПУБЛИЧНАЯ РЕГИСТРАЦИЯ (Умная логика)
# ==========================================
@router.post("/public/register", status_code=status.HTTP_201_CREATED, response_model=PublicRegisterResponseSchema)
async def public_register(user_in: PublicRegisterSchema, db: AsyncSession = Depends(get_db)):
    """
    Публичная регистрация гостя.
    - Если организация с таким именем существует → регистрирует как рядового пользователя.
    - Если не существует → создает новую организацию и регистрирует как администратора.
    """
    # 1. Проверяем, нет ли уже пользователя с таким email
    existing_user = await crud_user.get_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[
                {
                    "loc": ["body", "email"],
                    "msg": "Пользователь с таким email уже существует",
                    "type": "value_error",
                }
            ],
        )

    # 2. Ищем организацию по имени
    existing_tenant = await crud_tenant.get_by_name(db, name=user_in.tenant_name)
    
    is_new_tenant = False
    tenant_id = None
    is_admin = False

    if existing_tenant:
        # ✅ Организация существует → рядовой пользователь
        tenant_id = existing_tenant.id
        is_admin = False
    else:
        # ✅ Организация не существует → создаем новую, пользователь будет админом
        try:
            new_tenant = await crud_tenant.create(db, name=user_in.tenant_name)
            tenant_id = new_tenant.id
            is_admin = True
            is_new_tenant = True
        except Exception as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка при создании организации: {str(e)}",
            )

    # 3. Создаем пользователя
    print(f"📝 Создаём пользователя с is_admin={is_admin}")
    try:
        user_register_data = UserRegisterSchema(
            name=user_in.name,
            email=user_in.email,
            password=user_in.password,
            tenant_id=tenant_id,
            is_admin=is_admin,
            is_superadmin=False,
        )
        new_user = await crud_user.register_new_user(db, user_in=user_register_data)
        print(f"📝 Данные для CRUD: tenant_id={user_register_data.tenant_id}, is_admin={user_register_data.is_admin}")
        
        await db.commit()
        await db.refresh(new_user)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка при создании пользователя: {str(e)}",
        )

    # 4. Формируем ответ с дополнительной информацией
    return PublicRegisterResponseSchema(
        id=new_user.id,
        name=new_user.name,
        email=new_user.email,
        tenant_id=new_user.tenant_id,
        is_admin=new_user.is_admin,
        is_superadmin=new_user.is_superadmin or False,
        is_new_tenant=is_new_tenant,
        tenant_name=user_in.tenant_name,
    )



# ==========================================
# ПУБЛИЧНАЯ РЕГИСТРАЦИЯ (Создание Tenant + User)
# ==========================================
# @router.post("/public/register", status_code=status.HTTP_201_CREATED)
# async def public_register(user_in: PublicRegisterSchema, db: AsyncSession = Depends(get_db)):
#     """
#     Публичная регистрация гостя.
#     Автоматически создает новую организацию (Tenant) и делает пользователя её админом.
#     """
#     # 1. Проверяем, нет ли уже пользователя с таким email
#     existing_user = await crud_user.get_by_email(db, email=user_in.email)
#     if existing_user:
#         raise HTTPException(
#             status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#             detail=[
#                 {
#                     "loc": ["body", "email"],
#                     "msg": "Пользователь с таким email уже существует",
#                     "type": "value_error",
#                 }
#             ],
#         )

#     # 2. Проверяем, нет ли уже организации с таким названием
#     existing_tenant = await crud_tenant.get_by_name(db, name=user_in.tenant_name)
#     if existing_tenant:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Организация с таким названием уже существует. Пожалуйста, выберите другое.",
#         )

#     # 3. Создаем новую организацию и пользователя в одной транзакции
#     try:
#         # 3a. Создаем Tenant (flush внутри crud_tenant.create)
#         new_tenant = await crud_tenant.create(db, name=user_in.tenant_name)

#         # 3b. Формируем данные для внутреннего метода создания пользователя
#         user_register_data = UserRegisterSchema(
#             name=user_in.name,
#             email=user_in.email,
#             password=user_in.password,
#             tenant_id=new_tenant.id,
#             is_admin=True,        # Гость становится админом своей организации
#             is_superadmin=False,
#         )

#         # 3c. Создаем пользователя через существующий CRUD
#         new_user = await crud_user.register_new_user(db, user_in=user_register_data)

#         # 3d. Коммитим транзакцию (если register_new_user не коммитит сам)
#         await db.commit()
#         await db.refresh(new_user)

#     except HTTPException:
#         raise
#     except Exception as e:
#         await db.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Ошибка при создании организации и пользователя: {str(e)}",
#         )

#     return UserResponseSchema.model_validate(new_user)

# ==========================================
# РЕГИСТРАЦИЯ
# ==========================================
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_in: UserRegisterSchema, db: AsyncSession = Depends(get_db)):
    """Регистрация нового пользователя"""
    existing_user = await crud_user.get_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=[
                {
                    "loc": ["body", "email"],
                    "msg": "Пользователь с таким email уже существует",
                    "type": "value_error",
                }
            ],
        )

    try:
        new_user = await crud_user.register_new_user(db, user_in=user_in)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка создания. Возможно tenant_id не существует в вашей БД.",
        )

    # return {"message": f"Пользователь {new_user.name} успешно зарегистрирован"}
    return new_user


# ==========================================
# АУТЕНТИФИКАЦИЯ
# ==========================================
# @router.post("/login", status_code=status.HTTP_200_OK)
# async def login(
#     request: Request,
#     user_in: UserLoginSchema,
#     response: Response,
#     db: AsyncSession = Depends(get_db),
# ):
#     """Авторизация пользователя с созданием сессии в БД"""
#     db_user = await crud_user.get_by_email(db, email=user_in.email)

#     if not db_user or not crud_user.authenticate(db_user, user_in.password):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Неверный email или пароль",
#         )

#     session_token = uuid.uuid4().hex
#     expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_LIFETIME_DAYS)

#     new_session = UserSession(
#         session_token=session_token,
#         user_id=db_user.id,
#         expires_at=expires_at,
#         ip_address=request.client.host if request.client else None,
#         user_agent=request.headers.get("user-agent", "")[:512],
#     )
#     db.add(new_session)
#     await db.commit()

#     response.set_cookie(
#         key="session_token",
#         value=session_token,
#         httponly=True,
#         samesite="lax",
#         secure=False,
#         max_age=SESSION_LIFETIME_DAYS * 24 * 60 * 60,
#         path="/",
#     )

#     return {"message": "Успешная авторизация"}


# @router.post("/logout")
# async def logout(
#     request: Request,
#     response: Response,
#     db: AsyncSession = Depends(get_db),
# ):
#     """Выход из системы: удаляет сессию из БД и очищает куку"""
#     session_token = request.cookies.get("session_token")

#     if session_token:
#         await db.execute(
#             delete(UserSession).where(UserSession.session_token == session_token)  # type: ignore
#         )
#         await db.commit()

#     response.delete_cookie(
#         key="session_token",
#         path="/",
#         samesite="lax",
#     )

#     return {"message": "Успешный выход"}


# ==========================================
# ПОЛУЧЕНИЕ ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ
# ==========================================
# @router.get("/user", response_model=UserResponseSchema)
# async def get_user(current_user: User = Depends(get_current_session)):
#     """Получение профиля текущего пользователя"""
#     # ✅ Явная конвертация ORM → Pydantic (критично для Orval!)
#     return UserResponseSchema.model_validate(current_user)
# @router.get("/user", response_model=ApiResponse[UserResponseSchema])
# async def get_user(current_user: User = Depends(get_current_session)):
#     """Получение профиля текущего пользователя во вложенной обертке"""
    
#     # 1. Конвертируем ORM в Pydantic
#     user_data = UserResponseSchema.model_validate(current_user)
    
#     # 2. Явно создаем экземпляр обертки (Orval это обожает)
#     return ApiResponse[UserResponseSchema](
#         success=True,
#         message="Пользователь успешно получен",
#         data=user_data
#     )

# ==========================================
# CRUD ОПЕРАЦИИ С ПОЛЬЗОВАТЕЛЯМИ
# ==========================================
# @router.get("/", response_model=PaginatedUserResponse)
# async def read_users(
#     skip: int = 0,
#     limit: int = 100,
#     search: Optional[str] = None,
#     db: AsyncSession = Depends(get_db),
# ):
#     """Получение списка пользователей с пагинацией"""
#     items, total = await crud_user.get_multi_paginated(
#         db, skip=skip, limit=limit, search=search
#     )
#     # ✅ Явная конвертация списка ORM → список Pydantic
#     return PaginatedUserResponse(
#         items=[UserResponseSchema.model_validate(item) for item in items],
#         total=total
#     )
@router.get("/", response_model=PaginatedResponse[UserResponseSchema])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Получение списка пользователей с пагинацией"""
    items, total = await crud_user.get_multi_paginated(
        db, skip=skip, limit=limit, search=search
    )
    
    # Явно создаем экземпляр дженерика
    return PaginatedResponse[UserResponseSchema](
        items=[UserResponseSchema.model_validate(item) for item in items],
        total=total,
        page=(skip // limit) + 1,
        size=limit
    )

@router.get("/{user_id}", response_model=UserResponseSchema)
async def read_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Получение одного пользователя по UUID"""
    db_user = await crud_user.get(db, id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    # ✅ Явная конвертация ORM → Pydantic
    return UserResponseSchema.model_validate(db_user)


@router.put("/{user_id}", response_model=UserResponseSchema)
async def update_user(
    user_id: uuid.UUID,
    user_changes: UserUpdateSchema,
    db: AsyncSession = Depends(get_db),
):
    """Обновление пользователя"""
    db_user = await crud_user.get(db, id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        updated_user = await crud_user.update_user(
            db, db_user=db_user, user_changes=user_changes
        )
    except Exception as e:
        import logging
        logging.error(f"Ошибка обновления пользователя {user_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка обновления. Возможно ошибка БД.",
        )

    # ✅ Явная конвертация ORM → Pydantic
    return UserResponseSchema.model_validate(updated_user)


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Удаление пользователя из базы данных"""
    deleted_user = await crud_user.remove(db, id=user_id)

    if deleted_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "status": "success",
        "message": f"User {deleted_user.name} successfully deleted",
    }