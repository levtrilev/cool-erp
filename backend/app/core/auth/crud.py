
import bcrypt
from typing import Optional, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.crud.base import CRUDBase
from app.core.user.models import UserModel
from app.core.user.schemas import UserRegisterSchema, UserUpdateSchema

# Глобальное хранилище сессий (в памяти: {session_id: {"user_id": UUID, ...}})
sessions_storage: dict[str, dict[str, Any]] = {}


class CRUDAuth(CRUDBase[UserModel, UserRegisterSchema, UserUpdateSchema]):

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[UserModel]:
        """Проверка существования пользователя по email"""
        result = await db.execute(select(self.model).where(self.model.email == email))
        return result.scalar_one_or_none()

    # async def register_new_user(
    #     self, db: AsyncSession, user_in: UserRegisterSchema
    # ) -> UserModel:
    #     """Регистрация с авто-хешированием пароля и прямым сохранением в БД"""
    #     salt = bcrypt.gensalt()
    #     hashed_password = bcrypt.hashpw(user_in.password.encode("utf-8"), salt)

    #     db_obj = self.model(
    #         name=user_in.name,
    #         email=user_in.email,
    #         password=hashed_password.decode("utf-8"),
    #         tenant_id=user_in.tenant_id,
    #         is_admin=False,
    #         is_superadmin=False,
    #         role_ids=[],
    #     )

    #     db.add(db_obj)
    #     await db.commit()
    #     await db.refresh(db_obj)

    #     return db_obj

    # async def update_user(
    #         self, db: AsyncSession, db_user: UserModel, user_changes: UserUpdateSchema
    #     ) -> UserModel:
    #         """Обновление с авто-хешированием пароля и точечной очисткой сессий."""
            
    #         # 1. Извлекаем данные из схемы в словарь, исключая неустановленные значения
    #         update_data = user_changes.model_dump(exclude_unset=True)

    #         # 2. Проверяем, передан ли пароль, и хешируем его только если он есть
    #         if "password" in update_data and update_data["password"] is not None:
    #             salt = bcrypt.gensalt()
    #             hashed_password = bcrypt.hashpw(update_data["password"].encode("utf-8"), salt)
    #             update_data["password"] = hashed_password.decode("utf-8")
    #         else:
    #             # Если пароль пришел как None или отсутствовал в запросе, удаляем поле из обновления
    #             update_data.pop("password", None)

    #         # ФЛАГ КРИТИЧЕСКИХ ИЗМЕНЕНИЙ: проверяем, меняются ли имя, email или пароль
    #         # Сравниваем новые значения с текущими значениями в db_user
    #         trigger_logout = False
    #         critical_fields = ["name", "email", "password"]
            
    #         for field in critical_fields:
    #             if field in update_data and update_data[field] != getattr(db_user, field):
    #                 trigger_logout = True
    #                 break

    #         # 3. Обновляем поля существующего объекта db_user динамически
    #         for field, value in update_data.items():
    #             setattr(db_user, field, value)

    #         # 4. Сохраняем изменения в базе данных
    #         db.add(db_user)
    #         await db.commit()
    #         await db.refresh(db_user)

    #         # 5. РАЗЛОГИН: удаляем сессии только при изменении критических данных
    #         if trigger_logout:
    #             self._clear_user_sessions(db_user.id)

    #         return db_user

    def authenticate(self, db_user: Optional[UserModel], plain_password: str) -> bool:
        """Проверка пароля пользователя"""
        if not db_user:
            return False
        stored_hash_bytes = db_user.password.encode("utf-8")
        return bcrypt.checkpw(plain_password.encode("utf-8"), stored_hash_bytes)

    # async def remove(self, db: AsyncSession, id: uuid.UUID) -> UserModel | None:
    #     """Удаление пользователя из БД и полная очистка его активных сессий."""
    #     # Вызываем базовый метод удаления из CRUDBase
    #     user = await super().remove(db, id=id)

    #     if user:
    #         # При успешном удалении пользователя стираем все его сессии
    #         self._clear_user_sessions(user.id)

    #     return user

    # def _clear_user_sessions(self, user_id: uuid.UUID) -> None:
        """Вспомогательный метод для удаления всех сессий пользователя из памяти."""
        for session_id, session_data in list(sessions_storage.items()):
            if session_data.get("user_id") == user_id:
                sessions_storage.pop(session_id, None)


# Экспортируем синглтон
crud_auth = CRUDAuth(UserModel)
