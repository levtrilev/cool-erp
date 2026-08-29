from logging.config import fileConfig
from sqlalchemy import pool #, engine_from_config
from alembic import context
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
# Импортируйте ваш Base и все модели
from app.core.database import Base
# Импортируем ВСЕ модели через __init__.py
from app.models import UserModel, UserSession # type: ignore


# Конфигурация Alembic
config = context.config

# Переопределяем URL базы данных из нашего config, если он не задан в alembic.ini
if config.config_file_name is not None:
    # Заменяем asyncpg на синхронный драйвер ТОЛЬКО для нужд Alembic (это самый надежный способ для autogenerate)
    # Или оставляем как есть, но используем async-обертку ниже. 
    # Оставим как есть, но настроим правильный async-запуск.
    pass

# Конфигурация Alembic
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Запуск миграций в 'офлайн' режиме (без подключения к БД, генерирует только SQL)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# def do_run_migrations(connection: Connection) -> None:
#     """Синхронная функция, которая будет вызвана внутри asyncio."""
#     context.configure(connection=connection, target_metadata=target_metadata)

#     with context.begin_transaction():
#         context.run_migrations()
def do_run_migrations(connection: Connection) -> None:
    """Синхронная функция, которая будет вызвана внутри asyncio."""
    
    # Функция фильтрации: игнорируем все таблицы, которых нет в нашем коде
    def include_object(object, name, type_, reflected, compare_to): # type: ignore
        # Если объект отражен из БД (reflected=True), но не в нашем коде — игнорируем
        if type_ == "table" and reflected:
            # Проверяем, есть ли эта таблица в Base.metadata
            if name not in Base.metadata.tables:
                return False  # Игнорируем эту таблицу
        return True  # Обрабатываем всё остальное
    
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,  # <-- ДОБАВЛЕНО: фильтр объектов # type: ignore
        compare_type=True,  # Опционально: сравнивать типы колонок
        compare_server_default=True,  # Опционально: сравнивать default значения
    )

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    """Асинхронный запуск миграций."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # КРИТИЧЕСКИ ВАЖНО: run_sync позволяет Alembic работать с асинхронным соединением
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Запуск миграций в 'онлайн' режиме."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()