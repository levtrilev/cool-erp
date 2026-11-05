from logging.config import fileConfig
import asyncio

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Импортируем ваш Base
from app.core.database import Base

# Импортируем ВСЕ модели, чтобы Alembic их увидел
from app.core.auth.models import UserSession
from app.core.tenants.models import TenantModel
from app.core.users.models import UserModel
from app.core.audit.models import AccessAuditLog, DataAuditLog

# Импортируем модели доменов, разделов и других модулей
from app.core.doctypes.models import DoctypeModel
from app.core.domains.models import DomainModel
from app.core.sections.models import SectionModel
from app.core.events.models import CoreReplicationTaskModel
from app.core.notes.models import NotesModel
from app.core.permissions.models import PermissionModel
from app.core.roles.models import RoleModel

# Модули inventory и sales (только основные таблицы, без репликаций)
from app.modules.inventory.warehouses.models import InvWarehouseModel
from app.modules.sales.goods.models import SalesGoodsModel

# Конфигурация Alembic
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Запуск миграций в 'офлайн' режиме."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Синхронная функция, которая будет вызвана внутри asyncio."""
    
    # Функция фильтрации: игнорируем все таблицы, которых нет в нашем коде
    def include_object(object, name, type_, reflected, compare_to): # type: ignore
        if type_ == "table" and reflected:
            if name not in Base.metadata.tables:
                return False
        return True
    
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object, # type: ignore
        compare_type=True,
        compare_server_default=True,
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
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Запуск миграций в 'онлайн' режиме."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()