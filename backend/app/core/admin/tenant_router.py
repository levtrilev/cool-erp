from sqlalchemy import select
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import List

from app.core.database import get_db
from app.core.admin.tenant_crud import tenant_crud
from app.core.admin.schemas import TenantCreate, TenantUpdate, TenantResponse
# import traceback

from app.core.admin.models import Tenant

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post(
    "/", 
    response_model=TenantResponse, 
    status_code=status.HTTP_201_CREATED
)
async def create_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_db)
) :
    """Создать нового tenant"""
    return await tenant_crud.create(db, obj_in=tenant_data)

@router.get("/debug")
async def debug_tenants(db: AsyncSession = Depends(get_db)): # type: ignore
    """Временный эндпоинт для проверки БД"""
    try:
        result = await db.execute(select(Tenant))
        tenants = result.scalars().all() # type: ignore
        return {
            "status": "success",
            "count": len(tenants), # type: ignore
            "data": [{"id": str(t.id), "name": t.name, "active": t.active} for t in tenants] # type: ignore
        } # type: ignore
    except Exception as e:
        import traceback
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}

# @router.get("/", response_model=List[TenantResponse])
# async def get_tenants(
#     skip: int = 0,
#     limit: int = 100,
#     active_only: bool = False,
#     search: str | None = None,
#     db: AsyncSession = Depends(get_db)
# ) -> List[TenantResponse]:
#     # 🚨 ЭТОТ ПРИНТ ДОЛЖЕН ПОЯВИТЬСЯ В ТЕРМИНАЛЕ
#     print("\n" + "🚀"*20)
#     print("✅ МАРШРУТ GET /tenants/ УСПЕШНО ВЫПОЛНЯЕТСЯ!")
#     print("🚀"*20 + "\n")
    
#     # Временный возврат тестовых данных, чтобы проверить, работает ли сам маршрут
#     return [
#         TenantResponse(
#             id=uuid.uuid4(), 
#             name="Тестовая организация", 
#             active=True, 
#             description="Проверка маршрута"
#         )
#     ]

@router.get("/", response_model=List[TenantResponse])
async def get_tenants(
    skip: int = 0,
    limit: int = 100,
    active_only: bool = False,
    search: str | None = None,
    db: AsyncSession = Depends(get_db)
) :
    """Получить список tenants с пагинацией и поиском"""
    if active_only:
        if search:
            items, _ = await tenant_crud.get_multi_paginated_active(
                db, skip=skip, limit=limit, search=search
            )
            return items
        return await tenant_crud.get_multi_active(db, skip, limit)
    
    # Используем базовый метод с пагинацией
    items, _ = await tenant_crud.get_multi_paginated(
        db, skip=skip, limit=limit, search=search, search_field="name"
    )
    return items

# @router.get("/", response_model=List[TenantResponse])
# async def get_tenants(
#     skip: int = 0,
#     limit: int = 100,
#     active_only: bool = False,
#     search: str | None = None,
#     db: AsyncSession = Depends(get_db)
# ) -> List[Tenant]:
#     """Получить список tenants с пагинацией и поиском"""
#     try:
#         if active_only:
#             if search:
#                 items, _ = await tenant_crud.get_multi_paginated_active(
#                     db, skip=skip, limit=limit, search=search
#                 )
#                 return items
#             return await tenant_crud.get_multi_active(db, skip, limit)
        
#         # Используем базовый метод с пагинацией
#         items, _ = await tenant_crud.get_multi_paginated(
#             db, skip=skip, limit=limit, search=search, search_field="name"
#         )
#         return items
        
#     except Exception as e:
#         # 🚨 Печатаем полную ошибку в терминал бэкенда
#         print("\n" + "="*50)
#         print("❌ КРИТИЧЕСКАЯ ОШИБКА В GET /tenants/")
#         traceback.print_exc()
#         print("="*50 + "\n")
        
#         # Возвращаем текст ошибки в браузер (поможет увидеть её в Network -> Response)
#         from fastapi import HTTPException
#         raise HTTPException(status_code=500, detail=f"Ошибка сервера: {str(e)}")

@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
) :
    """Получить tenant по ID"""
    tenant = await tenant_crud.get(db, id=tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    tenant_data: TenantUpdate,
    db: AsyncSession = Depends(get_db)
) :
    """Обновить tenant"""
    tenant = await tenant_crud.get(db, id=tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return await tenant_crud.update(db, db_obj=tenant, obj_in=tenant_data)


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> None:
    """Удалить tenant"""
    result = await tenant_crud.remove(db, id=tenant_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
