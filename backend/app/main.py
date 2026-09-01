from contextlib import asynccontextmanager
from typing import Any
import bcrypt
# ✅ ЭТО ДОЛЖНО БЫТЬ В САМОМ ВЕРХУ, до создания app
# import app.core - это запустит __init__.py и импортирует все модели
import app.core # pyright: ignore[reportUnusedImport]
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from app.core.config import settings
from app.core.database import async_session
from app.core.users.models import UserModel
from app.core.users.router import router as user_router
from app.core.auth.router import router as auth_router
from app.core.tenant.router import router as tenant_router


# Хранилище сессий в оперативной памяти сервера (токен -> метаданные)
sessions_storage: dict[str, Any] = {}

# ==========================================
#  LIFESPAN (Жизненный цикл)
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

app = FastAPI(
    lifespan=lifespan,
)
# print("!!! УСПЕХ: FastAPI инициализирован с openapi_version=3.0.3 !!!")

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

# ==========================================
# РЕГИСТРАЦИЯ РОУТЕРОВ
# Версия API задаётся ТОЛЬКО здесь через prefix.
# Домены (core/user, inventory/product и т.д.) 
# НЕ знают о версиях.
# При создании v2: добавить router_v2.py в домене,
# неизменившиеся роутеры переиспользовать из v1.
# ==========================================
app.include_router(tenant_router)   #, prefix="/api/v1")
app.include_router(auth_router)     #, prefix="/api/v1")
app.include_router(user_router)     #, prefix="/api/v1")

