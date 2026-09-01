для ERP-системы с десятками сущностей в каждом модуле - **двухуровневая архитектура**: домены → сущности.

---

## 🎯 Ключевые принципы новой структуры

1. **Домен (модуль)** — это крупная бизнес-область (`core`, `inventory`, `assets`, `cashflow`).
2. **Сущность** — это конкретная бизнес-концепция внутри домена (`user`, `tenant`, `role`, `asset`, `depreciation`).
3. **Каждая сущность** — самодостаточная единица со своим `models.py`, `schemas.py`, `crud.py`, `router.py`, `services.py`.
4. **Домен** агрегирует роутеры своих сущностей в единый публичный API.
5. **`core`** — это не просто инфраструктура, а **домен безопасности и RBAC** (согласен с вашим решением).

---

## 📁 Итоговая структура Backend

```
backend/app/
├── main.py                              # Точка входа, регистрация всех доменов
│
├── core/                                # 🛡️ ДОМЕН БЕЗОПАСНОСТИ И RBAC
│   ├── __init__.py
│   │
│   ├── database.py                      # Инфраструктура: engine, Base, get_db
│   ├── config.py                        # Инфраструктура: settings
│   ├── schemas.py                       # Общие схемы: ApiResponse, PaginatedResponse
│   ├── exceptions.py                    # Общие исключения
│   │
│   ├── auth/                            # 🔐 Аутентификация (сессии, токены)
│   │   ├── models.py                    # UserSession
│   │   ├── schemas.py                   # LoginSchema, TokenSchema
│   │   ├── router.py                    # /login, /logout, /refresh
│   │   ├── security.py                  # verify_password, hash_password
│   │   └── dependencies.py              # get_current_session
│   │
│   ├── user/                            # 👤 Пользователи
│   │   ├── models.py                    # UserModel
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── router.py                    # /users
│   │   └── services.py
│   │
│   ├── tenant/                          # 🏢 Организации (тенанты)
│   │   ├── models.py                    # TenantModel
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── router.py                    # /tenants
│   │   └── services.py
│   │
│   ├── role/                            # 🎭 Роли (RBAC)
│   │   ├── models.py                    # RoleModel
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── router.py                    # /roles
│   │   └── services.py
│   │
│   ├── permission/                      # 🔑 Полномочия
│   │   ├── models.py                    # PermissionModel
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── router.py                    # /permissions
│   │   └── services.py
│   │
│   └── group/                           # 👥 Группы пользователей
│       ├── models.py                    # GroupModel, user_group_association
│       ├── schemas.py
│       ├── crud.py
│       ├── router.py                    # /groups
│       └── services.py
│
├── inventory/                           # 📦 ДОМЕН "СКЛАД"
│   ├── __init__.py
│   ├── router.py                        # 🎯 АГРЕГАТОР: включает все суброутеры
│   │
│   ├── product/                         # Товары
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── router.py                    # /inventory/products
│   │   └── services.py
│   │
│   ├── warehouse/                       # Склады
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── router.py                    # /inventory/warehouses
│   │   └── services.py
│   │
│   ├── stock_movement/                  # Движение товаров
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── router.py                    # /inventory/movements
│   │   └── services.py
│   │
│   └── category/                        # Категории товаров
│       ├── models.py
│       ├── schemas.py
│       ├── crud.py
│       └── router.py
│
├── assets/                              # 🏗️ ДОМЕН "ОСНОВНЫЕ СРЕДСТВА"
│   ├── __init__.py
│   ├── router.py                        # АГРЕГАТОР
│   │
│   ├── asset/                           # Активы
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── router.py
│   │   └── services.py
│   │
│   ├── depreciation/                    # Амортизация
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── router.py
│   │   └── services.py
│   │
│   ├── asset_category/                  # Категории активов
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   └── router.py
│   │
│   └── location/                        # Местоположения
│       ├── models.py
│       ├── schemas.py
│       ├── crud.py
│       └── router.py
│
├── cashflow/                            # 💰 ДОМЕН "ДЕНЕЖНЫЕ СРЕДСТВА"
│   ├── __init__.py
│   ├── router.py
│   │
│   ├── transaction/
│   ├── bank_account/
│   ├── payment_method/
│   └── currency/
│
└── payable/                             # 💳 ДОМЕН "КРЕДИТОРСКАЯ ЗАДОЛЖЕННОСТЬ"
    ├── __init__.py
    ├── router.py
    │
    ├── invoice/
    ├── payment/
    └── vendor/
```

---

## 🔧 Как это работает

### 1. Роутер домена — агрегатор суброутеров

