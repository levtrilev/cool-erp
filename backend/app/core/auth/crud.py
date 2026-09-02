
import bcrypt
from typing import Optional, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.crud.base import CRUDBase
from app.core.users.models import UserModel
from app.core.users.schemas import UserRegisterSchema, UserUpdateSchema

# Глобальное хранилище сессий (в памяти: {session_id: {"user_id": UUID, ...}})
sessions_storage: dict[str, dict[str, Any]] = {}


class CRUDAuth(CRUDBase[UserModel, UserRegisterSchema, UserUpdateSchema]):

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[UserModel]:
        """Проверка существования пользователя по email"""
        result = await db.execute(select(self.model).where(self.model.email == email))
        return result.scalar_one_or_none()

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
