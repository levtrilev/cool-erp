from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# ==========================================
# ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ POSTGRESQL
# ==========================================
engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

# Зависимость для инжекции сессии БД в эндпоинты
async def get_db():
    async with async_session() as session:
        yield session
