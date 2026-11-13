# """
# Главный модуль FastAPI-приложения Cool ERP.
# Точка входа: uvicorn app.main:app --reload
# """
# import asyncio
# from contextlib import asynccontextmanager
# from typing import Any

# import bcrypt
# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.openapi.utils import get_openapi
# from sqlalchemy import select

# # ============================================================
# # ИМПОРТ МОДЕЛЕЙ И ОБРАБОТЧИКОВ РЕПЛИКАЦИИ
# # ============================================================
# # ✅ Импортируем ядро — запускает __init__.py и регистрирует все модели
# import app.core  # pyright: ignore[reportUnusedImport]

# # ✅ Импорт обработчиков репликации для регистрации (побочный эффект)
# # import app.operations.replica.handlers  # noqa: F401
# # import app.sales.replica.handlers  # noqa: F401
# # import app.business_partners.replica.handlers  # noqa: F401

# # ============================================================
# # ИМПОРТ РОУТЕРОВ
# # ============================================================
# from app.core.auth.router import router as auth_router
# from app.core.audit.router import router as audit_router
# from app.core.config import settings
# from app.core.database import async_session
# from app.core.doctypes.router import router as doctype_router
# from app.core.domains.router import router as domain_router
# from app.core.events.replicator import replicator
# from app.core.notes.router import router as notes_router
# from app.core.permissions.router import router as permission_router
# from app.core.roles.router import router as role_router
# from app.core.sections.router import router as section_router
# from app.core.tenants.router import router as tenant_router
# from app.core.users.models import UserModel
# from app.core.users.router import router as user_router
# from app.modules import register_all_replication_handlers
# from app.modules.business_partners.companies.router import (
#     router as companies_router,
# )
# from app.modules.business_partners.regions_replica.router import (
#     router as bp_regions_replica_router,
# )
# from app.modules.inventory.warehouses.router import (
#     router as warehouses_router,
# )
# from app.modules.sales.goods.router import router as goods_router
# from app.modules.sales.regions.router import router as regions_router

# # ============================================================
# # РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ РЕПЛИКАЦИИ
# # ============================================================
# register_all_replication_handlers()


# # ============================================================
# # LIFESPAN (жизненный цикл приложения)
# # ============================================================
# @asynccontextmanager
# async def lifespan(app: FastAPI):  # noqa: ARG001
#     """
#     При старте: создаёт суперадмина (если отсутствует), запускает репликатор.
#     При остановке: отменяет задачу репликатора.
#     """
#     # Создание суперадмина по умолчанию
#     async with async_session() as session:
#         result = await session.execute(
#             select(UserModel).where(
#                 UserModel.email == "superadmin@yandex.ru"
#             )
#         )
#         if not result.scalar_one_or_none():
#             salt = bcrypt.gensalt()
#             hashed_admin_pass = bcrypt.hashpw(
#                 settings.SUPERADMIN_PASSWORD.encode("utf-8"), salt
#             )
#             admin_user = UserModel(
#                 name="superadmin@yandex.ru",
#                 email="superadmin@yandex.ru",
#                 password=hashed_admin_pass.decode("utf-8"),
#                 is_admin=True,
#                 is_superadmin=True,
#                 tenant_id=settings.SUPERADMIN_TENANT_ID,
#                 role_ids=[],
#             )
#             session.add(admin_user)
#             await session.commit()

#     # Запуск фонового процесса репликации
#     replicator_task = asyncio.create_task(replicator.run())
#     try:
#         yield
#     finally:
#         replicator_task.cancel()
#         try:
#             await replicator_task
#         except asyncio.CancelledError:
#             pass


# # ============================================================
# # ИНИЦИАЛИЗАЦИЯ FASTAPI
# # ============================================================
# app = FastAPI(title="Cool ERP", lifespan=lifespan)


# # ============================================================
# # CORS
# # ============================================================
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "http://localhost:5173",
#         "http://127.0.0.1:5173",
#         "http://localhost:3000",
#         "http://127.0.0.1:8000",
#         "http://localhost:8000",
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
#     expose_headers=["Content-Disposition"],
# )


# # ============================================================
# # КАСТОМНАЯ ГЕНЕРАЦИЯ OPENAPI-СХЕМЫ
# # ============================================================
# # Убирает responses: 422 (HTTPValidationError) из всех эндпоинтов.
# #
# # Обоснование: 422 на фронтенд приходит как AxiosError-исключение
# # (customInstance выбрасывает его), а не как часть возвращаемых
# # данных. Orval 8.x иначе включает HTTPValidationError в union
# # возвращаемого типа, что ломает TypeScript-типизацию (340 ошибок).
# # ============================================================
# def custom_openapi() -> dict[str, Any]:
#     """Кастомная генерация OpenAPI без HTTPValidationError."""
#     if app.openapi_schema:
#         return app.openapi_schema

#     # ✅ Явная аннотация типа — Pyright strict не может вывести
#     # тип из get_openapi() (возвращает Unknown | dict[str, Any] | None)
#     openapi_schema: dict[str, Any] = get_openapi(
#         title=app.title,
#         version=app.version or "1.0.0",
#         routes=app.routes,
#     )

#     # Удаляем 422 responses из всех paths и методов
#     for path_item in openapi_schema.get("paths", {}).values():
#         for method in path_item.values():
#             if not isinstance(method, dict):
#                 continue
#             responses = method.get("responses", {})
#             if "422" in responses:
#                 del responses["422"]

#     # Удаляем саму схему HTTPValidationError из components
#     schemas = openapi_schema.get("components", {}).get("schemas", {})
#     schemas.pop("HTTPValidationError", None)
#     schemas.pop("ValidationError", None)

#     # ✅ setattr вместо # type: ignore (Правило №44)
#     # FastAPI.openapi_schema имеет тип OpenAPI | None,
#     # setattr обходит проверку без # type: ignore
#     setattr(app, "openapi_schema", openapi_schema)
#     return openapi_schema


# # ✅ setattr вместо # type: ignore (Правило №44)
# # FastAPI.openapi имеет тип Callable с конкретной сигнатурой,
# # setattr обходит проверку без # type: ignore
# setattr(app, "openapi", custom_openapi)


# # ============================================================
# # РЕГИСТРАЦИЯ РОУТЕРОВ
# # ============================================================
# app.include_router(auth_router)
# app.include_router(audit_router)
# app.include_router(tenant_router)
# app.include_router(user_router)
# app.include_router(section_router)
# app.include_router(role_router)
# app.include_router(permission_router)
# app.include_router(domain_router)
# app.include_router(doctype_router)
# app.include_router(notes_router)
# app.include_router(warehouses_router)
# app.include_router(goods_router)
# app.include_router(companies_router)
# app.include_router(regions_router)
# app.include_router(bp_regions_replica_router)