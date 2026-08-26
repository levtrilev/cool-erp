from contextlib import asynccontextmanager
from typing import Any
import bcrypt
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from app.core.config import settings
from app.core.database import async_session
from app.core.auth.models import UserModel
from app.core.auth.user_router import router as user_router
from app.core.auth.auth_router import router as auth_router


# Хранилище сессий в оперативной памяти сервера (токен -> метаданные)
sessions_storage: dict[str, Any] = {}

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://127.0.0.1:5173"
    ],  # Разрешаем запросы с нашего фронтенда
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем все методы (GET, POST, PUT, DELETE, OPTIONS)
    allow_headers=["*"],  # Разрешаем все заголовки (включая Content-Type)
)

app.include_router(user_router)
app.include_router(auth_router)


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
