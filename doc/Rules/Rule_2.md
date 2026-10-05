# Правило №2: Полный CRUD

Каждый новый CRUD-класс **ОБЯЗАТЕЛЬНО** должен реализовывать полный набор методов для работы с сущностью. Это обеспечивает единообразие архитектуры, предсказуемость API и упрощает поддержку кода.

**ОБЯЗАТЕЛЬНЫЙ НАБОР МЕТОДОВ:**
* `create` — создание записи
* `get` — получение одной записи по ID
* `get_by_*` — получение по уникальным полям (например, `get_by_name`, `get_by_email`)
* `get_multi` — получение списка с поиском и фильтрами
* `get_multi_paginated` — получение списка с пагинацией (возвращает `tuple[list[Model], int]`)
* `update` — обновление записи
* `delete` — удаление записи (с защитой от удаления, если есть связанные записи)

---

### 1. Обоснование (Почему это важно)

1. **Единообразие API:** Когда все домены (`users`, `roles`, `tenants`, `permissions`) имеют одинаковый набор CRUD-методов, разработчик мгновенно понимает, как работать с любой сущностью. Не нужно каждый раз изучать новый API.
2. **Предсказуемость фронтенда:** Orval генерирует хуки на основе эндпоинтов. Если CRUD-класс реализует полный набор, фронтенд автоматически получает типобезопасные методы для всех операций.
3. **Упрощение рефакторинга:** При добавлении новой сущности (например, `invoices`) разработчик просто копирует структуру существующего CRUD-класса, гарантируя, что ничего не упущено.
4. **Защита от "дыр":** Если CRUD-класс не реализует, например, метод `delete`, разработчик может случайно написать SQL-запрос напрямую в роутере, обойдя проверки безопасности (Правило №26).
5. **Тестируемость:** Единый контракт CRUD-класса упрощает написание unit-тестов — можно создать базовый тестовый класс и наследовать его для всех сущностей.
6. **Соответствие REST:** Полный CRUD-класс естественным образом маппится на REST-операции: `POST` → `create`, `GET /{id}` → `get`, `GET /` → `get_multi`, `PUT` → `update`, `DELETE` → `delete`.

---

### 2. Обязательные требования к реализации

#### 2.1. Базовая сигнатура методов
Все методы **ОБЯЗАТЕЛЬНО** должны принимать контекст безопасности:
* `db: AsyncSession` — сессия базы данных
* `current_tenant_id: uuid.UUID` — ID организации текущего пользователя
* `is_superadmin: bool = False` — флаг суперадмина

#### 2.2. Защита от удаления связанных записей
Метод `delete` **ОБЯЗАТЕЛЬНО** должен проверять наличие связанных записей перед удалением. Если связи существуют, удаление блокируется с понятным сообщением об ошибке.

#### 2.3. Поддержка поиска и пагинации
Метод `get_multi` **ОБЯЗАТЕЛЬНО** должен поддерживать:
* Поиск по текстовым полям (`search`)
* Фильтрацию по статусам и другим полям
* Сортировку (опционально)

Метод `get_multi_paginated` **ОБЯЗАТЕЛЬНО** возвращает кортеж `(items, total)`, где `total` — общее количество записей для пагинации.

#### 2.4. Консистентность с Pydantic-схемами
Каждый метод CRUD должен работать с соответствующей Pydantic-схемой (Правило №21):
* `create` принимает `XxxCreateSchema`
* `update` принимает `XxxUpdateSchema`
* Все методы возвращают ORM-модель, которая затем конвертируется в `XxxResponseSchema` через `.model_validate()` (Правило №4)

---

### 3. Примеры кода

#### ✅ ПРАВИЛЬНО: Полный CRUD-класс

