"""FastAPI роутер для аутентификации и управления сессиями."""
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import delete

from app.core.auth.crud import crud_auth
from app.core.auth.dependencies import CurrentUser, DBSession
from app.core.auth.models import UserSession
from app.core.schemas import ApiResponse
from app.core.users.crud import crud_user
from app.core.users.schemas import UserLoginSchema, UserResponseSchema

router = APIRouter(prefix="/auth", tags=["Authentication"])

SESSION_LIFETIME_DAYS = 7


# ==================================================================
# АВТОРИЗАЦИЯ (ВХОД)
# ==================================================================
@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=ApiResponse[UserResponseSchema],
)
async def login(
    request: Request,
    user_in: UserLoginSchema,
    response: Response,
    db: DBSession,
) -> ApiResponse[UserResponseSchema]:
    """Авторизация пользователя с созданием сессии в БД и установкой cookie."""
    db_user = await crud_user.get_by_email(db, email=user_in.email)

    if not db_user or not crud_auth.authenticate(db_user, user_in.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    session_token = uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_LIFETIME_DAYS)

    new_session = UserSession(
        session_token=session_token,
        user_id=db_user.id,
        expires_at=expires_at,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:512],
    )

    db.add(new_session)
    await db.commit()

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=False,  # Для localhost. В продакшене должно быть True
        max_age=SESSION_LIFETIME_DAYS * 24 * 60 * 60,
        path="/",
    )

    return ApiResponse(
        success=True,
        message="Успешная авторизация",
        data=UserResponseSchema.model_validate(db_user),
    )


# ==================================================================
# ВЫХОД ИЗ СИСТЕМЫ
# ==================================================================
@router.post(
    "/logout",
    response_model=ApiResponse[dict[str, str]],  # ✅ Явные аргументы типов
)
async def logout(
    request: Request,
    response: Response,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[dict[str, str]]:  # ✅ Явные аргументы типов
    """Выход из системы: удаляет сессию из БД и очищает cookie."""
    session_token = request.cookies.get("session_token")

    if session_token:
        await db.execute(
            delete(UserSession).where(UserSession.session_token == session_token)
        )
        await db.commit()

    response.delete_cookie(
        key="session_token",
        path="/",
        samesite="lax",
    )

    return ApiResponse(
        success=True,
        message="Успешный выход",
        data={"status": "ok"},  # ✅ Непустой dict для строгой типизации
    )


# ==================================================================
# ПОЛУЧЕНИЕ ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ
# ==================================================================
@router.get(
    "/user",
    response_model=ApiResponse[UserResponseSchema],
)
async def get_current_user(
    current_user: CurrentUser,
) -> ApiResponse[UserResponseSchema]:
    """Получение профиля текущего пользователя на основе cookie сессии."""
    return ApiResponse(
        success=True,
        message="Пользователь успешно получен",
        data=UserResponseSchema.model_validate(current_user),
    )