Каждый домен имеет свой `router.py`, который просто собирает роутеры сущностей:

```python
# backend/app/assets/router.py
from fastapi import APIRouter
from app.assets.asset.router import router as asset_router
from app.assets.depreciation.router import router as depreciation_router
from app.assets.asset_category.router import router as category_router
from app.assets.location.router import router as location_router

# Главный роутер домена
router = APIRouter(prefix="/assets", tags=["Assets"])

router.include_router(asset_router)        # /assets/...
router.include_router(depreciation_router) # /assets/depreciations/...
router.include_router(category_router)     # /assets/categories/...
router.include_router(location_router)     # /assets/locations/...
```

### 2. Роутер сущности — конкретные эндпоинты

```python
# backend/app/assets/asset/router.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.assets.asset.schemas import AssetCreateSchema, AssetResponseSchema
from app.assets.asset.crud import crud_asset

router = APIRouter(prefix="/items", tags=["Assets"])  # Обратите внимание: нет /assets, это добавит родитель

@router.get("/", response_model=list[AssetResponseSchema])
async def list_assets(db: AsyncSession = Depends(get_db)):
    return await crud_asset.get_multi(db)

@router.post("/", response_model=AssetResponseSchema, status_code=201)
async def create_asset(data: AssetCreateSchema, db: AsyncSession = Depends(get_db)):
    return await crud_asset.create(db, data)
```

### 3. Регистрация в `main.py`

```python
# backend/app/main.py
from fastapi import FastAPI

# Импорты моделей (критично для SQLAlchemy!)
from app.core.auth.models import UserSession
from app.core.user.models import UserModel
from app.core.tenant.models import TenantModel
from app.core.role.models import RoleModel
from app.core.permission.models import PermissionModel
from app.core.group.models import GroupModel
# ... импорты моделей из других доменов по мере их создания

# Импорты роутеров доменов
from app.core.auth.router import router as auth_router
from app.core.user.router import router as user_router
from app.core.tenant.router import router as tenant_router
from app.core.role.router import router as role_router
from app.core.permission.router import router as permission_router
from app.core.group.router import router as group_router
from app.assets.router import router as assets_router
from app.inventory.router import router as inventory_router
from app.cashflow.router import router as cashflow_router
from app.payable.router import router as payable_router

app = FastAPI(title="Cool ERP", version="1.0.0")

# Префикс /api/v1 применяется ко всем доменам
app.include_router(auth_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(tenant_router, prefix="/api/v1")
app.include_router(role_router, prefix="/api/v1")
app.include_router(permission_router, prefix="/api/v1")
app.include_router(group_router, prefix="/api/v1")
app.include_router(assets_router, prefix="/api/v1")
app.include_router(inventory_router, prefix="/api/v1")
app.include_router(cashflow_router, prefix="/api/v1")
app.include_router(payable_router, prefix="/api/v1")
```

Итоговые URL:
- `POST /api/v1/auth/login`
- `GET /api/v1/users/`
- `GET /api/v1/tenants/`
- `GET /api/v1/assets/items/`
- `POST /api/v1/assets/items/`
- `GET /api/v1/assets/depreciations/`
- `GET /api/v1/inventory/products/`

---

## 📁 Зеркальная структура Frontend

```
frontend/src/
├── api/
│   └── generated/                       # Orval (автогенерация)
│
├── core/                                # 🛡️ Общие утилиты + домен безопасности
│   ├── components/                      # UI-kit: Button, Input, Dialog, ReferenceSelect
│   ├── hooks/                           # useAuth, useDebounce, usePagination
│   ├── lib/                             # cn, formatDate, apiClient
│   ├── types/                           # Общие типы
│   │
│   ├── auth/                            # 🔐 Аутентификация
│   │   ├── components/                  # LoginForm, LogoutButton
│   │   ├── hooks/                       # useLogin, useLogout, useSession
│   │   └── pages/                       # LoginPage
│   │
│   ├── user/                            # 👤 Пользователи
│   │   ├── components/                  # UserTable, EditUserModal
│   │   ├── hooks/                       # useUsers, useUpdateUser
│   │   └── pages/                       # UsersPage
│   │
│   ├── tenant/                          # 🏢 Организации
│   ├── role/                            # 🎭 Роли
│   ├── permission/                      # 🔑 Полномочия
│   └── group/                           # 👥 Группы
│
├── inventory/                           # 📦 ДОМЕН "СКЛАД"
│   ├── product/
│   │   ├── components/                  # ProductTable, ProductForm
│   │   ├── hooks/                       # useProducts
│   │   └── pages/                       # ProductsPage
│   ├── warehouse/
│   ├── stock-movement/
│   └── category/
│
├── assets/                              # 🏗️ ДОМЕН "ОСНОВНЫЕ СРЕДСТВА"
│   ├── asset/
│   │   ├── components/
│   │   ├── hooks/
│   │   └── pages/
│   ├── depreciation/
│   ├── asset-category/
│   └── location/
│
└── cashflow/                            # 💰 ДОМЕН "ДЕНЕЖНЫЕ СРЕДСТВА"
    ├── transaction/
    ├── bank-account/
    └── payment-method/
```

