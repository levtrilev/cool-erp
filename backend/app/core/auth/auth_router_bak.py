# from typing import Any

# from fastapi import (
#     APIRouter,
#     Depends,
#     HTTPException,
#     Response,
#     status,
#     Request,
# )  # , Cookie
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.core.database import get_db
# import uuid
# from app.core.auth.schemas import (
#     UserLoginSchema,
#     UserRegisterSchema,
#     UserUpdateSchema,
#     UserResponseSchema,
# )
# from app.core.auth.crud import crud_user  # , sessions_storage
# from app.core.auth.dependencies import get_current_session, require_admin
# from datetime import datetime, timedelta
# from app.core.auth.models import UserSession
# from datetime import datetime, timedelta, timezone
# from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import delete
# from sqlalchemy.sql import Delete
# from app.core.auth.security import get_current_session
# from app.core.auth.models import UserModel as User
# from app.core.schemas import PaginatedResponse
# from typing import Optional

# # Создаем роутер для авторизации. Префикс /auth объединит все эндпоинты входа/регистрации
# router = APIRouter(prefix="/auth", tags=["Authentication"])

# SESSION_LIFETIME_DAYS = 7


# @router.post("/register", status_code=status.HTTP_201_CREATED)
# async def register(user_in: UserRegisterSchema, db: AsyncSession = Depends(get_db)):
#     # 1. Бизнес-проверка через CRUD-сервис
#     existing_user = await crud_user.get_by_email(db, email=user_in.email)
#     if existing_user:
#         #     raise HTTPException(
#         #         status_code=status.HTTP_400_BAD_REQUEST,
#         #         detail="Пользователь с таким email уже существует",
#         #     )
#         # Возвращаем ошибку 422 с конкретной информацией о поле
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

#     # 2. Выполнение регистрации
#     try:
#         new_user = await crud_user.register_new_user(db, user_in=user_in)
#     except Exception:
#         # Перехватываем ошибку внешнего ключа tenant_id
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Ошибка создания. Возможно tenant_id не существует в вашей БД.",
#         )

#     return {"message": f"Пользователь {new_user.name} успешно зарегистрирован"}


# @router.put("/{user_id}", response_model=UserResponseSchema)
# async def update_user(
#     user_id: uuid.UUID,
#     user_changes: UserUpdateSchema,
#     db: AsyncSession = Depends(get_db),
# ):
#     # 1. Проверяем, существует ли пользователь в базе данных
#     db_user = await crud_user.get(db, id=user_id)
#     if db_user is None:
#         raise HTTPException(status_code=404, detail="User not found")

#     # 2. Выполнение обновления
#     try:
#         updated_user = await crud_user.update_user(
#             db, db_user=db_user, user_changes=user_changes
#         )
#     except Exception:
#         # Перехватываем ошибку внешнего ключа tenant_id
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Ошибка обновления. Возможно ошибка БД.",
#         )

#     return updated_user


# @router.post("/login", status_code=status.HTTP_200_OK)
# async def login(
#     request: Request,
#     user_in: UserLoginSchema,
#     response: Response,
#     db: AsyncSession = Depends(get_db),
# ):
#     """Авторизация пользователя с созданием сессии в БД"""

#     # 1. Поиск пользователя
#     db_user = await crud_user.get_by_email(db, email=user_in.email)

#     # 2. Проверка подлинности
#     if not db_user or not crud_user.authenticate(db_user, user_in.password):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Неверный email или пароль",
#         )

#     # 3. Генерация токена и времени истечения (timezone-aware!)
#     session_token = uuid.uuid4().hex
#     expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_LIFETIME_DAYS)

#     # 4. Сохранение сессии в БД
#     new_session = UserSession(
#         session_token=session_token,
#         user_id=db_user.id,
#         expires_at=expires_at,
#         ip_address=request.client.host if request.client else None,
#         user_agent=request.headers.get("user-agent", "")[:512],
#     )
#     db.add(new_session)
#     await db.commit()

#     # 5. Установка HttpOnly куки
#     response.set_cookie(
#         key="session_token",
#         value=session_token,
#         httponly=True,
#         samesite="lax",
#         secure=False,  # True в продакшене с HTTPS
#         max_age=SESSION_LIFETIME_DAYS * 24 * 60 * 60,
#         path="/",
#     )

#     return {"message": "Успешная авторизация"}


# @router.get("/user", response_model=UserResponseSchema)
# async def get_user(current_user: User = Depends(get_current_session)):
#     """Получение профиля текущего пользователя"""
#     return current_user


