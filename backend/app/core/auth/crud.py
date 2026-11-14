"""backend/app/core/auth/crud.py"""
import bcrypt
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crud.base import CRUDBase
from app.core.users.models import UserModel
from app.core.users.schemas import UserRegisterSchema, UserUpdateSchema

class CRUDAuth(CRUDBase[UserModel, UserRegisterSchema, UserUpdateSchema]):
    """CRUD для аутентификации.

    ⚠️ ПРАВИЛО №40 ч.8.1: CRUD НЕ управляет транзакцией — только flush().
    Транзакцией и аудитом владеет роутер (app/core/auth/router.py).
    """

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[UserModel]:
        """Проверка существования пользователя по email."""
        result = await db.execute(select(self.model).where(self.model.email == email))
        return result.scalar_one_or_none()

    def authenticate(self, db_user: Optional[UserModel], plain_password: str) -> bool:
        """Проверка пароля (bcrypt — синхронный, CPU-bound).

        ⚠️ ВАЖНО: метод СИНХРОННЫЙ (не async) — это правильно.
        bcrypt.checkpw — CPU-bound (~100ms). В async-эндпоинте его нужно
        вызывать через `await asyncio.to_thread(crud_auth.authenticate, ...)`,
        чтобы не блокировать event loop. См. `login` в auth/router.py.
        """
        if not db_user:
            return False
        stored_hash_bytes = db_user.password.encode("utf-8")
        return bcrypt.checkpw(plain_password.encode("utf-8"), stored_hash_bytes)

# Экспортируем синглтон
crud_auth = CRUDAuth(UserModel)