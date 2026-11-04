# type: ignore

"""Фикстуры для автоматизированных тестов."""
import sys
import uuid
from pathlib import Path
from typing import AsyncGenerator

# Добавляем backend/ в sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text  # ✅ ДОБАВЛЕНО: text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.database import Base, get_db
from app.main import app

# Тестовая БД — ⚠️ ИЗМЕНИТЕ под вашу конфигурацию
TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:lev43856@localhost:5432/test_cool_erp"
)


# ==================================================================
# SESSION-SCOPED: создание таблиц один раз на всю сессию тестов
# ==================================================================
@pytest_asyncio.fixture(scope="session")
async def setup_database() -> AsyncGenerator[None, None]:
    """
    Создаёт таблицы один раз перед всеми тестами.
    После завершения всех тестов — удаляет таблицы.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.exec_driver_sql('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def engine(setup_database: None):
    """Общий engine для всей сессии тестов."""
    eng = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронная сессия для каждого теста.
    
    ✅ ИСПРАВЛЕНО: Убрано автоматическое управление транзакциями.
    Роутеры сами управляют commit/rollback.
    После теста делается rollback для очистки незакоммиченных изменений.
    """
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session
        # После теста откатываем любые незакоммиченные изменения
        await session.rollback()


@pytest_asyncio.fixture(autouse=True)
async def setup_test_data(db_session: AsyncSession):
    """Автоматически создаёт тестовые данные для каждого теста."""
    from app.core.sections.models import SectionModel, SectionType

    with db_session.no_autoflush:
        # 1. Создаём тестовые домены (только name, чтобы избежать ошибок схемы)
        domains = [
            ("business_partners", "Бизнес-партнёры"),
            ("inventory", "Склад"),
            ("sales", "Продажи"),
        ]

        domain_ids: dict[str, str] = {}
        for domain_key, domain_name in domains:
            result = await db_session.execute(
                text("SELECT id FROM public.domains WHERE name = :name"),
                {"name": domain_name},
            )
            row = result.scalar_one_or_none()

            if row is None:
                # ✅ ТОЛЬКО name. Никаких description или is_active
                insert_result = await db_session.execute(
                    text(
                        "INSERT INTO public.domains (name) "
                        "VALUES (:name) RETURNING id"
                    ),
                    {"name": domain_name},
                )
                domain_id: uuid.UUID = insert_result.scalar_one()
            else:
                domain_id: uuid.UUID = row

            domain_ids[domain_key] = str(domain_id)

        # 2. Создаём doctype с обязательным domain_id
        doctypes_data = [
            {
                "doctype": "bp_companies",
                "doctype_name": "Компании",
                "domain_id": domain_ids["business_partners"],
            },
            {
                "doctype": "inv_warehouses",
                "doctype_name": "Склады",
                "domain_id": domain_ids["inventory"],
            },
            {
                "doctype": "sales_goods",
                "doctype_name": "Товары",
                "domain_id": domain_ids["sales"],
            },
        ]

        for data in doctypes_data:
            result = await db_session.execute(
                text("SELECT id FROM public.doctypes WHERE doctype = :doctype"),
                {"doctype": data["doctype"]},
            )
            existing = result.scalar_one_or_none()

            if existing is None:
                await db_session.execute(
                    text(
                        "INSERT INTO public.doctypes "
                        "(domain_id, doctype, doctype_name, is_active) "
                        "VALUES (CAST(:domain_id AS uuid), :doctype, :doctype_name, true)"
                    ),
                    {
                        "domain_id": data["domain_id"],
                        "doctype": data["doctype"],
                        "doctype_name": data["doctype_name"],
                    },
                )

        # 3. Создаём платформенный раздел «Общий»
        result = await db_session.execute(
            text(
                "SELECT id FROM public.sections "
                "WHERE section_type = :section_type AND tenant_id IS NULL"
            ),
            {"section_type": SectionType.PLATFORM},
        )
        existing_platform = result.scalar_one_or_none()

        if existing_platform is None:
            platform = SectionModel(
                name="Общий",
                section_type=SectionType.PLATFORM,
                tenant_id=None,
                description="Платформенный общий раздел",
            )
            db_session.add(platform)

    await db_session.commit()
@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    HTTP-клиент с переопределённой зависимостью get_db.
    """

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def login_and_get_cookie(client: AsyncClient):
    """Вход в систему и получение cookies сессии."""

    async def _login(email: str, password: str) -> dict:
        response = await client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        assert response.status_code == 200, (
            f"Login failed for {email}: {response.status_code} {response.text}"
        )
        return dict(response.cookies)

    return _login