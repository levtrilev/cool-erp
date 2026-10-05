# 📋 Правило №32: Использование аннотированных типов для параметров безопасности

Все параметры зависимостей безопасности (текущий пользователь, проверка прав суперадмина, сессия БД) **ОБЯЗАТЕЛЬНО** должны объявляться через аннотированные типы `Annotated[T, Depends(...)]`. Использование `Depends(...)` в значении по умолчанию параметра **КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО**.

---

### 1. Обоснование (Почему это важно)

1. **Устранение предупреждений анализатора:** При использовании `current_session = Depends(require_superadmin)` без использования переменной в теле функции, Pyright выдаёт предупреждение `"current_session" is not accessed`. С `Annotated` параметр считается "использованным" через тип.
2. **Типобезопасность:** `Annotated` объединяет тип и зависимость в одном месте. Анализатор точно знает, какой тип вернёт зависимость.
3. **Единообразие кода:** Все роутеры используют одинаковые алиасы (`SuperAdminUser`, `CurrentUser`, `DBSession`), что упрощает чтение и рефакторинг.
4. **Снижение boilerplate:** Не нужно дублировать `Depends(require_superadmin)` в каждом роутере — достаточно одного алиаса.
5. **Соответствие современным стандартам FastAPI:** Официальная документация FastAPI рекомендует `Annotated` с версии 0.95.0.
6. **Автоматическая документация:** Swagger UI корректно отображает зависимости, объявленные через `Annotated`.

---

### 2. Обязательные требования к реализации

#### 2.1. Создание алиасов типов в `dependencies.py`
Все алиасы зависимостей **ОБЯЗАТЕЛЬНО** должны быть объявлены в файле `backend/app/core/auth/dependencies.py`:

```python
from typing import Annotated
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Алиасы для использования в роутерах
SuperAdminUser = Annotated[UserSession, Depends(require_superadmin)]
CurrentUser = Annotated[UserSession, Depends(get_current_session)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
```

#### 2.2. Использование алиасов в роутерах
В роутерах **ОБЯЗАТЕЛЬНО** использовать алиасы вместо прямого `Depends(...)`:

```python
# ✅ ПРАВИЛЬНО
@router.post("/", response_model=ApiResponse[RoleResponseSchema])
async def create_role(
    obj_in: RoleCreateSchema,
    current_session: SuperAdminUser,  # ✅ Аннотированный тип
    db: DBSession,
):
    ...

# ❌ НЕПРАВИЛЬНО
@router.post("/", response_model=ApiResponse[RoleResponseSchema])
async def create_role(
    obj_in: RoleCreateSchema,
    current_session: UserSession = Depends(require_superadmin),  # ❌ Старый синтаксис
    db: AsyncSession = Depends(get_db),
):
    ...
```

#### 2.3. Стандартный набор алиасов
Проект **ОБЯЗАТЕЛЬНО** должен содержать следующие алиасы:

| Алиас | Тип | Зависимость | Назначение |
| :--- | :--- | :--- | :--- |
| `SuperAdminUser` | `UserSession` | `require_superadmin` | Только суперадмин |
| `CurrentUser` | `UserSession` | `get_current_session` | Любой авторизованный |
| `DBSession` | `AsyncSession` | `get_db` | Сессия БД |
| `OptionalUser` | `UserSession \| None` | `get_optional_session` | Опциональная авторизация |

#### 2.4. Запрет на прямой `Depends(...)` в роутерах
В файлах `router.py` **ОБЯЗАТЕЛЬНО** запрещено использовать:
- `current_session: UserSession = Depends(require_superadmin)`
- `db: AsyncSession = Depends(get_db)`
- Любые другие прямые вызовы `Depends(...)` в сигнатурах функций

---

### 3. Примеры кода

#### ✅ ПРАВИЛЬНО: Файл `dependencies.py`