```python
# backend/app/core/roles/crud.py
import uuid
from typing import Optional
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.core.roles.models import RoleModel
from app.core.roles.schemas import RoleCreateSchema, RoleUpdateSchema
from app.core.permissions.models import PermissionModel


class CRUDRole:
    def __init__(self, model):
        self.model = model

    # ✅ 1. CREATE
    async def create(
        self,
        db: AsyncSession,
        data: RoleCreateSchema,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> RoleModel:
        # Проверка уникальности имени в рамках тенанта
        existing = await self.get_by_name(db, data.name, current_tenant_id, is_superadmin)
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Роль с именем '{data.name}' уже существует"
            )
        
        db_obj = self.model(
            **data.model_dump(exclude={'tenant_id'}),
            tenant_id=current_tenant_id,  # ✅ Правило №26: tenant_id из сессии
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    # ✅ 2. GET (по ID)
    async def get(
        self,
        db: AsyncSession,
        item_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> Optional[RoleModel]:
        stmt = select(self.model).where(self.model.id == item_id)
        
        # ✅ Правило №26: фильтрация по tenant_id
        if not is_superadmin:
            stmt = stmt.where(self.model.tenant_id == current_tenant_id)
        
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ✅ 3. GET_BY_* (по уникальным полям)
    async def get_by_name(
        self,
        db: AsyncSession,
        name: str,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> Optional[RoleModel]:
        stmt = select(self.model).where(self.model.name == name)
        
        if not is_superadmin:
            stmt = stmt.where(self.model.tenant_id == current_tenant_id)
        
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    # ✅ 4. GET_MULTI (список с поиском)
    async def get_multi(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        current_tenant_id: Optional[uuid.UUID] = None,
        is_superadmin: bool = False,
    ) -> list[RoleModel]:
        stmt = select(self.model)
        
        if not is_superadmin and current_tenant_id:
            stmt = stmt.where(self.model.tenant_id == current_tenant_id)
        
        if search:
            stmt = stmt.where(self.model.name.ilike(f"%{search}%"))
        
        stmt = stmt.offset(skip).limit(limit).order_by(self.model.name)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    # ✅ 5. GET_MULTI_PAGINATED (список с пагинацией и total)
    async def get_multi_paginated(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
        current_tenant_id: Optional[uuid.UUID] = None,
        is_superadmin: bool = False,
    ) -> tuple[list[RoleModel], int]:
        # Базовый запрос для данных
        stmt = select(self.model)
        count_stmt = select(func.count()).select_from(self.model)
        
        # Применяем фильтры
        if not is_superadmin and current_tenant_id:
            stmt = stmt.where(self.model.tenant_id == current_tenant_id)
            count_stmt = count_stmt.where(self.model.tenant_id == current_tenant_id)
        
        if search:
            search_filter = self.model.name.ilike(f"%{search}%")
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)
        
        # Получаем общее количество
        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one()
        
        # Получаем данные с пагинацией
        stmt = stmt.offset(skip).limit(limit).order_by(self.model.name)
        result = await db.execute(stmt)
        
        return list(result.scalars().all()), total

    # ✅ 6. UPDATE
    async def update(
        self,
        db: AsyncSession,
        item_id: uuid.UUID,
        data: RoleUpdateSchema,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> RoleModel:
        db_obj = await self.get(db, item_id, current_tenant_id, is_superadmin)
        
        if not db_obj:
            raise HTTPException(status_code=404, detail="Роль не найдена")
        
        # Проверка уникальности имени (если оно меняется)
        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data and update_data["name"] != db_obj.name:
            existing = await self.get_by_name(
                db, update_data["name"], current_tenant_id, is_superadmin
            )
            if existing and existing.id != item_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Роль с именем '{update_data['name']}' уже существует"
                )
        
        for key, value in update_data.items():
            setattr(db_obj, key, value)
        
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    # ✅ 7. DELETE (с защитой от удаления связанных записей)
    async def delete(
        self,
        db: AsyncSession,
        item_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> RoleModel:
        db_obj = await self.get(db, item_id, current_tenant_id, is_superadmin)
        
        if not db_obj:
            raise HTTPException(status_code=404, detail="Роль не найдена")
        
        # ✅ Проверка наличия связанных записей
        permissions_count_stmt = (
            select(func.count())
            .select_from(PermissionModel)
            .where(PermissionModel.role_id == item_id)
        )
        result = await db.execute(permissions_count_stmt)
        permissions_count = result.scalar_one()
        
        if permissions_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Невозможно удалить роль: существует {permissions_count} связанных полномочий. "
                       "Сначала удалите или переназначьте полномочия."
            )
        
        # Удаляем запись
        await db.delete(db_obj)
        await db.commit()
        return db_obj


# ✅ Экземпляр CRUD с именем сущности
crud_role = CRUDRole(RoleModel)
```

