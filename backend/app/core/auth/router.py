"""FastAPI роутер для аутентификации и управления сессиями."""
import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import delete

from app.core.audit import service as audit_service
from app.core.auth.crud import crud_auth
from app.core.auth.dependencies import CurrentUser, DBSession
from app.core.auth.models import UserSession
from app.core.schemas import ApiResponse
from app.core.users.crud import crud_user
from app.core.users.schemas import (
    UserLoginSchema,
    UserResponseSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

SESSION_LIFETIME_DAYS = 7

# ⚠️ «Системный» тенант для аудита неудачных login:
# у пользователя ещё нет tenant_id, но AccessAuditLog.tenant_id — NOT NULL.
# uuid.UUID(int=0) — соглашение проекта (см. модели аудита).
_SYSTEM_TENANT_ID = uuid.UUID(int=0)


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
    client_ip = request.client.host if request.client else None
    db_user = await crud_user.get_by_email(db, email=user_in.email)

    # ✅ 1. Пользователь не найден — аудит + 401
    if db_user is None:
        try:
            await audit_service.log_access(
                db,
                tenant_id=_SYSTEM_TENANT_ID,
                user_id=None,
                action="access_denied",
                resource="auth",
                status="fail",
                ip_address=client_ip,
            )
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error(
                "Не удалось записать аудит неудачного login: %s",
                str(exc),
                exc_info=True,
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    # ✅ 2. db_user: UserModel — Pylance знает это после `if db_user is None: raise`
    #    bcrypt — CPU-bound (~100ms), выполняем в отдельном потоке.
    is_valid = await asyncio.to_thread(
        crud_auth.authenticate,
        db_user,
        user_in.password,
    )

    # ✅ 3. Пароль неверный — аудит + 401
    if not is_valid:
        try:
            await audit_service.log_access(
                db,
                tenant_id=db_user.tenant_id,   # ✅ теперь Pylance видит UserModel
                user_id=db_user.id,            # ✅ ok
                action="access_denied",
                resource="auth",
                status="fail",
                ip_address=client_ip,
            )
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error(
                "Не удалось записать аудит неудачного login: %s",
                str(exc),
                exc_info=True,
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    # ✅ 4. Успешный login: db_user: UserModel
    session_token = uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(days=SESSION_LIFETIME_DAYS)

    try:
        new_session = UserSession(
            session_token=session_token,
            user_id=db_user.id,           # ✅ ok
            expires_at=expires_at,
            ip_address=client_ip,
            user_agent=request.headers.get("user-agent", "")[:512],
        )
        db.add(new_session)

        await audit_service.log_access(
            db,
            tenant_id=db_user.tenant_id,  # ✅ ok
            user_id=db_user.id,           # ✅ ok
            action="login",
            resource="auth",
            status="success",
            ip_address=client_ip,
        )

        await db.commit()
        await db.refresh(new_session)
    except Exception as exc:
        await db.rollback()
        logger.error("Ошибка создания сессии: %s", str(exc), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка авторизации",
        ) from exc

    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=False,
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
    client_ip = request.client.host if request.client else None

    try:
        # ✅ Сначала delete, потом аудит — в ОДНОЙ транзакции.
        #    Если delete упадёт — аудит не запишется (rollback откатит всё).
        if session_token:
            await db.execute(
                delete(UserSession).where(UserSession.session_token == session_token)
            )

        await audit_service.log_access(
            db,
            tenant_id=session.tenant_id,
            user_id=session.id,
            action="logout",
            resource="auth",
            status="success",
            ip_address=client_ip,
        )

        await db.commit()          # ✅ ОДИН коммит: delete + audit
    except Exception as exc:
        await db.rollback()
        logger.error(
            "Ошибка logout для user %s: %s",
            session.id,
            str(exc),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка выхода из системы",
        ) from exc

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