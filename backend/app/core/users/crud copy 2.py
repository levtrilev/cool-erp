import uuid
import bcrypt
from typing import Optional, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.crud.base import CRUDBase
from app.core.users.models import UserModel
from app.core.users.schemas import UserRegisterSchema, UserUpdateSchema

# Глобальное хранилище сессий (в памяти: {session_id: {"user_id": UUID, ...}})
sessions_storage: dict[str, dict[str, Any]] = {}


class CRUDUser(CRUDBase[UserModel, UserRegisterSchema, UserUpdateSchema]):

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[UserModel]:
        """Проверка существования пользователя по email"""
        result = await db.execute(select(self.model).where(self.model.email == email))
        return result.scalar_one_or_none()

    # ✅ НОВЫЙ МЕТОД: пагинированный список с поддержкой target_tenant_id
    async def get_multi_paginated(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        search_field: str = "email",
        user_is_superadmin: bool = False,
        target_tenant_id: uuid.UUID | None = None,
    ) -> tuple[list[UserModel], int]:
        """
        Получение пагинированного списка пользователей.
        
        ✅ Правило №26: Жёсткая фильтрация по tenant_id на уровне SQL.
        
        Логика фильтрации:
        - Если передан target_tenant_id и пользователь — суперадмин,
          фильтрация идёт по target_tenant_id (пользователи другого предприятия).
        - Если пользователь НЕ суперадмин, фильтрация всегда по его собственному тенанту.
        """
        # ✅ Определяем фактический тенант для фильтрации
        effective_tenant = (
            target_tenant_id
            if (user_is_superadmin and target_tenant_id)
            else tenant_id
        )

        stmt = select(self.model)
        count_stmt = select(func.count()).select_from(self.model)

        # ✅ ВСЕГДА фильтруем по конкретному предприятию (даже для суперадмина,
        # если он запросил пользователей конкретной роли)
        stmt = stmt.where(self.model.tenant_id == effective_tenant)
        count_stmt = count_stmt.where(self.model.tenant_id == effective_tenant)

        if search:
            search_filter = (
                self.model.name.ilike(f"%{search}%")
                | self.model.email.ilike(f"%{search}%")
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        count_result = await db.execute(count_stmt)
        total = count_result.scalar_one()

        stmt = stmt.offset(skip).limit(limit).order_by(self.model.name)
        result = await db.execute(stmt)
        return list(result.scalars().all()), total

    async def register_new_user(
        self, db: AsyncSession, user_in: UserRegisterSchema
    ) -> UserModel:
        """Регистрация с авто-хешированием пароля и прямым сохранением в БД"""
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(user_in.password.encode("utf-8"), salt)
        db_obj = self.model(
            name=user_in.name,
            email=user_in.email,
            password=hashed_password.decode("utf-8"),
            tenant_id=user_in.tenant_id,
            is_admin=user_in.is_admin,
            is_superadmin=user_in.is_superadmin,
            role_ids=[],
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update_user(
        self, db: AsyncSession, db_user: UserModel, user_changes: UserUpdateSchema
    ) -> UserModel:
        """Обновление с авто-хешированием пароля и точечной очисткой сессий."""
        update_data = user_changes.model_dump(exclude_unset=True)

        if "password" in update_data and update_data["password"] is not None:
            salt = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(
                update_data["password"].encode("utf-8"), salt
            )
            update_data["password"] = hashed_password.decode("utf-8")
        else:
            update_data.pop("password", None)

        trigger_logout = False
        critical_fields = ["name", "email", "password"]
        for field in critical_fields:
            if field in update_data and update_data[field] != getattr(db_user, field):
                trigger_logout = True
                break

        if "role_ids" in update_data:
            update_data["role_names"] = await self._sync_role_names(
                db, db_user, update_data["role_ids"]
            )

        for field, value in update_data.items():
            setattr(db_user, field, value)

        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)

        if trigger_logout:
            self._clear_user_sessions(db_user.id)
        return db_user

    async def remove(self, db: AsyncSession, id: uuid.UUID) -> UserModel | None:
        """Удаление пользователя из БД и полная очистка его активных сессий."""
        user = await super().remove(db, id=id)
        if user:
            self._clear_user_sessions(user.id)
        return user

    def _clear_user_sessions(self, user_id: uuid.UUID) -> None:
        """Вспомогательный метод для удаления всех сессий пользователя из памяти."""
        for session_id, session_data in list(sessions_storage.items()):
            if session_data.get("user_id") == user_id:
                sessions_storage.pop(session_id, None)

    async def _sync_role_names(
        self,
        db: AsyncSession,
        user: UserModel,
        role_ids: list[uuid.UUID] | None,
    ) -> list[str] | None:
        """Синхронизирует role_names на основе role_ids."""
        if not role_ids:
            return None
        from app.core.roles.models import RoleModel

        stmt = select(RoleModel).where(RoleModel.id.in_(role_ids))
        result = await db.execute(stmt)
        roles = result.scalars().all()

        role_map = {r.id: r.name for r in roles}
        return [role_map.get(rid, "Неизвестная роль") for rid in role_ids]


# Экспортируем синглтон
crud_user = CRUDUser(UserModel)