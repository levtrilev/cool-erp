# Правило №6: Именование файлов в доменах

В каждой папке домена (сущности) файлы **ОБЯЗАТЕЛЬНО** именуются коротко, БЕЗ префиксов и суффиксов с именем сущности. Контекст задаётся именем родительской папки, а не именем файла.

✅ **Правильно:** `models.py`, `schemas.py`, `crud.py`, `router.py`, `services.py`, `dependencies.py`
❌ **Неправильно:** `crud_user.py`, `router_tenant.py`, `schemas_role.py`, `user_models.py`, `tenant_crud.py`

---

### 1. Обоснование (Почему это важно)

1. **Контекст задаётся папкой:** Когда разработчик открывает `backend/app/core/users/crud.py`, он уже видит из пути, что это CRUD для пользователей. Дублирование имени сущности в файле (`crud_user.py`) — это избыточность, нарушающая принцип DRY.
2. **Единообразие структуры:** Все домены (`users`, `roles`, `tenants`, `permissions`) имеют **идентичную** внутреннюю структуру. Разработчик, изучив один домен, мгновенно понимает организацию любого другого.
3. **Простота импортов:** Короткие имена файлов делают импорты чище и легче читаются:
   ```python
   # ✅ ПРАВИЛЬНО: Короткий и понятный импорт
   from app.core.users.crud import crud_user
   from app.core.users.schemas import UserCreateSchema
   
   # ❌ ОШИБКА: Избыточный импорт с дублированием контекста
   from app.core.users.crud_user import crud_user
   from app.core.users.schemas_user import UserCreateSchema
   ```
4. **Масштабируемость:** При добавлении нового домена (например, `invoices`) не нужно придумывать новые имена файлов — структура уже стандартизирована.
5. **Соответствие фреймворкам:** Многие Python-фреймворки (Django, FastAPI-шаблоны) используют именно такой подход (`models.py`, `views.py`, `urls.py`), что облегчает онбординг разработчиков, знакомых с экосистемой.

---

### 2. Обязательные требования к реализации

#### 2.1. Стандартный набор файлов
Каждый домен **ОБЯЗАТЕЛЬНО** должен содержать следующие файлы (если функционал требуется):

| Файл | Назначение | Обязательность |
| :--- | :--- | :--- |
| `models.py` | SQLAlchemy ORM-модели | ✅ Обязательно |
| `schemas.py` | Pydantic-схемы (DTO) | ✅ Обязательно |
| `crud.py` | CRUD-класс с экземпляром `crud_xxx` | ✅ Обязательно |
| `router.py` | FastAPI-роутер с эндпоинтами | ✅ Обязательно |
| `services.py` | Бизнес-логика (если нужна) | ⚠️ Опционально |
| `dependencies.py` | FastAPI-зависимости (если нужны) | ⚠️ Опционально |
| `__init__.py` | Экспорты для упрощения импортов | ⚠️ Опционально |

#### 2.2. Запрет на префиксы/суффиксы
**КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО** добавлять имя сущности в название файла:
* ❌ `user_models.py` → ✅ `models.py`
* ❌ `crud_role.py` → ✅ `crud.py`
* ❌ `router_tenant.py` → ✅ `router.py`
* ❌ `schemas_permission.py` → ✅ `schemas.py`
* ❌ `services_section.py` → ✅ `services.py`

#### 2.3. Именование экземпляров внутри файлов
Внутри файлов имена переменных и классов **ДОЛЖНЫ** содержать имя сущности для различения:
```python
# ✅ ПРАВИЛЬНО: Файл crud.py, но экземпляр имеет имя сущности
class CRUDUser:
    ...

crud_user = CRUDUser(UserModel)  # ✅ Имя переменной различает сущности
```

---

### 3. Примеры кода

#### ✅ ПРАВИЛЬНО: Структура домена `users`

```text
backend/app/core/users/
 ├── __init__.py          # Экспорты
 ├── models.py            # ✅ UserModel
 ├── schemas.py           # ✅ UserBaseSchema, UserCreateSchema, UserResponseSchema
 ├── crud.py              # ✅ CRUDUser, crud_user
 ├── router.py            # ✅ router с эндпоинтами /users/...
 ├── services.py          # ✅ UserService (если нужна бизнес-логика)
 └── dependencies.py      # ✅ get_current_user и другие зависимости
```

