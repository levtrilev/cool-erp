from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from uuid import UUID
from typing import Optional
from datetime import datetime, timedelta

from app.core.database import get_db, async_session
from app.core.auth.dependencies import CurrentUser, get_db
from app.core.schemas import ApiResponse, PaginatedResponse
from app.core.audit.schemas import (
    AuditAccessRead,
    AuditDataRead,
    AuditFilter,
    AccessAuditCreate,
    DataAuditCreate,
)
from app.core.audit.models import AccessAuditLog, DataAuditLog
from app.core.users.models import UserModel as User
from fastapi.responses import StreamingResponse
from io import StringIO
import csv


# Создаем роутер для аудита
router = APIRouter(prefix="/api/v1/audit", tags=["Audit: access logs"])


async def _apply_tenant_filter(
    statement,
    tenant_id: UUID,
    is_superadmin: bool,
):
    """Применять фильтрацию tenant_id только если пользователь НЕ суперадмин."""
    if not is_superadmin:
        statement = statement.where(AccessAuditLog.tenant_id == tenant_id)  # type: ignore
    return statement


@router.get(
    "/access",
    response_model=ApiResponse[PaginatedResponse[AuditAccessRead]],
)
async def list_access_audit(
    session: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaginatedResponse[AuditAccessRead]]:
    """Возвращает список логов доступа (только для супер-админа или админа тенанта)."""

    from app.core.users.models import UserModel as User

    is_superadmin = session.is_superadmin
    tenant_id = session.tenant_id

    # Базовый запрос для подсчета (без JOIN, чтобы не размножал строки)
    if not is_superadmin:
        count_stmt = select(func.count()).select_from(AccessAuditLog).where(AccessAuditLog.tenant_id == tenant_id)  # type: ignore
    else:
        count_stmt = select(func.count()).select_from(AccessAuditLog)  # type: ignore

    # Считаем общее количество
    count_result = await db.execute(count_stmt)
    total: int = count_result.scalar() or 0

    # Запрос с пагинацией и LEFT JOIN для получения email
    # Используем LEFT JOIN, чтобы записи с user_id=None не пропадали
    from sqlalchemy import outerjoin

    join_stmt = outerjoin(AccessAuditLog, User, AccessAuditLog.user_id == User.id)

    # Фильтр tenant_id применять только если НЕ суперадмин
    if not is_superadmin:
        base_stmt = select(AccessAuditLog).select_from(join_stmt).where(AccessAuditLog.tenant_id == tenant_id).order_by(AccessAuditLog.created_at.desc()).offset(skip).limit(limit)
    else:
        base_stmt = select(AccessAuditLog).select_from(join_stmt).order_by(AccessAuditLog.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(base_stmt)
    items = result.scalars().all()

    # Собираем данные для маппинга user_id -> email
    user_ids: list[UUID | None] = [item.user_id for item in items]
    unique_user_ids = list(set(uid for uid in user_ids if uid is not None))

    # Получаем email для всех уникальных user_id
    user_emails: dict[UUID, str] = {}
    if unique_user_ids:
        user_stmt = select(User.id, User.email).where(User.id.in_(unique_user_ids))
        user_result = await db.execute(user_stmt)
        for uid, email in user_result.all():
            user_emails[uid] = email

    # Конвертируем в Pydantic схемы
    audit_items = [
        AuditAccessRead(
            id=item.id,
            tenant_id=item.tenant_id,
            user_id=item.user_id,
            user_email=user_emails.get(item.user_id) if item.user_id else None,
            action=item.action,
            resource=item.resource,
            status=item.status,
            ip_address=item.ip_address,
            created_at=item.created_at,
        )
        for item in items
    ]

    paginated = PaginatedResponse(
        items=audit_items,
        total=total,
        page=(skip // limit) + 1,
        size=limit,
    )

    return ApiResponse(
        success=True,
        message="Логи доступа получены",
        data=paginated,
    )


@router.get(
    "/data",
    response_model=ApiResponse[PaginatedResponse[AuditDataRead]],
)
async def list_data_audit(
    session: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    user_email: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[PaginatedResponse[AuditDataRead]]:
    """Возвращает список изменений данных (с пагинацией)."""

    from app.core.users.models import UserModel as User

    is_superadmin = session.is_superadmin
    tenant_id = session.tenant_id

    # Базовый запрос для подсчета
    if not is_superadmin:
        filter_conditions = [DataAuditLog.tenant_id == tenant_id]  # type: ignore
    else:
        filter_conditions = []

    if entity_type:
        filter_conditions.append(DataAuditLog.entity_type == entity_type)  # type: ignore
    if entity_id:
        filter_conditions.append(DataAuditLog.entity_id == entity_id)  # type: ignore
    if action:
        filter_conditions.append(DataAuditLog.action == action)  # type: ignore
    if user_email:
        filter_conditions.append(User.email.ilike(f"%{user_email}%"))
    if start_date:
        filter_conditions.append(DataAuditLog.created_at >= start_date)
    if end_date:
        end_date_inclusive = end_date + timedelta(days=1)
        filter_conditions.append(DataAuditLog.created_at < end_date_inclusive)

    count_stmt = select(func.count()).select_from(DataAuditLog).where(and_(*filter_conditions))  # type: ignore
    count_result = await db.execute(count_stmt)
    total: int = count_result.scalar() or 0

    # Запрос с пагинацией и LEFT JOIN
    from sqlalchemy import outerjoin
    join_stmt = outerjoin(DataAuditLog, User, DataAuditLog.user_id == User.id)

    # ВАЖНО: Если фильтруем по user_email, нужно использовать select(DataAuditLog) с join_stmt
    base_stmt = (
        select(DataAuditLog)
        .select_from(join_stmt)
        .where(and_(*filter_conditions))
        .order_by(DataAuditLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(base_stmt)
    items = result.scalars().all()

    # Маппинг user_id -> email
    user_ids: list[UUID | None] = [item.user_id for item in items]
    unique_user_ids = list(set(uid for uid in user_ids if uid is not None))
    user_emails: dict[UUID, str] = {}
    if unique_user_ids:
        user_stmt = select(User.id, User.email).where(User.id.in_(unique_user_ids))
        user_result = await db.execute(user_stmt)
        for uid, email in user_result.all():
            user_emails[uid] = email

    # Конвертация в Pydantic
    audit_items = [
        AuditDataRead(
            id=item.id,
            tenant_id=item.tenant_id,
            user_id=item.user_id,
            user_email=user_emails.get(item.user_id) if item.user_id else None,
            entity_type=item.entity_type,
            entity_id=item.entity_id,
            entity_name=item.entity_name,
            action=item.action,
            changes=item.changes if item.changes else None,
            created_at=item.created_at,
        )
        for item in items
    ]

    paginated = PaginatedResponse(
        items=audit_items,
        total=total,
        page=(skip // limit) + 1,
        size=limit,
    )

    return ApiResponse(
        success=True,
        message="Данные аудита получены",
        data=paginated,
    )


@router.get(
    "/export",
    response_class=StreamingResponse,
)
async def export_data_audit(
    session: CurrentUser,
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    user_email: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    """Экспорт всех изменений данных в CSV."""
    from app.core.users.models import UserModel as User

    is_superadmin = session.is_superadmin
    tenant_id = session.tenant_id

    if not is_superadmin:
        filter_conditions = [DataAuditLog.tenant_id == tenant_id]  # type: ignore
    else:
        filter_conditions = []

    if entity_type:
        filter_conditions.append(DataAuditLog.entity_type == entity_type)  # type: ignore
    if entity_id:
        filter_conditions.append(DataAuditLog.entity_id == entity_id)  # type: ignore
    if action:
        filter_conditions.append(DataAuditLog.action == action)  # type: ignore
    if user_email:
        filter_conditions.append(User.email.ilike(f"%{user_email}%"))
    if start_date:
        filter_conditions.append(DataAuditLog.created_at >= start_date)
    if end_date:
        end_date_inclusive = end_date + timedelta(days=1)
        filter_conditions.append(DataAuditLog.created_at < end_date_inclusive)

    from sqlalchemy import outerjoin
    join_stmt = outerjoin(DataAuditLog, User, DataAuditLog.user_id == User.id)
    base_stmt = select(DataAuditLog).select_from(join_stmt).where(and_(*filter_conditions)).order_by(DataAuditLog.created_at.desc())

    result = await db.execute(base_stmt)
    items = result.scalars().all()

    # Получаем email для всех уникальных user_id
    user_ids: list[UUID | None] = [item.user_id for item in items]
    unique_user_ids = list(set(uid for uid in user_ids if uid is not None))
    user_emails: dict[UUID, str] = {}
    if unique_user_ids:
        user_stmt = select(User.id, User.email).where(User.id.in_(unique_user_ids))
        user_result = await db.execute(user_stmt)
        for uid, email in user_result.all():
            user_emails[uid] = email

    # Создаем CSV
    output = StringIO()
    output.write('\ufeff')  # BOM
    writer = csv.writer(output, delimiter=';')

    writer.writerow(['Дата', 'Пользователь', 'Сущность', 'Действие', 'Изменения'])

    for item in items:
        entity = f"{item.entity_type}: {item.entity_name}" if item.entity_name else f"{item.entity_type}: {item.entity_id}"
        
        # Безопасное формирование изменений (проверяем, что это словарь)
        changes_str = ""
        if item.changes and isinstance(item.changes, dict):
            changes_list = []
            for field, val in item.changes.items():
                if isinstance(val, dict):
                    old_val = val.get('old', '—')
                    new_val = val.get('new', '—')
                    changes_list.append(f"{field}: {old_val} → {new_val}")
                else:
                    changes_list.append(f"{field}: {val}")
            changes_str = "\n".join(changes_list)
        elif item.changes:
            changes_str = str(item.changes)

        writer.writerow([
            item.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            user_emails.get(item.user_id, 'Система'),
            entity,
            item.action,
            changes_str,
        ])

    output.seek(0)
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=audit.csv",
            "Content-Type": "text/csv; charset=utf-8",
        }
    )