#### ✅ ПРАВИЛЬНО: Использование CRUD в роутере

```python
# backend/app/core/roles/router.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import cast

from app.core.database import get_db
from app.core.auth.dependencies import get_current_session
from app.core.roles.crud import crud_role
from app.core.roles.schemas import (
    RoleCreateSchema,
    RoleUpdateSchema,
    RoleResponseSchema,
)
from app.core.schemas import ApiResponse, PaginatedResponse

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/", response_model=ApiResponse[PaginatedResponse[RoleResponseSchema]])
async def get_roles(
    skip: int = 0,
    limit: int = 10,
    search: str | None = None,
    current_session=Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    # ✅ Используем get_multi_paginated
    items, total = await crud_role.get_multi_paginated(
        db,
        skip=skip,
        limit=limit,
        search=search,
        current_tenant_id=current_session.tenant_id,
        is_superadmin=current_session.is_superadmin,
    )
    
    paginated_data = cast(
        PaginatedResponse[RoleResponseSchema],
        PaginatedResponse(
            items=[RoleResponseSchema.model_validate(item) for item in items],
            total=total,
            skip=skip,
            limit=limit,
        )
    )
    
    return ApiResponse(
        success=True,
        message="Роли получены",
        data=paginated_data,
    )


@router.get("/{role_id}", response_model=ApiResponse[RoleResponseSchema])
async def get_role(
    role_id: uuid.UUID,
    current_session=Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    # ✅ Используем get
    role = await crud_role.get(
        db,
        item_id=role_id,
        current_tenant_id=current_session.tenant_id,
        is_superadmin=current_session.is_superadmin,
    )
    
    if not role:
        raise HTTPException(status_code=404, detail="Роль не найдена")
    
    return ApiResponse(
        success=True,
        message="Роль получена",
        data=RoleResponseSchema.model_validate(role),
    )


@router.post("/", response_model=ApiResponse[RoleResponseSchema], status_code=201)
async def create_role(
    data: RoleCreateSchema,
    current_session=Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    # ✅ Используем create
    role = await crud_role.create(
        db,
        data=data,
        current_tenant_id=current_session.tenant_id,
        is_superadmin=current_session.is_superadmin,
    )
    
    return ApiResponse(
        success=True,
        message="Роль создана",
        data=RoleResponseSchema.model_validate(role),
    )


@router.put("/{role_id}", response_model=ApiResponse[RoleResponseSchema])
async def update_role(
    role_id: uuid.UUID,
    data: RoleUpdateSchema,
    current_session=Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    # ✅ Используем update
    role = await crud_role.update(
        db,
        item_id=role_id,
        data=data,
        current_tenant_id=current_session.tenant_id,
        is_superadmin=current_session.is_superadmin,
    )
    
    return ApiResponse(
        success=True,
        message="Роль обновлена",
        data=RoleResponseSchema.model_validate(role),
    )


@router.delete("/{role_id}", response_model=ApiResponse[RoleResponseSchema])
async def delete_role(
    role_id: uuid.UUID,
    current_session=Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    # ✅ Используем delete (с проверкой связанных записей внутри)
    role = await crud_role.delete(
        db,
        item_id=role_id,
        current_tenant_id=current_session.tenant_id,
        is_superadmin=current_session.is_superadmin,
    )
    
    return ApiResponse(
        success=True,
        message="Роль удалена",
        data=RoleResponseSchema.model_validate(role),
    )
```

#### ❌ НЕПРАВИЛЬНО: Неполный CRUD-класс