```python
# backend/app/core/auth/dependencies.py
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.users.models import UserModel


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class UserSession:
    """DTO для передачи данных текущего пользователя."""
    def __init__(self, user: UserModel):
        self.user = user
        self.id = user.id
        self.tenant_id = user.tenant_id
        self.is_superadmin = user.is_superadmin


async def get_current_session(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> UserSession:
    """Получение данных текущего авторизованного пользователя."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось подтвердить учётные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    return UserSession(user)


async def require_superadmin(
    current_session: UserSession = Depends(get_current_session),
) -> UserSession:
    """Зависимость, требующая прав суперадминистратора."""
    if not current_session.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступно только суперадминистратору"
        )
    return current_session


# ✅ АЛИАСЫ ТИПОВ ДЛЯ ИСПОЛЬЗОВАНИЯ В РОУТЕРАХ
SuperAdminUser = Annotated[UserSession, Depends(require_superadmin)]
CurrentUser = Annotated[UserSession, Depends(get_current_session)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
```

#### ✅ ПРАВИЛЬНО: Использование в роутерах

**Файл `backend/app/core/roles/router.py`:**
```python
import uuid
from fastapi import APIRouter
from typing import cast

from app.core.auth.dependencies import SuperAdminUser, CurrentUser, DBSession
from app.core.roles.crud import crud_role
from app.core.roles.schemas import (
    RoleCreateSchema,
    RoleUpdateSchema,
    RoleResponseSchema,
)
from app.core.schemas import ApiResponse, PaginatedResponse

router = APIRouter(prefix="/roles", tags=["Roles"])


# ✅ Чтение — требуется только авторизация
@router.get("/", response_model=ApiResponse[PaginatedResponse[RoleResponseSchema]])
async def get_roles(
    skip: int = 0,
    limit: int = 10,
    search: str | None = None,
    current_session: CurrentUser,  # ✅ Аннотированный тип
    db: DBSession,
):
    items, total = await crud_role.get_multi_paginated(
        db,
        tenant_id=current_session.tenant_id,
        skip=skip,
        limit=limit,
        search=search,
        user_is_superadmin=current_session.is_superadmin,
    )
    return ApiResponse(
        success=True,
        message="Роли получены",
        data=cast(
            PaginatedResponse[RoleResponseSchema],
            PaginatedResponse(
                items=[RoleResponseSchema.model_validate(item) for item in items],
                total=total,
                skip=skip,
                limit=limit,
            ),
        ),
    )


# ✅ Создание — требуется суперадмин
@router.post("/", response_model=ApiResponse[RoleResponseSchema], status_code=201)
async def create_role(
    obj_in: RoleCreateSchema,
    current_session: SuperAdminUser,  # ✅ Аннотированный тип
    db: DBSession,
):
    # ✅ current_session "используется" через тип — анализатор не ругается
    obj = await crud_role.create(
        db,
        obj_in=obj_in,
        tenant_id=current_session.tenant_id,
        user_is_superadmin=True,
    )
    return ApiResponse(
        success=True,
        message="Роль создана",
        data=RoleResponseSchema.model_validate(obj),
    )


# ✅ Обновление — требуется суперадмин
@router.put("/{role_id}", response_model=ApiResponse[RoleResponseSchema])
async def update_role(
    role_id: uuid.UUID,
    obj_in: RoleUpdateSchema,
    current_session: SuperAdminUser,
    db: DBSession,
):
    db_obj = await crud_role.get(db, id=role_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Роль не найдена")
    
    updated_obj = await crud_role.update(
        db,
        db_obj=db_obj,
        obj_in=obj_in,
        tenant_id=current_session.tenant_id,
        user_is_superadmin=True,
    )
    return ApiResponse(
        success=True,
        message="Роль обновлена",
        data=RoleResponseSchema.model_validate(updated_obj),
    )


# ✅ Удаление — требуется суперадмин
@router.delete("/{role_id}", response_model=ApiResponse[RoleResponseSchema])
async def delete_role(
    role_id: uuid.UUID,
    current_session: SuperAdminUser,
    db: DBSession,
):
    deleted_obj = await crud_role.remove(db, id=role_id)
    if not deleted_obj:
        raise HTTPException(status_code=404, detail="Роль не найдена")
    
    return ApiResponse(
        success=True,
        message="Роль удалена",
        data=RoleResponseSchema.model_validate(deleted_obj),
    )
```

