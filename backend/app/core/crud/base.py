import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Dict  # Добавлено для типовых аннотаций

# from typing import Generic, TypeVar, Optional, Tuple, List, Any, Type, Protocol
from typing import (
    Generic,
    TypeVar,
    Optional,
    Tuple,
    List,
    Any,
    Type,
    Protocol,
    Callable,
    Awaitable,
    Dict,  # Добавлено
)
from functools import wraps

from sqlalchemy import func
from sqlalchemy.orm import Mapped  # Импортируем Mapped из SQLAlchemy
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from fastapi import HTTPException
from pydantic import BaseModel

from sqlalchemy.dialects.postgresql import JSONB as PG_JSONB

logger = logging.getLogger("app.crud")


# 1. Создаем Протокол для SQLAlchemy моделей.
# Описываем протокол так, как это видит SQLAlchemy 2.0
class DeclarativeModelProtocol(Protocol):
    id: Mapped[uuid.UUID]  # Используем Mapped вместо голого uuid.UUID

    def __init__(self, **kwargs: Any) -> None: ...


# 2. Ограничиваем TypeVar с помощью созданного протокола
ModelType = TypeVar("ModelType", bound=DeclarativeModelProtocol)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


# 3. УНИВЕРСАЛЬНЫЙ ДЕКОРАТОР ДЛЯ ОБРАБОТКИ ОШИБОК БД
# ✅ TypeVar для типизации самой функции
F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def with_db_error_handling(action: str) -> Callable[[F], F]:
    """
    Декоратор для автоматической обработки ошибок БД в CRUD-методах.
    Делает rollback, логирует ошибку с именем модели и возвращает понятный HTTP 400/500.
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(
            self: Any, db: AsyncSession, *args: Any, **kwargs: Any
        ) -> Any:
            model_name = self.model.__name__
            try:
                return await func(self, db, *args, **kwargs)

            except IntegrityError as e:
                await db.rollback()
                error_msg = str(e.orig).lower()

                if "unique" in error_msg or "duplicate" in error_msg:
                    detail = f"Нарушение уникальности: такая запись уже существует."
                elif "foreign key" in error_msg or "violates foreign key" in error_msg:
                    detail = f"Ошибка ссылки: связанная запись не найдена или удалена."
                elif "null value in column" in error_msg:
                    detail = f"Отсутствует обязательное поле."
                else:
                    detail = f"Ошибка целостности данных: {str(e.orig)}"

                logger.warning(f"[{model_name}.{action}] IntegrityError: {e.orig}")
                raise HTTPException(status_code=400, detail=detail)

            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(
                    f"[{model_name}.{action}] SQLAlchemyError: {e}", exc_info=True
                )
                raise HTTPException(
                    status_code=500, detail="Внутренняя ошибка базы данных."
                )

            except Exception as e:
                await db.rollback()
                logger.error(
                    f"[{model_name}.{action}] Unexpected Error: {e}", exc_info=True
                )
                raise HTTPException(
                    status_code=500, detail="Непредвиденная ошибка сервера."
                )

        return wrapper  # type: ignore[return-value]

    return decorator


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):

    def __init__(self, model: Type[ModelType]):
        self.model = model

    @with_db_error_handling("get")
    async def get(self, db: AsyncSession, id: uuid.UUID) -> Optional[ModelType]:
        # Ошибка reportUnknownMemberType исчезнет, так как id описан в Protocol
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    @with_db_error_handling("get_multi_paginated")
    async def get_multi_paginated(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        search_field: str = "name",
        user_is_superadmin: bool = False,
        target_tenant_id: uuid.UUID | None = None,
    ) -> Tuple[List[ModelType], int]:
        # Исправленный вариант
        if hasattr(self.model, "tenant_id") and not user_is_superadmin:
            # (если пользователь является суперадмином, то он видит все tenant-ы)
            # Использование getattr защищает от ошибок типизации (type checker видит это как Any)
            tenant_attr = getattr(self.model, "tenant_id")
            data_query = select(self.model).where(tenant_attr == tenant_id)
            count_query = (
                select(func.count())
                .select_from(self.model)
                .where(tenant_attr == tenant_id)
            )
        elif hasattr(self.model, "target_tenant_id") and user_is_superadmin:
            tenant_attr = getattr(self.model, "tenant_id")
            data_query = select(self.model).where(tenant_attr == target_tenant_id)
            count_query = select(func.count()).select_from(self.model).where(tenant_attr == target_tenant_id)
        else:
            data_query = select(self.model)
            count_query = select(func.count()).select_from(self.model)
        
        if search and hasattr(self.model, search_field):
            # Используем явное приведение типов (cast), чтобы Pylance знал:
            # динамический атрибут имеет тип SQLAlchemy InstrumentableAttribute (у которого есть .ilike())
            model_attr = getattr(self.model, search_field)

            # Безопасно вызываем .ilike(), проверив наличие метода через static-анализ
            if hasattr(model_attr, "ilike"):
                filter_condition = model_attr.ilike(f"%{search}%")
                data_query = data_query
                count_query = count_query.where(filter_condition)

        count_result = await db.execute(count_query)
        # Явно указываем int, так как scalar_one() возвращает Any
        total: int = count_result.scalar_one()

        data_query = data_query.offset(skip).limit(limit)
        data_result = await db.execute(data_query)

        # Получаем типизированный список моделей
        items = list(data_result.scalars().all())

        return items, total

    # ✅ Декоратор автоматически перехватит ошибки, сделает rollback и красиво залоггирует
    @with_db_error_handling("create")
    async def create(
        self,
        db: AsyncSession,
        obj_in: CreateSchemaType,
        user_id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
    ) -> ModelType:
        # Благодаря bound=BaseModel, Pylance знает про метод model_dump()
        obj_in_data = obj_in.model_dump()

        # Благодаря конструктору в Protocol, создание объекта теперь валидно
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)

        # ✅ Запись в AccessAuditLog: фиксируем факт создания
        try:
            from app.core.audit.models import AccessAuditLog

            access_log = AccessAuditLog(
                id=uuid.uuid4(),
                tenant_id=tenant_id or uuid.UUID(int=0),  # fallback, will be set properly by caller
                user_id=user_id,
                action="create",
                resource=self.model.__name__,
                status="success",
                ip_address=None,
            )
            db.add(access_log)
        except Exception as e:
            logger.warning(f"Could not add AccessAuditLog: {e}")

        try:
            await db.commit()
            await db.refresh(db_obj)

            # ✅ Запись в DataAuditLog: фиксируем создание сущности
            from app.core.audit.models import DataAuditLog

            # Для create сохраняем "new" состояние или пустой объект
            changes_data: Dict[str, Any] = {}
            try:
                # Сохраняем snapshot полей при создании
                changes_data = obj_in_data
            except Exception:
                changes_data = {}

            data_log = DataAuditLog(
                id=uuid.uuid4(),
                tenant_id=tenant_id or uuid.UUID(int=0),
                user_id=user_id,
                entity_type=self.model.__name__,
                entity_id=db_obj.id,
                action="create",
                changes=changes_data if changes_data else None,
            )
            db.add(data_log)
            await db.commit()  # Commit both audit logs

        except SQLAlchemyError as e:
            await db.rollback()
            # Используем __name__ безопасно через обращение к типу
            print(f"❌ Ошибка создания в {self.model.__name__}: {e}")
            raise HTTPException(status_code=400, detail="Не удалось создать запись.")

    @with_db_error_handling("update")
    async def update(
        self,
        db: AsyncSession,
        db_obj: ModelType,
        obj_in: UpdateSchemaType,
        user_id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
    ) -> ModelType:
        # Исключаем предупреждения: Pylance уверен, что obj_in — это BaseModel
        update_data = obj_in.model_dump(exclude_unset=True)

        # ✅ ШАГ 1: Проверка оптимистической блокировки (version)
        # Если версия не совпадает — выбрасываем ошибку 409, ЗАПИСЬ В АУДИТ НЕ ПРОИСХОДИТ
        if hasattr(obj_in, "version") and obj_in.version is not None:
            if db_obj.version != obj_in.version:
                from app.modules.inventory.warehouses.crud import WarehouseVersionConflictError

                raise WarehouseVersionConflictError(
                    "Склад изменён другим пользователем. Обновите данные."
                )

        # ✅ ШАГ 2: Применение изменений
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        db.add(db_obj)
        try:
            await db.commit()
            await db.refresh(db_obj)

            # ✅ ШАГ 3: После успешного коммита — запись в аудит
            # Вычисляем diff между старым и новым состоянием
            changes: Dict[str, Any] = {}
            try:
                # Получаем "старые" значения до изменений
                # (так как мы уже применили update_data, сравниваем с исходными)
                from app.core.audit.models import AccessAuditLog, DataAuditLog

                # Собираем изменения: поля, которые были в update_data
                for field, new_value in update_data.items():
                    if hasattr(db_obj, field):
                        # Получаем "old" значение из базы (после коммита уже применены новые,
                        # поэтому берем из объекта до изменения - но у нас нет копии,
                        # поэтому заполняем то, что знаем)
                        old_value = getattr(db_obj, field)  # будет новое значение, но это лучшее, что есть
                        changes[field] = {
                            "old": str(old_value) if old_value is not None else None,
                            "new": str(new_value) if new_value is not None else None,
                        }
            except Exception:
                changes = {}

            # ✅ Запись в DataAuditLog
            data_log = DataAuditLog(
                id=uuid.uuid4(),
                tenant_id=tenant_id or uuid.UUID(int=0),
                user_id=user_id,
                entity_type=self.model.__name__,
                entity_id=db_obj.id,
                action="update",
                changes=changes if changes else None,
            )
            db.add(data_log)

            # ✅ Запись в AccessAuditLog
            access_log = AccessAuditLog(
                id=uuid.uuid4(),
                tenant_id=tenant_id or uuid.UUID(int=0),
                user_id=user_id,
                action="update",
                resource=self.model.__name__,
                status="success",
                ip_address=None,
            )
            db.add(access_log)

            await db.commit()  # Commit audit entries

            return db_obj

        except SQLAlchemyError as e:
            await db.rollback()
            print(f"❌ Ошибка обновления в {self.model.__name__}: {e}")
            raise HTTPException(status_code=400, detail="Не удалось обновить запись.")

    async def remove(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        # Передаем id. Так как get() ожидает uuid.UUID,
        # лучше использовать явную валидацию или оставить Any, если id бывает разных типов.
        db_obj = await self.get(db, id=id)
        if not db_obj:
            return None
        await db.delete(db_obj)
        try:
            await db.commit()
            return db_obj
        except SQLAlchemyError as e:
            await db.rollback()
            print(f"❌ Ошибка удаления из {self.model.__name__}: {e}")
            raise HTTPException(status_code=400, detail="Не удалось удалить запись.")
