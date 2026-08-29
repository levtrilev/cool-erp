from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth.models import UserSession
from app.core.auth.models import UserModel as User

async def get_current_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Извлекает пользователя из сессии в куки."""

    session_token = request.cookies.get("session_token")
    if not session_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не авторизован",
        )

    result = await db.execute(
        select(UserSession).where(
            UserSession.session_token == session_token,
            UserSession.is_active == "1",
        )
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Сессия не найдена или отозвана",
        )

    if session.is_expired:
        await db.execute(
            delete(UserSession).where(UserSession.session_token == session_token)
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Сессия истекла. Войдите снова.",
        )

    user_result = await db.execute(select(User).where(User.id == session.user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
        )

    return user