#### ❌ НЕПРАВИЛЬНО: Старый синтаксис с `Depends(...)` в значении по умолчанию

```python
# ❌ ОШИБКА: Прямое использование Depends в значении по умолчанию
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.auth.dependencies import get_current_session, require_superadmin, UserSession

@router.post("/", response_model=ApiResponse[RoleResponseSchema])
async def create_role(
    obj_in: RoleCreateSchema,
    current_session: UserSession = Depends(require_superadmin),  # ❌ Старый синтаксис
    db: AsyncSession = Depends(get_db),  # ❌ Старый синтаксис
):
    # 💥 Pyright предупреждение: "current_session" is not accessed
    # 💥 Pyright предупреждение: Type annotation is missing for parameter "current_session"
    ...
```

**Почему это плохо:**
1. Анализатор видит, что `current_session` объявлен, но не используется в теле функции
2. Нет явной связи между типом и зависимостью
3. При изменении зависимости нужно править каждый роутер
4. Код менее читаем и более многословен

#### ❌ НЕПРАВИЛЬНО: Отсутствие аннотации типа

```python
# ❌ ОШИБКА: Параметр без аннотации типа
@router.post("/")
async def create_role(
    obj_in: RoleCreateSchema,
    current_session = Depends(require_superadmin),  # ❌ Нет типа!
    db = Depends(get_db),  # ❌ Нет типа!
):
    ...
```
*Почему это плохо:* Pyright выдаёт `"Type of parameter 'current_session' is unknown"`.

---

### 4. Нюансы и лучшие практики

#### 4.1. Группировка алиасов
Все алиасы типов **ОБЯЗАТЕЛЬНО** должны быть объявлены в одном месте — в конце файла `dependencies.py`, после всех функций-зависимостей. Это упрощает навигацию и импорт.

#### 4.2. Именование алиасов
Имена алиасов должны быть **семантически понятными**:
- ✅ `SuperAdminUser` — явно указывает на требование прав суперадмина
- ✅ `CurrentUser` — любой авторизованный пользователь
- ✅ `DBSession` — сессия базы данных
- ❌ `UserDep`, `SessionDep`, `AdminDep` — непонятные сокращения

#### 4.3. Комбинирование зависимостей
Если нужна сложная зависимость (например, "пользователь с правом редактирования"), создавайте отдельную функцию и алиас:

```python
async def require_editor(
    current_session: UserSession = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
) -> UserSession:
    """Пользователь с правом редактирования."""
    # Проверка прав через роли
    ...
    return current_session

EditorUser = Annotated[UserSession, Depends(require_editor)]
```

#### 4.4. Использование в тестах
В тестах `Annotated` работает так же, как обычный `Depends`. Можно переопределять зависимости через `app.dependency_overrides`:

```python
# test_roles.py
from fastapi.testclient import TestClient
from app.main import app
from app.core.auth.dependencies import get_current_session, UserSession

# Переопределяем зависимость для теста
def override_get_current_session():
    return UserSession(mock_user)

app.dependency_overrides[get_current_session] = override_get_current_session

client = TestClient(app)
response = client.get("/api/v1/roles/")
```

#### 4.5. Связь с другими правилами

**Правило №1 (Чистая архитектура):** Алиасы типов помогают чётко разделить слои — зависимости безопасности находятся в `dependencies.py`, а не "размазаны" по роутерам.