**Содержимое `crud.py`:**
```python
# ✅ Файл называется crud.py (НЕ crud_user.py)
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.users.models import UserModel
from app.core.users.schemas import UserCreateSchema, UserUpdateSchema


class CRUDUser:
    def __init__(self, model):
        self.model = model

    async def create(
        self, 
        db: AsyncSession, 
        data: UserCreateSchema,
        current_tenant_id: uuid.UUID,
        is_superadmin: bool = False,
    ) -> UserModel:
        db_obj = self.model(**data.model_dump(), tenant_id=current_tenant_id)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_multi(self, db: AsyncSession, ...):
        # ... логика получения списка
        pass


# ✅ Экземпляр имеет имя сущности для различения при импорте
crud_user = CRUDUser(UserModel)
```

**Использование в роутере (`router.py`):**
```python
# ✅ Файл называется router.py (НЕ router_user.py)
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.users.crud import crud_user  # ✅ Короткий импорт
from app.core.users.schemas import UserCreateSchema, UserResponseSchema

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponseSchema)
async def create_user(
    data: UserCreateSchema,
    db: AsyncSession = Depends(get_db),
):
    return await crud_user.create(db, data=data)
```

#### ✅ ПРАВИЛЬНО: Структура домена `roles`

```text
backend/app/core/roles/
 ├── __init__.py
 ├── models.py            # ✅ RoleModel
 ├── schemas.py           # ✅ RoleBaseSchema, RoleCreateSchema, RoleResponseSchema, RoleSaveSchema
 ├── crud.py              # ✅ CRUDRole, crud_role
 ├── router.py            # ✅ router с эндпоинтами /roles/...
 └── services.py          # ✅ RoleService (с методом save_role для sync-паттерна)
```

#### ✅ ПРАВИЛЬНО: Структура домена `permissions`

```text
backend/app/core/permissions/
 ├── __init__.py
 ├── models.py            # ✅ PermissionModel
 ├── schemas.py           # ✅ PermissionBaseSchema, PermissionCreateSchema, PermissionResponseSchema
 ├── crud.py              # ✅ CRUDPermission, crud_permission
 └── router.py            # ✅ router (если есть отдельные эндпоинты)
```

#### ❌ НЕПРАВИЛЬНО: Избыточные имена файлов

```text
backend/app/core/users/
 ├── __init__.py
 ├── user_models.py           # ❌ ОШИБКА: должно быть models.py
 ├── user_schemas.py          # ❌ ОШИБКА: должно быть schemas.py
 ├── crud_user.py             # ❌ ОШИБКА: должно быть crud.py
 ├── router_user.py           # ❌ ОШИБКА: должно быть router.py
 └── services_user.py         # ❌ ОШИБКА: должно быть services.py
```

```text
backend/app/core/roles/
 ├── __init__.py
 ├── role_models.py           # ❌ ОШИБКА
 ├── role_schemas.py          # ❌ ОШИБКА
 ├── crud_role.py             # ❌ ОШИБКА
 └── router_role.py           # ❌ ОШИБКА
```
*Почему это плохо:* При импорте получается `from app.core.users.crud_user import crud_user` — имя сущности дублируется дважды. Это нарушает принцип DRY и затрудняет чтение кода.

#### ❌ НЕПРАВИЛЬНО: Смешение стилей

```text
backend/app/core/
 ├── users/
 │   ├── models.py              # ✅ Короткое имя
 │   └── crud_user.py           # ❌ ОШИБКА: длинное имя (несогласованность)
 ├── roles/
 │   ├── role_models.py         # ❌ ОШИБКА: длинное имя
 │   └── crud.py                # ✅ Короткое имя
 └── tenants/
     ├── tenant_models.py       # ❌ ОШИБКА
     └── tenant_crud.py         # ❌ ОШИБКА
```
*Почему это плохо:* Несоответствие стилей внутри проекта. Разработчик не может предсказать, как называется файл в новом домене, и вынужден каждый раз искать его в проводнике.

