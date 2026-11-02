"""Роутер для чтения реплики регионов (для фронтенда).

Запись в реплику выполняется только репликатором.
Этот роутер предоставляет только чтение с фильтрацией
через AccessService.
"""
from typing import cast
import uuid

from fastapi import APIRouter, HTTPException

from app.core.auth.dependencies import DBSession, CurrentUser
from app.core.schemas import ApiResponse, PaginatedResponse
from app.modules.business_partners.regions_replica.crud import crud_sales_regions_replica
from app.modules.business_partners.regions_replica.schemas import (
    BpSalesRegionsReplicaResponseSchema,
)
from app.core.access.schemas import UserProtocol

router = APIRouter(
    prefix="/business-partners/regions-replica",
    tags=["Business Partners: regions-replica"],
)


@router.get(
    "/",
    response_model=ApiResponse[PaginatedResponse[BpSalesRegionsReplicaResponseSchema]],
)
async def list_regions_replica(
    db: DBSession,
    session: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
) -> ApiResponse[PaginatedResponse[BpSalesRegionsReplicaResponseSchema]]:
    """
    Список реплик регионов из домена sales.

    ✅ Фильтрация через AccessService.build_replica_access_filter:
    - Кросс-организационная видимость для раздела «Общий» (ТЗ §3.1.2.1)
    - Фильтрация по ролям и permissions (ТЗ §3.2, §3.4)
    - Тег-проверка на уровне SQL (ТЗ §6)
    """
    items, total = await crud_sales_regions_replica.get_multi(
        db,
        user=cast(UserProtocol, session),
        skip=skip,
        limit=limit,
        search=search,
    )
    return ApiResponse(
        success=True,
        message="Реплики регионов получены",
        data=PaginatedResponse(
            items=[
                BpSalesRegionsReplicaResponseSchema.model_validate(i)
                for i in items
            ],
            total=total,
            page=(skip // limit) + 1,
            size=limit,
        ),
    )


@router.get(
    "/{region_id}",
    response_model=ApiResponse[BpSalesRegionsReplicaResponseSchema],
)
async def get_region_replica(
    region_id: uuid.UUID,
    db: DBSession,
    session: CurrentUser,
) -> ApiResponse[BpSalesRegionsReplicaResponseSchema]:
    """Одна реплика региона по ID оригинала с проверкой доступа."""
    replica = await crud_sales_regions_replica.get_by_id(
        db,
        region_id=region_id,
        user=cast(UserProtocol, session),
    )
    if replica is None:
        raise HTTPException(status_code=404, detail="Регион не найден в реплике")
    return ApiResponse(
        success=True,
        message="Реплика региона получена",
        data=BpSalesRegionsReplicaResponseSchema.model_validate(replica),
    )