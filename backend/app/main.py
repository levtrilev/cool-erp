from contextlib import asynccontextmanager
import uuid
import bcrypt
from fastapi import FastAPI, Cookie, Response, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import select, text
from app.core.config import settings
from app.core.database import async_session, get_db
from app.core.auth.models import UserModel
from app.core.auth.schemas import UserLoginSchema, UserRegisterSchema
from app.core.auth.user_router import router as user_router
from app.core.auth.auth_router import router as auth_router


# Хранилище сессий в оперативной памяти сервера (токен -> метаданные)
sessions_storage = {}

# ==========================================
# 4. СОВРЕМЕННЫЙ LIFESPAN (Жизненный цикл)
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код выполняется строго ПРИ СТАРТЕ сервера
    async with async_session() as session:
        result = await session.execute(
            select(UserModel).where(UserModel.email == "superadmin@yandex.ru")
        )
        if not result.scalar_one_or_none():
            salt = bcrypt.gensalt()
            hashed_admin_pass = bcrypt.hashpw(settings.SUPERADMIN_PASSWORD.encode('utf-8'), salt)
            
            admin_user = UserModel(
                name="superadmin@yandex.ru",
                email="superadmin@yandex.ru",
                password=hashed_admin_pass.decode('utf-8'),
                is_admin=True,
                is_superadmin=True,
                tenant_id=settings.SUPERADMIN_TENANT_ID,
                role_ids=[]
            )
            session.add(admin_user)
            await session.commit()
            print("🚀 СуперАдминистратор по умолчанию успешно проверен/создан в PostgreSQL.")
            
    yield  # В этой точке приложение запускается и начинает слушать запросы
    
    # Код выполняется строго ПРИ ОСТАНОВКЕ сервера
    print("🛑 Сервер останавливается. Очистка ресурсов...")

app = FastAPI(lifespan=lifespan)
app.include_router(user_router)
app.include_router(auth_router)
# ==========================================
# 6. ВЫДЕЛЕННЫЕ ЗАВИСИМОСТИ (DEPENDENCIES)
# ==========================================
# Позволяет получать данные сессии одной строчкой в любом роуте
async def get_current_session(session_token: str | None = Cookie(default=None)) -> dict:
    if not session_token or session_token not in sessions_storage:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Вы не авторизованы или сессия истекла"
        )
    return sessions_storage[session_token]

# Расширенная зависимость: пустит только если пользователь админ
async def require_admin(current_user: dict = Depends(get_current_session)):
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав доступа (требуются права администратора)"
        )
    return current_user

# ==========================================
# 7. МАРШРУТЫ ПРИЛОЖЕНИЯ (ENDPOINTS)
# ==========================================

# @app.post("/register", status_code=status.HTTP_201_CREATED)
# async def register(user: UserRegisterSchema, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(UserModel).where(UserModel.email == user.email))
#     if result.scalar_one_or_none():
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Пользователь с таким email уже существует"
#         )
    
#     salt = bcrypt.gensalt()
#     hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), salt)
    
#     new_user = UserModel(
#         name=user.name,
#         email=user.email,
#         password=hashed_password.decode('utf-8'),
#         tenant_id=user.tenant_id,
#         is_admin=False,
#         is_superadmin=False,
#         role_ids=[]
#     )
#     db.add(new_user)
#     try:
#         await db.commit()
#     except Exception:
#         await db.rollback()
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Ошибка создания. Убедитесь, что tenant_id существует в вашей БД."
#         )
    
#     return {"message": f"Пользователь {user.name} успешно зарегистрирован"}


# @app.post("/login")
# async def login(user: UserLoginSchema, response: Response, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(UserModel).where(UserModel.email == user.email))
#     db_user = result.scalar_one_or_none()
    
#     if not db_user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail=f"Неверный email или пароль"
#         )
    
#     stored_hash_bytes = db_user.password.encode('utf-8')
#     if not bcrypt.checkpw(user.password.encode('utf-8'), stored_hash_bytes):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail=f"Неверный email или пароль! email:{user.email}"
#         )
    
#     session_token = str(uuid.uuid4())
#     sessions_storage[session_token] = {
#         "user_id": str(db_user.id),
#         "name": db_user.name,
#         "email": db_user.email,
#         "tenant_id": str(db_user.tenant_id),
#         "is_admin": db_user.is_admin,
#         "is_superadmin": db_user.is_superadmin,
#         "role_ids": db_user.role_ids
#     }
    
#     response.set_cookie(
#         key="session_token",
#         value=session_token,
#         httponly=True,
#         samesite="lax"
#     )
#     return {"message": "Успешная авторизация"}


# @app.get("/user")
# # Используем нашу зависимость: код чистый, дублирования проверок больше нет
# async def get_user(current_user: dict = Depends(get_current_session)):
#     return {"status": "Доступ разрешен", "user": current_user}


# @app.get("/admin/dashboard")
# # Пример защищенного маршрута только для админов
# async def get_admin_dashboard(current_admin: dict = Depends(require_admin)):
#     return {"message": f"Добро пожаловать в админ-панель, {current_admin['name']}!"}


# @app.post("/logout")
# async def logout(response: Response, session_token: str | None = Cookie(default=None)):
#     if session_token and session_token in sessions_storage:
#         del sessions_storage[session_token]
        
#     response.delete_cookie(key="session_token", httponly=True, samesite="lax")
#     return {"message": "Вы успешно вышли из системы"}