---

### 4. Нюансы и лучшие практики

#### 4.1. Связь с Правилом №7 (Множественное число)
Правило №6 работает в паре с Правилом №7:
* **Папка** — во множественном числе (`users/`), так как содержит код для работы со всеми сущностями.
* **Файлы внутри** — короткие (`models.py`), так как контекст уже задан папкой.
* **Классы внутри** — в единственном числе (`UserModel`), так как представляют один объект.
* **Экземпляры** — с именем сущности (`crud_user`), для различения при импорте.

```text
users/                    ← Множественное (Папка)
 ├── models.py            ← Короткое (Файл)
 │    └── UserModel       ← Единственное (Класс)
 └── crud.py              ← Короткое (Файл)
      └── crud_user       ← С именем сущности (Экземпляр)
```

#### 4.2. Файл `__init__.py` для удобных импортов
Чтобы упростить импорты извне, можно использовать `__init__.py`:

```python
# backend/app/core/users/__init__.py
from app.core.users.models import UserModel
from app.core.users.crud import crud_user
from app.core.users.schemas import (
    UserBaseSchema,
    UserCreateSchema,
    UserUpdateSchema,
    UserResponseSchema,
)

__all__ = [
    "UserModel",
    "crud_user",
    "UserBaseSchema",
    "UserCreateSchema",
    "UserUpdateSchema",
    "UserResponseSchema",
]
```

Теперь импорты становятся ещё короче:
```python
# ✅ Вместо
from app.core.users.crud import crud_user
from app.core.users.schemas import UserCreateSchema

# ✅ Можно писать
from app.core.users import crud_user, UserCreateSchema
```

#### 4.3. Когда нужны дополнительные файлы
Если домен становится слишком сложным, допускается разделение на дополнительные файлы, но **ВСЕГДА** с короткими именами:

```text
backend/app/core/roles/
 ├── models.py
 ├── schemas.py
 ├── crud.py
 ├── router.py
 ├── services.py          # ✅ Основная бизнес-логика
 ├── validators.py        # ✅ Дополнительная валидация (если нужна)
 └── utils.py             # ✅ Утилиты для домена (если нужны)
```

❌ **НЕПРАВИЛЬНО:** `role_validators.py`, `role_utils.py` — префикс с именем сущности запрещён.

#### 4.4. Файлы тестов
Тесты обычно выносятся в отдельную директорию `tests/`, но внутри неё также применяется правило коротких имён:

```text
tests/
 ├── core/
 │   ├── users/
 │   │   ├── test_models.py      # ✅ (НЕ test_user_models.py)
 │   │   ├── test_crud.py        # ✅ (НЕ test_crud_user.py)
 │   │   └── test_router.py      # ✅ (НЕ test_router_user.py)
 │   └── roles/
 │       ├── test_models.py
 │       ├── test_crud.py
 │       └── test_router.py
```

#### 4.5. Frontend: аналогичное правило
На фронтенде правило работает аналогично, но с учётом React-специфики:

```text
frontend/src/core/users/
 ├── UsersPage.tsx          # ✅ Страница списка
 ├── CreateUserModal.tsx    # ✅ Модалка создания
 ├── EditUserModal.tsx      # ✅ Модалка редактирования
 └── index.ts               # ✅ Экспорты
```

Здесь имена файлов уже содержат имя сущности, так как на фронтенде компоненты называются по их назначению (а не по слою архитектуры). Это допустимое исключение для UI-компонентов.

#### 4.6. Связь с Правилом №1 (Чистая архитектура)
Правило №6 поддерживает чистую архитектуру, явно разделяя слои:
* `models.py` — слой данных (ORM)
* `schemas.py` — слой DTO (валидация)
* `crud.py` — слой доступа к данным
* `router.py` — слой API (HTTP)
* `services.py` — слой бизнес-логики

Каждый файл отвечает за **один** слой, что соответствует принципу единственной ответственности (SRP).

