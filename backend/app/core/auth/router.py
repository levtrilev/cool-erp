
"""FastAPI роутер для аутентификации и управления сессиями."""
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import delete

from app.core.audit.models import AccessAuditLog
from app.core.auth.crud import crud_auth
from app.core.auth.dependencies import CurrentUser, DBSession
from app.core.auth.models import UserSession
from app.core.schemas import ApiResponse
from app.core.users.crud import crud_user
from app.core.users.schemas import UserLoginSchema, UserResponseSchema

logger = logging.getLogger(__name__)

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
    """Авторизация пользователя с созданием сессии в БД и записью в аудит."""
    db_user = await crud_user.get_by_email(db, email=user_in.email)

    # ⚠️ Если crud_auth.authenticate не async, оставь без await. 
    # Если async — добавь await перед ним.
    if not db_user or not crud_auth.authenticate(db_user, user_in.password):
        # ✅ ЗАПИСЬ В АУДИТ: неудачная попытка login
        try:
            access_log = AccessAuditLog(
                id=uuid.uuid4(),
                tenant_id=uuid.UUID(int=0),
                user_id=None,
                action="access_denied",
                resource="auth",
                status="fail",
                ip_address=request.client.host if request.client else None,
            )
            db.add(access_log)
            await db.commit()
        except Exception as e:
            logger.warning(f"Could not write access_denied audit: {e}")

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

    # ✅ ЗАПИСЬ В АУДИТ: успешный login
    try:
        access_log = AccessAuditLog(
            id=uuid.uuid4(),
            tenant_id=db_user.tenant_id,
            user_id=db_user.id,
            action="login",
            resource="auth",
            status="success",
            ip_address=request.client.host if request.client else None,
        )
        db.add(access_log)
        await db.commit()
    except Exception as e:
        logger.warning(f"Could not write login audit: {e}")

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
    response_model=ApiResponse[dict[str, str]],
)
async def logout(
    request: Request,
    response: Response,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[dict[str, str]]:
    """Выход из системы: удаляет сессию из БД, очищает cookie и пишет в аудит."""
    session_token = request.cookies.get("session_token")

    # ✅ ЗАПИСЬ В АУДИТ: logout
    try:
        access_log = AccessAuditLog(
            id=uuid.uuid4(),
            tenant_id=session.tenant_id,
            user_id=session.id,
            action="logout",
            resource="auth",
            status="success",
            ip_address=request.client.host if request.client else None,
        )
        db.add(access_log)
        await db.commit()
    except Exception as e:
        logger.warning(f"Could not write logout audit: {e}")

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
        data={"status": "ok"},
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