```python
# ❌ ГРУБОЕ НАРУШЕНИЕ ПРАВИЛА №2
class CRUDRole:
    def __init__(self, model):
        self.model = model

    # ✅ Есть только create и get
    async def create(self, db, data):
        pass
    
    async def get(self, db, item_id):
        pass
    
    # ❌ ОТСУТСТВУЮТ:
    # - get_by_* (поиск по уникальным полям)
    # - get_multi (список)
    # - get_multi_paginated (список с пагинацией)
    # - update (обновление)
    # - delete (удаление)
```
*Почему это плохо:* Разработчик вынужден писать SQL-запросы напрямую в роутерах, обходя проверки безопасности и бизнес-логику.

#### ❌ НЕПРАВИЛЬНО: Отсутствие проверки связанных записей при удалении

```python
# ❌ ОШИБКА: Удаление без проверки связей
async def delete(self, db: AsyncSession, item_id: uuid.UUID):
    db_obj = await self.get(db, item_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Роль не найдена")
    
    # ❌ Нет проверки наличия связанных полномочий!
    # Пользователь удалит роль, а полномочия останутся "висящими"
    await db.delete(db_obj)
    await db.commit()
    return db_obj
```
*Почему это плохо:* Нарушается целостность данных. Полномочия, ссылающиеся на удалённую роль, становятся "сиротами", что вызывает ошибки при последующих запросах.

#### ❌ НЕПРАВИЛЬНО: Отсутствие фильтрации по tenant_id

```python
# ❌ ОШИБКА: Метод не учитывает multi-tenancy
async def get(self, db: AsyncSession, item_id: uuid.UUID):
    # ❌ Возвращает роль из ЛЮБОГО тенанта!
    stmt = select(self.model).where(self.model.id == item_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
```
*Почему это плохо:* Нарушение Правила №26 — пользователь из Организации А может получить данные роли Организации Б, просто узнав её UUID.

#### ❌ НЕПРАВИЛЬНО: Отсутствие пагинации

```python
# ❌ ОШИБКА: Возвращает все записи без пагинации
async def get_multi(self, db: AsyncSession):
    stmt = select(self.model)
    result = await db.execute(stmt)
    return result.scalars().all()  # ❌ Может вернуть 10,000 записей!
```
*Почему это плохо:* При большом количестве записей это вызывает:
1. Перегрузку базы данных
2. Огромный объём передаваемых данных
3. Зависание фронтенда при рендеринге
4. Невозможность построить пагинацию (нет `total`)

---

### 4. Нюансы и лучшие практики

#### 4.1. Базовый CRUD-класс (Generic)
Для уменьшения дублирования можно создать базовый класс с общими методами:

```python
# backend/app/core/base_crud.py
from typing import Generic, TypeVar, Optional, Type
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)


class CRUDBase(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(
        self,
        db: AsyncSession,
        item_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> Optional[ModelType]:
        stmt = select(self.model).where(self.model.id == item_id)
        if not is_superadmin:
            stmt = stmt.where(self.model.tenant_id == current_tenant_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
        current_tenant_id: Optional[uuid.UUID] = None,
        is_superadmin: bool = False,
    ) -> tuple[list[ModelType], int]:
        stmt = select(self.model)
        count_stmt = select(func.count()).select_from(self.model)
        
        if not is_superadmin and current_tenant_id:
            stmt = stmt.where(self.model.tenant_id == current_tenant_id)
            count_stmt = count_stmt.where(self.model.tenant_id == current_tenant_id)
        
        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one()
        
        stmt = stmt.offset(skip).limit(limit).order_by(self.model.id)
        result = await db.execute(stmt)
        
        return list(result.scalars().all()), total

    async def delete(
        self,
        db: AsyncSession,
        item_id: uuid.UUID,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> ModelType:
        db_obj = await self.get(db, item_id, current_tenant_id, is_superadmin)
        if not db_obj:
            raise HTTPException(status_code=404, detail="Запись не найдена")
        
        await db.delete(db_obj)
        await db.commit()
        return db_obj
```

**Использование:**
```python
# backend/app/core/roles/crud.py
from app.core.base_crud import CRUDBase
from app.core.roles.models import RoleModel


class CRUDRole(CRUDBase[RoleModel]):
    # ✅ Наследуем базовые методы
    # ✅ Добавляем только специфичные для ролей
    
    async def get_by_name(self, db, name, current_tenant_id, is_superadmin=False):
        # Специфичная для ролей логика
        pass
    
    async def create(self, db, data, current_tenant_id, is_superadmin=False):
        # Специфичная логика создания роли
        pass
```