# # @router.get("/user")
# # async def get_user(current_user: User = Depends(get_current_session)) -> dict[str, Any]:
# #     """Получение профиля текущего пользователя"""
# #     return {
# #         "status": "Доступ разрешен",
# #         "user": {
# #             "id": str(current_user.id),
# #             "name": current_user.name,
# #             "email": current_user.email,
# #             "tenant_id": str(current_user.tenant_id),
# #             "is_admin": current_user.is_admin,
# #             "is_superadmin": current_user.is_superadmin,
# #         }
# #     }
# @router.get("/admin/dashboard")
# async def get_admin_dashboard(
#     current_admin: dict[str, dict[str, Any]] = Depends(require_admin),
# ):
#     """Защищенный маршрут только для администраторов"""
#     return {"message": f"Добро пожаловать в админ-панель, {current_admin['name']}!"}


# # @router.post("/logout")
# # async def logout(response: Response, session_token: str | None = Cookie(default=None)):
# #     """Выход из системы с очисткой сессии"""
# #     if session_token and session_token in sessions_storage:
# #         del sessions_storage[session_token]

# #     response.delete_cookie(key="session_token", httponly=True, samesite="lax")
# #     return {"message": "Вы успешно вышли из системы"}

# # from fastapi import APIRouter, Depends, Response, Request, status
# # from sqlalchemy.ext.asyncio import AsyncSession
# # from sqlalchemy import delete

# # from app.core.database import get_db
# # from app.core.auth.models import UserSession
# # from app.core.security import get_current_session  # Ваша зависимость для получения текущего пользователя
# # from app.core.auth.models import UserModel

# # @router.post("/logout")
# # async def logout(
# #     request: Request,
# #     response: Response,
# #     current_user: UserModel = Depends(get_current_session),
# #     db: AsyncSession = Depends(get_db),
# # ):
# #     """Выход из системы: удаляет текущую сессию из БД"""

# #     # 1. Получаем токен из куки
# #     session_token = request.cookies.get("session_token")

# #     if session_token:
# #         # 2. Удаляем сессию из БД
# #         await db.execute(
# #             delete(UserSession).where(UserSession.session_token == session_token) # type: ignore
# #         )
# #         await db.commit()

# #     # 3. Очищаем куку на клиенте
# #     response.delete_cookie(
# #         key="session_token",
# #         path="/",
# #         samesite="lax",
# #     )

# #     return {"message": "Успешный выход"}


# @router.post("/logout")
# async def logout(
#     request: Request,
#     response: Response,
#     db: AsyncSession = Depends(get_db),
# ):
#     """Выход из системы: удаляет сессию из БД и очищает куку"""

#     # 1. Читаем токен напрямую из куки (без зависимости get_current_session)
#     session_token = request.cookies.get("session_token")

#     if session_token:
#         # Явно типизируем statement
#         stmt: Delete = delete(UserSession).where(
#             UserSession.session_token == session_token
#         )
#         await db.execute(stmt)
#         await db.commit()

#     # 3. Очищаем куку на клиенте.
#     # ВАЖНО: параметры path и samesite должны точно совпадать с теми, что были при set_cookie!
#     response.delete_cookie(
#         key="session_token",
#         path="/",
#         samesite="lax",
#     )

#     return {"message": "Успешный выход"}


# @router.delete("/{user_id}", status_code=status.HTTP_200_OK)
# async def delete_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
#     """Удаление пользователя из базы данных."""
#     # метод crud_user.remove сам проверит существование,
#     # удалит запись, выполнит коммит и вернет удаленный объект (или None)
#     deleted_user = await crud_user.remove(db, id=user_id)

#     if deleted_user is None:
#         raise HTTPException(status_code=404, detail="User not found")

#     return {
#         "status": "success",
#         "message": f"User {deleted_user.name} successfully deleted",
#     }


# @router.get("/", response_model=PaginatedResponse[UserResponseSchema])
# async def read_users(
#     skip: int = 0,
#     limit: int = 100,
#     search: Optional[str] = None,
#     db: AsyncSession = Depends(get_db),
# ):
#     """Получение списка пользователей с пагинацией и GIN-поиском."""
#     items, total = await crud_user.get_multi_paginated(
#         db, skip=skip, limit=limit, search=search
#     )
#     return {"items": items, "total": total}


# @router.get("/{user_id}", response_model=UserResponseSchema)
# async def read_user(user_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
#     """Получение одного пользователя по UUID."""
#     db_user = await crud_user.get(db, id=user_id)
#     if db_user is None:
#         raise HTTPException(status_code=404, detail="User not found")
#     return db_user