**Правило №4 (Orval-совместимость):** Корректные типы зависимостей обеспечивают правильную OpenAPI-спецификацию, что критично для генерации клиентов Orval.

**Правило №26 (Безопасность multi-tenancy):** Алиас `SuperAdminUser` гарантирует, что суперадмин-проверка выполнена до входа в тело функции.

**Правило №31 (Приоритет CRUDBase):** Алиасы `DBSession` и `CurrentUser` используются при вызове методов CRUD.

---

### 5. Миграция существующего кода

Для перехода со старого синтаксиса на `Annotated`:

**Шаг 1.** Добавьте алиасы в `dependencies.py`:
```python
SuperAdminUser = Annotated[UserSession, Depends(require_superadmin)]
CurrentUser = Annotated[UserSession, Depends(get_current_session)]
DBSession = Annotated[AsyncSession, Depends(get_db)]
```

**Шаг 2.** Замените во всех роутерах:
```python
# Было:
current_session: UserSession = Depends(require_superadmin)
db: AsyncSession = Depends(get_db)

# Стало:
current_session: SuperAdminUser
db: DBSession
```

**Шаг 3.** Удалите прямые импорты `Depends`, `get_current_session`, `require_superadmin`, `get_db` из роутеров — они больше не нужны.

---

### 6. Чек-лист для разработчика

При создании или рефакторинге роутера проверьте:

**Алиасы типов:**
- [ ] Созданы ли алиасы `SuperAdminUser`, `CurrentUser`, `DBSession` в `dependencies.py`?
- [ ] Используют ли алиасы `Annotated[T, Depends(...)]`?
- [ ] Имена алиасов семантически понятны?

**Использование в роутерах:**
- [ ] Все параметры безопасности объявлены через алиасы (`current_session: SuperAdminUser`)?
- [ ] Отсутствуют ли прямые вызовы `Depends(...)` в сигнатурах функций?
- [ ] Все параметры имеют явные аннотации типов?
- [ ] Импортируются ли алиасы из `app.core.auth.dependencies`?

**Анализатор кода:**
- [ ] Отсутствуют ли предупреждения `"is not accessed"`?
- [ ] Отсутствуют ли предупреждения `"Type annotation is missing"`?
- [ ] Отсутствуют ли предупреждения `"Type of parameter is unknown"`?

**Тестирование:**
- [ ] Работает ли `app.dependency_overrides` для тестов?
- [ ] Корректно ли отображаются зависимости в Swagger UI?

---

### 7. Таблица соответствий

| Ситуация | Алиас | Пример использования |
| :--- | :--- | :--- |
| Публичный эндпоинт (без авторизации) | — | `async def register(...)` |
| Любой авторизованный пользователь | `CurrentUser` | `async def get_roles(current_session: CurrentUser, ...)` |
| Только суперадмин | `SuperAdminUser` | `async def create_role(current_session: SuperAdminUser, ...)` |
| Сессия БД | `DBSession` | `async def get_roles(..., db: DBSession)` |
| Комбинированная проверка | `EditorUser` | `async def edit_item(user: EditorUser, ...)` |

---

### 8. Итоговое размещение в структуре правил

Правило №32 добавляется в **ЧАСТЬ 1. АРХИТЕКТУРА И BACKEND**, после Правила №31.

---

Следование этому правилу гарантирует, что:
✅ Код роутеров будет чистым и типобезопасным
✅ Анализаторы (Pyright/MyPy) не будут выдавать ложные предупреждения
✅ Все зависимости безопасности будут централизованы в `dependencies.py`
✅ Swagger UI будет корректно отображать зависимости
✅ Миграция на новые версии FastAPI будет простой

Это правило работает в связке с Правилами №1 (Чистая архитектура), №4 (Orval-совместимость), №26 (Безопасность multi-tenancy) и №31 (Приоритет CRUDBase), формируя единый стандарт API-дизайна проекта Cool ERP.