#### 4.2. Методы `get_by_*` для уникальных полей
Для каждого уникального поля **ОБЯЗАТЕЛЬНО** должен быть метод `get_by_*`:

```python
class CRUDUser(CRUDBase[UserModel]):
    async def get_by_email(
        self,
        db: AsyncSession,
        email: str,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> Optional[UserModel]:
        stmt = select(self.model).where(self.model.email == email)
        if not is_superadmin:
            stmt = stmt.where(self.model.tenant_id == current_tenant_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_username(
        self,
        db: AsyncSession,
        username: str,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> Optional[UserModel]:
        # Аналогично для username
        pass
```

#### 4.3. Защита от удаления связанных записей
Перед удалением **ОБЯЗАТЕЛЬНО** проверять все связи:

```python
async def delete(self, db, item_id, current_tenant_id, is_superadmin=False):
    db_obj = await self.get(db, item_id, current_tenant_id, is_superadmin)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Запись не найдена")
    
    # ✅ Проверка всех связей
    relations = {
        "permissions": await self._count_permissions(db, item_id),
        "users": await self._count_users_with_role(db, item_id),
    }
    
    active_relations = {k: v for k, v in relations.items() if v > 0}
    if active_relations:
        details = ", ".join([f"{k}: {v}" for k, v in active_relations.items()])
        raise HTTPException(
            status_code=400,
            detail=f"Невозможно удалить запись. Существуют связанные записи: {details}"
        )
    
    await db.delete(db_obj)
    await db.commit()
    return db_obj
```

#### 4.4. Поддержка поиска (search)
Метод `get_multi` **ОБЯЗАТЕЛЬНО** должен поддерживать поиск по основным текстовым полям:

```python
async def get_multi(
    self,
    db: AsyncSession,
    search: Optional[str] = None,
    # ...
):
    stmt = select(self.model)
    
    if search:
        # ✅ Поиск по нескольким полям через OR
        search_filter = (
            self.model.name.ilike(f"%{search}%") |
            self.model.description.ilike(f"%{search}%")
        )
        stmt = stmt.where(search_filter)
    
    # ...
```

#### 4.5. Сортировка по умолчанию
Все методы получения списка **ОБЯЗАТЕЛЬНО** должны иметь сортировку по умолчанию, чтобы результаты были предсказуемы:

```python
# ✅ Сортировка по имени (или по created_at, если имени нет)
stmt = stmt.order_by(self.model.name)

# ✅ Для записей без имени — по дате создания
stmt = stmt.order_by(self.model.created_at.desc())
```

#### 4.6. Связь с другими правилами

**Правило №1 (Чистая архитектура):**
CRUD-класс работает только с ORM-моделями и Pydantic-схемами. Он не должен знать о HTTP, сессиях или бизнес-логике.

**Правило №4 (Orval-совместимость):**
CRUD-методы возвращают ORM-объекты, которые затем конвертируются в роутере через `.model_validate()`.

**Правило №21 (Именование Pydantic-схем):**
CRUD-методы принимают схемы с суффиксом `Schema`: `RoleCreateSchema`, `RoleUpdateSchema`.

**Правило №26 (Безопасность multi-tenancy):**
Каждый метод CRUD **ОБЯЗАТЕЛЬНО** принимает `current_tenant_id` и `is_superadmin`, и применяет фильтрацию.

**Правило №28 (Схема `public`):**
Все модели, с которыми работает CRUD, должны иметь `__table_args__ = {"schema": "public"}`.

---

### 5. Типичные ошибки и их исправление

