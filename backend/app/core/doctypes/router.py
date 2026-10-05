import uuid
from typing import cast
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.schemas import ApiResponse, PaginatedResponse
from app.core.doctypes.crud import crud_doctype
from app.core.doctypes.schemas import (
    DoctypeCreateSchema,
    DoctypeUpdateSchema,
    DoctypeResponseSchema,
)

router = APIRouter(prefix="/doctypes", tags=["Doctypes"])


@router.get("/", response_model=ApiResponse[PaginatedResponse[DoctypeResponseSchema]])
async def get_doctypes(
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    items, total = await crud_doctype.get_multi_paginated(
        db, skip=skip, limit=limit, search=search, active_only=active_only
    )
    
    paginated_data = cast(
        PaginatedResponse[DoctypeResponseSchema],
        PaginatedResponse(
            items=[DoctypeResponseSchema.model_validate(item) for item in items],
            total=total,
            skip=skip,
            limit=limit,
        )
    )
    
    return ApiResponse(success=True, message="Document types retrieved", data=paginated_data)


@router.post("/", response_model=ApiResponse[DoctypeResponseSchema], status_code=201)
async def create_doctype(
    data: DoctypeCreateSchema,
    db: AsyncSession = Depends(get_db),
):
    doctype = await crud_doctype.create(db, obj_in=data)
    return ApiResponse(success=True, message="Document type created", data=DoctypeResponseSchema.model_validate(doctype))


@router.put("/{doctype_id}", response_model=ApiResponse[DoctypeResponseSchema])
async def update_doctype(
    doctype_id: uuid.UUID,
    data: DoctypeUpdateSchema,
    db: AsyncSession = Depends(get_db),
):
    db_obj = await crud_doctype.get(db, id=doctype_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Document type not found")
    
    updated_doctype = await crud_doctype.update(db, db_obj=db_obj, obj_in=data)
    return ApiResponse(success=True, message="Document type updated", data=DoctypeResponseSchema.model_validate(updated_doctype))


@router.delete("/{doctype_id}", response_model=ApiResponse[DoctypeResponseSchema])
async def delete_doctype(
    doctype_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    db_obj = await crud_doctype.get(db, id=doctype_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Document type not found")
    
    deleted_doctype = await crud_doctype.delete(db, id=doctype_id)
    return ApiResponse(success=True, message="Document type deleted", data=DoctypeResponseSchema.model_validate(deleted_doctype))