#### 4.7. Связь с Правилом №21 (Именование Pydantic-схем)
Внутри `schemas.py` все классы должны заканчиваться на `Schema`:
```python
# ✅ ПРАВИЛЬНО: Файл schemas.py, классы с суффиксом Schema
class UserBaseSchema(BaseModel): ...
class UserCreateSchema(UserBaseSchema): ...
class UserResponseSchema(UserBaseSchema): ...
```

#### 4.8. Связь с Правилом №28 (Схема `public`)
Внутри `models.py` все модели должны указывать `schema="public"`:
```python
# ✅ ПРАВИЛЬНО: Файл models.py, схема public
class UserModel(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}
```

---

### 5. Исключения

Допускаются следующие исключения из правила:

1. **Файлы конфигурации:** `config.py`, `settings.py` — не относятся к конкретному домену.
2. **Утилиты общего назначения:** `utils.py`, `helpers.py` в корне `app/`.
3. **Миграции Alembic:** Файлы в `alembic/versions/` имеют собственные имена с хэшами.
4. **Тестовые фикстуры:** `conftest.py` — стандартное имя для pytest.
5. **Frontend-компоненты:** На фронтенде имена файлов компонентов содержат имя сущности (см. п.4.5).

---

### 6. Чек-лист для разработчика

При создании нового домена или рефакторинге существующего проверьте:

**Структура папки:**
- [ ] Папка домена названа во множественном числе (Правило №7)?
- [ ] В папке есть `models.py` (без префикса)?
- [ ] В папке есть `schemas.py` (без префикса)?
- [ ] В папке есть `crud.py` (без префикса)?
- [ ] В папке есть `router.py` (без префикса)?
- [ ] Дополнительные файлы (`services.py`, `dependencies.py`) тоже без префиксов?

**Содержимое файлов:**
- [ ] В `models.py` классы имеют суффикс `Model` (`UserModel`, `RoleModel`)?
- [ ] В `schemas.py` классы имеют суффикс `Schema` (Правило №21)?
- [ ] В `crud.py` класс называется `CRUDXxx`, а экземпляр — `crud_xxx`?
- [ ] В `router.py` используется `APIRouter` с правильным `prefix`?

**Импорты:**
- [ ] Импорты в других файлах используют короткие пути (`from app.core.users.crud import crud_user`)?
- [ ] Отсутствуют ли импорты вида `from app.core.users.crud_user import crud_user`?

**Тесты:**
- [ ] Тестовые файлы также используют короткие имена (`test_models.py`, а не `test_user_models.py`)?

**Frontend (если применимо):**
- [ ] Папка домена на фронтенде названа во множественном числе?
- [ ] Компоненты имеют понятные имена (`UsersPage.tsx`, `EditUserModal.tsx`)?

---

### 7. Таблица соответствий

| Домен | Папка | Файл модели | Файл схем | Файл CRUD | Экземпляр CRUD |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Пользователи | `users/` | `models.py` | `schemas.py` | `crud.py` | `crud_user` |
| Организации | `tenants/` | `models.py` | `schemas.py` | `crud.py` | `crud_tenant` |
| Роли | `roles/` | `models.py` | `schemas.py` | `crud.py` | `crud_role` |
| Полномочия | `permissions/` | `models.py` | `schemas.py` | `crud.py` | `crud_permission` |
| Разделы | `sections/` | `models.py` | `schemas.py` | `crud.py` | `crud_section` |
| Типы документов | `doctypes/` | `models.py` | `schemas.py` | `crud.py` | `crud_doctype` |

---

Следование этому правилу гарантирует, что структура проекта Cool ERP будет:
✅ **Предсказуемой** — любой разработчик мгновенно найдёт нужный файл
✅ **Единообразной** — все домены имеют одинаковую организацию
✅ **Масштабируемой** — добавление новых доменов не требует придумывания имён
✅ **Читаемой** — импорты короткие и понятные
✅ **Соответствующей стандартам** — следует best practices Python-экосистемы

Это правило является фундаментом чистой архитектуры проекта и работает в связке с Правилами №1 (Чистая архитектура), №7 (Множественное число), №21 (Именование схем) и №28 (Схема `public`).