| Ошибка | Исправление |
| :--- | :--- |
| Отсутствие метода `get_multi_paginated` | Добавить метод, возвращающий `(items, total)` |
| Отсутствие фильтрации по `tenant_id` | Добавить проверку в каждый метод |
| Отсутствие проверки связанных записей в `delete` | Добавить подсчёт связей и блокировку удаления |
| Отсутствие поиска в `get_multi` | Добавить параметр `search` с `ilike` |
| Отсутствие сортировки по умолчанию | Добавить `.order_by()` в запрос |
| Возврат ORM-объекта напрямую в роутере | Использовать `.model_validate()` (Правило №4) |
| Ручные словари вместо Pydantic-схем | Использовать схемы с суффиксом `Schema` (Правило №21) |
| Отсутствие метода `get_by_*` для уникальных полей | Добавить методы для всех уникальных полей |

---

### 6. Чек-лист для разработчика

При создании нового CRUD-класса проверьте:

**Обязательные методы:**
- [ ] Реализован ли метод `create`?
- [ ] Реализован ли метод `get` (по ID)?
- [ ] Реализованы ли методы `get_by_*` для всех уникальных полей?
- [ ] Реализован ли метод `get_multi` (список с поиском)?
- [ ] Реализован ли метод `get_multi_paginated` (возвращает `tuple[list, int]`)?
- [ ] Реализован ли метод `update`?
- [ ] Реализован ли метод `delete`?

**Безопасность (Правило №26):**
- [ ] Все методы принимают `current_tenant_id` и `is_superadmin`?
- [ ] Все `SELECT`-запросы фильтруют по `tenant_id`?
- [ ] При создании `tenant_id` берётся из контекста, а не из данных?
- [ ] При обновлении/удалении проверяется принадлежность к тенанту?

**Целостность данных:**
- [ ] Метод `delete` проверяет наличие связанных записей?
- [ ] Метод `create` проверяет уникальность (если есть уникальные поля)?
- [ ] Метод `update` проверяет уникальность при изменении уникальных полей?

**Поиск и пагинация:**
- [ ] Метод `get_multi` поддерживает параметр `search`?
- [ ] Поиск использует `ilike` для регистронезависимости?
- [ ] Метод `get_multi_paginated` возвращает `total` для пагинации?
- [ ] Есть ли сортировка по умолчанию (`order_by`)?

**Интеграция:**
- [ ] CRUD-класс экспортирует экземпляр с именем сущности (`crud_role`)?
- [ ] Методы возвращают ORM-модели (не словари)?
- [ ] В роутере используется `.model_validate()` для конвертации (Правило №4)?
- [ ] Все Pydantic-схемы имеют суффикс `Schema` (Правило №21)?

**Тестирование:**
- [ ] Написаны ли unit-тесты для каждого метода CRUD?
- [ ] Проверяется ли фильтрация по `tenant_id` в тестах?
- [ ] Проверяется ли защита от удаления связанных записей?

---

### 7. Таблица соответствий

| Метод CRUD | HTTP-метод | URL | Назначение |
| :--- | :--- | :--- | :--- |
| `create` | `POST` | `/api/v1/roles/` | Создание записи |
| `get` | `GET` | `/api/v1/roles/{id}` | Получение одной записи |
| `get_by_*` | — | — | Внутренний метод для проверки уникальности |
| `get_multi` | `GET` | `/api/v1/roles/?search=...` | Получение списка (без пагинации) |
| `get_multi_paginated` | `GET` | `/api/v1/roles/?skip=0&limit=10` | Получение списка с пагинацией |
| `update` | `PUT` | `/api/v1/roles/{id}` | Обновление записи |
| `delete` | `DELETE` | `/api/v1/roles/{id}` | Удаление записи |

---

Следование этому правилу гарантирует, что CRUD-слой Cool ERP будет:
✅ **Полным** — все необходимые методы реализованы
✅ **Безопасным** — фильтрация по `tenant_id` в каждом методе
✅ **Целостным** — защита от удаления связанных записей
✅ **Производительным** — пагинация и поиск из коробки
✅ **Единообразным** — одинаковая структура для всех доменов
✅ **Orval-совместимым** — автоматическая генерация фронтенд-клиентов

Это правило работает в связке с Правилами №1 (Чистая архитектура), №4 (Orval-совместимость), №21 (Именование схем), №26 (Безопасность multi-tenancy) и №28 (Схема `public`), формируя единый стандарт работы с данными на уровне доступа к БД.