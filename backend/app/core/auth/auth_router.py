# app/core/auth/router.py
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
import uuid
from app.core.auth.schemas import UserLoginSchema, UserRegisterSchema, UserUpdateSchema, UserResponseSchema
from app.core.auth.crud import crud_user, sessions_storage
from app.core.auth.dependencies import get_current_session, require_admin

# Создаем роутер для авторизации. Префикс /auth объединит все эндпоинты входа/регистрации
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_in: UserRegisterSchema, db: AsyncSession = Depends(get_db)):
    # 1. Бизнес-проверка через CRUD-сервис
    existing_user = await crud_user.get_by_email(db, email=user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже существует",
        )

    # 2. Выполнение регистрации
    try:
        new_user = await crud_user.register_new_user(db, user_in=user_in)
    except Exception:
        # Перехватываем ошибку внешнего ключа tenant_id
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка создания. Возможно tenant_id не существует в вашей БД.",
        )

    return {"message": f"Пользователь {new_user.name} успешно зарегистрирован"}


@router.put("/{user_id}", response_model=UserResponseSchema)
async def update_user(
    user_id: uuid.UUID,
    user_changes: UserUpdateSchema,
    db: AsyncSession = Depends(get_db),
):
    # 1. Проверяем, существует ли пользователь в базе данных
    db_user = await crud_user.get(db, id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    # 2. Выполнение обновления
    try:
        updated_user = await crud_user.update_user(db, db_user=db_user, user_changes=user_changes)
    except Exception:
        # Перехватываем ошибку внешнего ключа tenant_id
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ошибка обновления. Возможно ошибка БД.",
        )

    return updated_user
    

    # # 1. Проверяем, существует ли пользователь в базе данных
    # db_user = await crud_user.get(db, id=user_id)
    # if db_user is None:
    #     raise HTTPException(status_code=404, detail="User not found")

    # # 2. Передаем объект из БД и схему обновлений в базовый CRUD.
    # # Он автоматически обновит измененные поля и сделает безопасный commit/rollback.
    # updated_user = await crud_user.update(db, db_obj=db_user, obj_in=user_in)
    # return updated_user


@router.post("/login")
async def login(
    user_in: UserLoginSchema, response: Response, db: AsyncSession = Depends(get_db)
):
    # 1. Поиск пользователя через слой CRUD
    db_user = await crud_user.get_by_email(db, email=user_in.email)

    # 2. Проверка подлинности
    if not db_user or not crud_user.authenticate(db_user, user_in.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль"
        )

    # 3. Генерация токена сессии
    session_token = str(uuid.uuid4())
    sessions_storage[session_token] = {
        "user_id": str(db_user.id),
        "name": db_user.name,
        "email": db_user.email,
        "tenant_id": str(db_user.tenant_id),
        "is_admin": db_user.is_admin,
        "is_superadmin": db_user.is_superadmin,
        "role_ids": db_user.role_ids,
    }

    # 4. Установка httpOnly куки
    response.set_cookie(
        key="session_token", value=session_token, httponly=True, samesite="lax"
    )
    return {"message": "Успешная авторизация"}


@router.get("/user")
async def get_user(current_user: dict[str, dict[str, Any]] = Depends(get_current_session)):
    """Получение профиля текущего пользователя"""
    return {"status": "Доступ разрешен", "user": current_user}


@router.get("/admin/dashboard")
async def get_admin_dashboard(current_admin: dict[str, dict[str, Any]] = Depends(require_admin)):
    """Защищенный маршрут только для администраторов"""
    return {"message": f"Добро пожаловать в админ-панель, {current_admin['name']}!"}


@router.post("/logout")
async def logout(response: Response, session_token: str | None = Cookie(default=None)):
    """Выход из системы с очисткой сессии"""
    if session_token and session_token in sessions_storage:
        del sessions_storage[session_token]

    response.delete_cookie(key="session_token", httponly=True, samesite="lax")
    return {"message": "Вы успешно вышли из системы"}

@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Удаление пользователя из базы данных.
    """
    # метод crud_user.remove сам проверит существование,
    # удалит запись, выполнит коммит и вернет удаленный объект (или None)
    deleted_user = await crud_user.remove(db, id=user_id)

    if deleted_user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "status": "success",
        "message": f"User {deleted_user.name} successfully deleted",
    }