---

## 🚀 Межмодульное взаимодействие

Когда модуль `cashflow` должен проверить остаток на складе из `inventory`, он использует **сервис**, а не CRUD:

```python
# backend/app/inventory/services.py (или inventory/product/services.py)
from sqlalchemy.ext.asyncio import AsyncSession
from app.inventory.product.crud import crud_product

class InventoryService:
    async def check_stock(self, db: AsyncSession, product_id: uuid.UUID, quantity: int) -> bool:
        product = await crud_product.get(db, id=product_id)
        return product is not None and product.stock >= quantity

inventory_service = InventoryService()
```

```python
# backend/app/cashflow/transaction/services.py
from app.inventory.services import inventory_service

class TransactionService:
    async def create_sale(self, db: AsyncSession, product_id: uuid.UUID, quantity: int, ...):
        # Проверяем остаток через сервис другого домена
        has_stock = await inventory_service.check_stock(db, product_id, quantity)
        if not has_stock:
            raise ValueError("Недостаточно товара на складе")
        # ... создание транзакции
```

**Важно**: домены могут импортировать сервисы друг друга, но **не должны импортировать CRUD или роутеры** других доменов. Это сохраняет слабую связанность.

---

## 📋 Шаблон для создания нового модуля

Когда будете добавлять новый домен (например, `hr` для HR-модуля), используйте этот чек-лист:

### Backend:
```bash
# Создать структуру домена
mkdir -p backend/app/hr/{employee,position,department}
touch backend/app/hr/__init__.py
touch backend/app/hr/router.py

# Для каждой сущности
for entity in employee position department; do
  touch backend/app/hr/$entity/__init__.py
  touch backend/app/hr/$entity/models.py
  touch backend/app/hr/$entity/schemas.py
  touch backend/app/hr/$entity/crud.py
  touch backend/app/hr/$entity/router.py
  touch backend/app/hr/$entity/services.py
done
```

### Frontend:
```bash
mkdir -p frontend/src/hr/{employee,position,department}
for entity in employee position department; do
  mkdir -p frontend/src/hr/$entity/{components,hooks,pages}
done
```

---

## 💡 Дополнительные рекомендации

### 1. Alembic и миграции

При такой структуре все модели используют общий `Base` из `app.core.database`, поэтому Alembic будет корректно видеть все таблицы. Главное — импортировать все модели в `main.py` (или в специальном `app/models.py`) до запуска миграций.

### 2. Избегайте циклических импортов

Если `inventory` импортирует `cashflow`, а `cashflow` импортирует `inventory` — это архитектурная ошибка. Решения:
- Вынести общую логику в отдельный домен
- Использовать событийную модель (EventBus)
- Пересмотреть границы доменов

### 3. Тесты

Размещайте тесты рядом с сущностью:
```
inventory/product/
├── models.py
├── schemas.py
├── crud.py
├── router.py
├── services.py
└── tests/
    ├── test_crud.py
    ├── test_router.py
    └── test_services.py
```

### 4. `__init__.py` для публичного API сущности

```python
# backend/app/inventory/product/__init__.py
from .crud import crud_product
from .services import ProductService
from .models import ProductModel

__all__ = ["crud_product", "ProductService", "ProductModel"]
```

Теперь другие модули могут импортировать так:
```python
from app.inventory.product import ProductService
```

---

## 🎯 Итог

Главное:
- **`core`** — это полноценный домен безопасности и RBAC, а не просто "общие утилиты".
- **Каждый бизнес-модуль** (`inventory`, `assets`, `cashflow`) — это контейнер для десятков сущностей.
- **Каждая сущность** — самодостаточная единица со стандартной структурой.
- **Домен** агрегирует сущности в единый API через роутер-агрегатор.

Эта структура:
✅ Масштабируется до сотен сущностей  
✅ Соответствует принципам DDD (Domain-Driven Design)  
✅ Позволяет команде работать над разными доменами параллельно  
✅ Упрощает тестирование (каждая сущность тестируется изолированно)  
✅ Соответствует Vertical Slice Architecture  

