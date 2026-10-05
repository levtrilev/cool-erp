# Правило №4: Orval-совместимость (Backend)

Все эндпоинты бэкенда **ОБЯЗАТЕЛЬНО** должны возвращать данные в формате, совместимом с автоматически сгенерированными клиентами Orval на фронтенде. Это означает использование стандартных обёрток `ApiResponse` и `PaginatedResponse`, а также явную конвертацию ORM-объектов в Pydantic-схемы через `.model_validate()`.

**СТРОГИЕ ТРЕБОВАНИЯ:**
* Все эндпоинты, возвращающие списки, **ОБЯЗАТЕЛЬНО** используют `PaginatedResponse[Schema]`
* Для обёртки успеха используется `ApiResponse[Schema]` с полями `success`, `message`, `data`
* Явная конвертация ORM → Pydantic через `.model_validate()`
* **ЗАПРЕЩЕНО** возвращать "сырые" ORM-объекты или словари

---

### 1. Обоснование (Почему это важно)

1. **Типобезопасность фронтенда:** Orval генерирует TypeScript-типы на основе OpenAPI-специации. Если бэкенд возвращает данные в нестандартном формате, фронтенд теряет типобезопасность, и разработчики вынуждены писать ручные маппинги.
2. **Единообразие API:** Все эндпоинты возвращают одинаковую структуру (`{success, message, data}`), что упрощает обработку ответов на фронтенде. Не нужно писать разные обработчики для разных эндпоинтов.
3. **Автоматическая пагинация:** `PaginatedResponse` содержит не только элементы, но и метаданные (`total`, `skip`, `limit`), что позволяет фронтенду автоматически строить пагинацию без дополнительных запросов.
4. **Семантическая ясность:** Поле `success: boolean` явно указывает, успешна ли операция, а `message` содержит человекочитаемое описание. Это упрощает отладку и логирование.
5. **Защита от утечек ORM-структуры:** Явная конвертация через `.model_validate()` гарантирует, что в ответ попадут только те поля, которые объявлены в Pydantic-схеме. Случайно "протащить" внутреннее поле ORM (например, `hashed_password`) невозможно.

---

### 2. Обязательные требования к реализации

#### 2.1. Стандартные обёртки ответов
В проекте определены две базовые схемы в `backend/app/core/schemas.py`:

**`ApiResponse[T]`** — универсальная обёртка для всех ответов:
```python
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None
```

**`PaginatedResponse[T]`** — обёртка для списков с пагинацией:
```python
from typing import Generic, TypeVar, List
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    skip: int
    limit: int
```

#### 2.2. Использование обёрток в роутерах
Каждый роутер **ОБЯЗАТЕЛЬНО** должен возвращать ответ в формате `ApiResponse[...]`:
* Для списков: `ApiResponse[PaginatedResponse[ItemResponseSchema]]`
* Для одного объекта: `ApiResponse[ItemResponseSchema]`
* Для операций без данных (удаление): `ApiResponse[ItemResponseSchema]` или `ApiResponse[None]`

#### 2.3. Явная конвертация ORM → Pydantic
**КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО** возвращать ORM-объекты напрямую. Каждая запись **ОБЯЗАТЕЛЬНО** должна быть сконвертирована через `.model_validate()`:

```python
# ✅ ПРАВИЛЬНО
return ApiResponse(
    success=True,
    message="Роль создана",
    data=RoleResponseSchema.model_validate(role)
)

# ❌ НЕПРАВИЛЬНО
return role  # ❌ ORM-объект
return {"id": role.id, "name": role.name}  # ❌ Ручной словарь
```

#### 2.4. Конвертация списков
При возврате списка каждая запись конвертируется отдельно:
```python
return ApiResponse(
    success=True,
    message="Роли получены",
    data=PaginatedResponse(
        items=[RoleResponseSchema.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )
)
```

---

### 3. Примеры кода

#### ✅ ПРАВИЛЬНО: Эндпоинт получения списка

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import cast

from app.core.database import get_db
from app.core.schemas import ApiResponse, PaginatedResponse
from app.core.roles.crud import crud_role
from app.core.roles.schemas import RoleResponseSchema
from app.core.auth.dependencies import get_current_session

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/", response_model=ApiResponse[PaginatedResponse[RoleResponseSchema]])
async def get_roles(
    skip: int = 0,
    limit: int = 10,
    search: str | None = None,
    current_session=Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    # 1. Получаем данные из CRUD
    items, total = await crud_role.get_multi(
        db,
        skip=skip,
        limit=limit,
        search=search,
        current_tenant_id=current_session.tenant_id,
        is_superadmin=current_session.is_superadmin,
    )
    
    # 2. ✅ Явная конвертация каждой записи
    paginated_data = cast(
        PaginatedResponse[RoleResponseSchema],
        PaginatedResponse(
            items=[RoleResponseSchema.model_validate(item) for item in items],
            total=total,
            skip=skip,
            limit=limit,
        )
    )
    
    # 3. ✅ Обёртка в ApiResponse
    return ApiResponse(
        success=True,
        message="Роли успешно получены",
        data=paginated_data,
    )
```

#### ✅ ПРАВИЛЬНО: Эндпоинт создания записи

```python
@router.post("/", response_model=ApiResponse[RoleResponseSchema], status_code=201)
async def create_role(
    data: RoleCreateSchema,
    current_session=Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    # 1. Создаём запись через CRUD
    role = await crud_role.create(
        db,
        data=data,
        current_tenant_id=current_session.tenant_id,
        is_superadmin=current_session.is_superadmin,
    )
    
    # 2. ✅ Конвертация и обёртка
    return ApiResponse(
        success=True,
        message="Роль успешно создана",
        data=RoleResponseSchema.model_validate(role),
    )
```

#### ✅ ПРАВИЛЬНО: Эндпоинт получения одной записи

```python
@router.get("/{role_id}", response_model=ApiResponse[RoleResponseSchema])
async def get_role(
    role_id: uuid.UUID,
    current_session=Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
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
```

#### ✅ ПРАВИЛЬНО: Эндпоинт удаления

```python
@router.delete("/{role_id}", response_model=ApiResponse[RoleResponseSchema])
async def delete_role(
    role_id: uuid.UUID,
    current_session=Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    role = await crud_role.delete(
        db,
        item_id=role_id,
        current_tenant_id=current_session.tenant_id,
        is_superadmin=current_session.is_superadmin,
    )
    
    return ApiResponse(
        success=True,
        message="Роль успешно удалена",
        data=RoleResponseSchema.model_validate(role),
    )
```

#### ❌ НЕПРАВИЛЬНО: Возврат ORM-объекта напрямую

```python
# ❌ ГРУБОЕ НАРУШЕНИЕ ПРАВИЛА №4
@router.get("/", response_model=list[RoleResponseSchema])
async def get_roles(db: AsyncSession = Depends(get_db)):
    roles = await db.execute(select(RoleModel))
    # ❌ Возвращаем ORM-объекты напрямую — Orval не сможет правильно сгенерировать типы
    return roles.scalars().all()
```
*Почему это плохо:* 
1. Нет обёртки `ApiResponse` — фронтенд не сможет единообразно обрабатывать ответы.
2. Нет `PaginatedResponse` — фронтенд не получит `total`, `skip`, `limit` для пагинации.
3. Orval сгенерирует тип `RoleResponseSchema[]` вместо `ApiResponse<PaginatedResponse<RoleResponseSchema>>`, что сломает всю логику работы со списками.

#### ❌ НЕПРАВИЛЬНО: Возврат словаря

```python
# ❌ ГРУБОЕ НАРУШЕНИЕ ПРАВИЛА №4
@router.get("/{role_id}")
async def get_role(role_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    role = await db.get(RoleModel, role_id)
    # ❌ Ручной словарь — потеря типобезопасности, риск утечки полей
    return {
        "id": str(role.id),
        "name": role.name,
        "description": role.description,
        "hashed_password": role.hashed_password,  # 💥 УТЕЧКА СЕКРЕТНЫХ ДАННЫХ!
    }
```
*Почему это плохо:*
1. Нет обёртки `ApiResponse`.
2. Ручной словарь легко ошибиться — можно забыть поле или случайно добавить секретное.
3. Pydantic-валидация не выполняется — в ответ может попасть невалидное значение.
4. Orval не сможет корректно сгенерировать типы.

#### ❌ НЕПРАВИЛЬНО: Отсутствие `PaginatedResponse` для списка

```python
# ❌ ОШИБКА: Список без пагинации
@router.get("/", response_model=ApiResponse[list[RoleResponseSchema]])
async def get_roles(db: AsyncSession = Depends(get_db)):
    roles = await db.execute(select(RoleModel))
    items = [RoleResponseSchema.model_validate(r) for r in roles.scalars().all()]
    
    # ❌ Нет total, skip, limit — фронтенд не сможет построить пагинацию
    return ApiResponse(
        success=True,
        message="Роли получены",
        data=items,
    )
```
*Почему это плохо:* Фронтенд не знает общее количество записей и не может корректно отображать пагинацию. Придётся делать дополнительный запрос или загружать все данные сразу.

#### ❌ НЕПРАВИЛЬНО: Отсутствие `.model_validate()`

```python
# ❌ ОШИБКА: Пропущена конвертация
@router.get("/{role_id}", response_model=ApiResponse[RoleResponseSchema])
async def get_role(role_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    role = await db.get(RoleModel, role_id)
    
    # ❌ Передаём ORM-объект напрямую в data
    return ApiResponse(
        success=True,
        message="Роль получена",
        data=role,  # ❌ Должно быть RoleResponseSchema.model_validate(role)
    )
```
*Почему это плохо:* FastAPI попытается сериализовать ORM-объект напрямую, что может привести к ошибкам (например, `datetime` не сериализуется в JSON без настройки) или утечке лишних полей.

---

### 4. Нюансы и лучшие практики

#### 4.1. Использование `cast()` для типизации
При создании `PaginatedResponse` внутри `ApiResponse` TypeScript (и Pyright) может не понять вложенную дженерик-структуру. Используйте `cast()` для явного указания типа:

```python
from typing import cast

paginated_data = cast(
    PaginatedResponse[RoleResponseSchema],
    PaginatedResponse(
        items=[RoleResponseSchema.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )
)
```

#### 4.2. Сообщения (`message`)
Сообщение в `ApiResponse` **ОБЯЗАТЕЛЬНО** должно быть:
* **Человекочитаемым** — пользователь может увидеть его в UI
* **Информативным** — описывать результат операции
* **На русском языке** — так как приложение для русскоязычных пользователей

✅ **Правильно:**
* `"Роли успешно получены"`
* `"Роль создана"`
* `"Роль не найдена"`

❌ **Неправильно:**
* `"OK"` (слишком абстрактно)
* `"Success"` (на английском)
* `""` (пустая строка)
* `"Error 500"` (техническое сообщение)

#### 4.3. HTTP-коды
Используйте стандартные HTTP-коды:
* `200 OK` — успешное чтение или обновление
* `201 Created` — успешное создание
* `204 No Content` — успешное удаление (если не возвращаем данные)
* `400 Bad Request` — ошибка валидации
* `401 Unauthorized` — нет токена
* `403 Forbidden` — нет прав
* `404 Not Found` — запись не найдена
* `500 Internal Server Error` — внутренняя ошибка

```python
@router.post("/", response_model=ApiResponse[RoleResponseSchema], status_code=201)
async def create_role(...):
    # ✅ 201 для создания
    return ApiResponse(...)
```

#### 4.4. Обработка ошибок
Ошибки **ОБЯЗАТЕЛЬНО** должны возвращаться через `HTTPException`, а не через `ApiResponse(success=False)`:

```python
# ✅ ПРАВИЛЬНО: Ошибка через HTTPException
if not role:
    raise HTTPException(status_code=404, detail="Роль не найдена")

# ❌ НЕПРАВИЛЬНО: Ошибка через ApiResponse
return ApiResponse(
    success=False,
    message="Роль не найдена",
    data=None,
)  # ❌ Это вернёт HTTP 200, что неправильно
```

#### 4.5. Связь с Orval
Orval автоматически распознаёт структуру `ApiResponse` и `PaginatedResponse`, если они правильно описаны в OpenAPI-спецификации (через `response_model`). На фронтенде это будет выглядеть так:

```typescript
// Orval сгенерирует такой тип:
interface ApiResponsePaginatedResponseOfRoleResponseSchema {
  success: boolean;
  message: string;
  data?: PaginatedResponseRoleResponseSchema;
}

interface PaginatedResponseRoleResponseSchema {
  items: RoleResponseSchema[];
  total: number;
  skip: number;
  limit: number;
}
```

Использование на фронтенде:
```typescript
const { data } = useReadRolesRolesGet({ skip: 0, limit: 10 });

// ✅ Типобезопасный доступ к данным
const roles = data?.data?.items || [];
const total = data?.data?.total || 0;
```

#### 4.6. Связь с Правилом №1 (Чистая архитектура)
Правило №4 тесно связано с Правилом №1:
* **Правило №1** требует использовать `@property` в ORM-модели и `from_attributes=True` в Pydantic-схемах.
* **Правило №4** требует использовать `.model_validate()` для конвертации.

Вместе они обеспечивают чистое разделение слоёв: ORM → Pydantic → JSON.

#### 4.7. Связь с Правилом №21 (Именование Pydantic-схем)
Все Pydantic-схемы должны заканчиваться на `Schema`, что позволяет Orval корректно генерировать TypeScript-типы:
```python
class RoleResponseSchema(BaseModel): ...  # ✅ Суффикс Schema
```

#### 4.8. Связь с Правилом №26 (Безопасность multi-tenancy)
Даже при использовании `ApiResponse` и `PaginatedResponse` **ОБЯЗАТЕЛЬНО** фильтровать данные по `tenant_id` (Правило №26). Обёртка ответа не заменяет проверку безопасности.

---

### 5. Типичные ошибки и их исправление

| Ошибка | Исправление |
| :--- | :--- |
| Возврат ORM-объекта напрямую | `RoleResponseSchema.model_validate(role)` |
| Возврат словаря `{"id": role.id, ...}` | Использовать Pydantic-схему + `.model_validate()` |
| Отсутствие `ApiResponse` | Обернуть ответ в `ApiResponse(success=True, ...)` |
| Отсутствие `PaginatedResponse` для списка | Использовать `PaginatedResponse(items=..., total=..., skip=..., limit=...)` |
| Ошибка через `ApiResponse(success=False)` | Использовать `HTTPException(status_code=404, ...)` |
| Пустое или техническое `message` | Писать человекочитаемое сообщение на русском |
| Отсутствие `status_code=201` для создания | Добавить `status_code=201` в декоратор роутера |

---

### 6. Чек-лист для разработчика

При создании или рефакторинге любого эндпоинта проверьте:

**Структура ответа:**
- [ ] Возвращается ли `ApiResponse[...]`?
- [ ] Для списков используется `PaginatedResponse[Schema]`?
- [ ] Есть ли поля `success`, `message`, `data` в ответе?
- [ ] Для списков есть ли поля `items`, `total`, `skip`, `limit`?

**Конвертация данных:**
- [ ] Каждая ORM-запись конвертируется через `.model_validate()`?
- [ ] Отсутствуют ли ручные словари `{"id": obj.id, ...}`?
- [ ] Отсутствует ли возврат "сырых" ORM-объектов?

**HTTP-коды:**
- [ ] Для создания указан `status_code=201`?
- [ ] Для ошибок используется `HTTPException` (а не `ApiResponse(success=False)`)?
- [ ] Коды соответствуют стандартам (200, 201, 400, 401, 403, 404, 500)?

**Сообщения:**
- [ ] Поле `message` заполнено человекочитаемым текстом?
- [ ] Сообщения на русском языке?
- [ ] Сообщения информативны (описывают результат операции)?

**Типизация:**
- [ ] Указан ли `response_model` в декораторе роутера?
- [ ] Используется ли `cast()` для вложенных дженериков?
- [ ] Совпадает ли `response_model` с фактическим возвращаемым типом?

**Безопасность:**
- [ ] Применяется ли фильтрация по `tenant_id` (Правило №26)?
- [ ] Не попадают ли в ответ секретные поля (пароли, токены)?

**Orval-совместимость:**
- [ ] Перегенерирован ли Orval после изменения `response_model`?
- [ ] Корректно ли работают хуки на фронтенде (`useReadRolesRolesGet`)?

---

### 7. Таблица соответствий

| Тип операции | response_model | HTTP-код | Пример message |
| :--- | :--- | :--- | :--- |
| Получение списка | `ApiResponse[PaginatedResponse[ItemResponseSchema]]` | 200 | `"Записи успешно получены"` |
| Получение одной записи | `ApiResponse[ItemResponseSchema]` | 200 | `"Запись получена"` |
| Создание записи | `ApiResponse[ItemResponseSchema]` | 201 | `"Запись успешно создана"` |
| Обновление записи | `ApiResponse[ItemResponseSchema]` | 200 | `"Запись успешно обновлена"` |
| Удаление записи | `ApiResponse[ItemResponseSchema]` | 200 | `"Запись успешно удалена"` |
| Ошибка (не найдено) | `HTTPException` | 404 | `"Запись не найдена"` |
| Ошибка (нет прав) | `HTTPException` | 403 | `"Недостаточно прав"` |

---

Следование этому правилу гарантирует, что API Cool ERP будет:
✅ **Orval-совместимым** — фронтенд автоматически получает типобезопасные клиенты
✅ **Единообразным** — все эндпоинты возвращают данные в одинаковом формате
✅ **Безопасным** — явная конвертация предотвращает утечку ORM-полей
✅ **Информативным** — `success` и `message` дают понятную обратную связь
✅ **Масштабируемым** — добавление новых эндпоинтов не требует изобретения новых форматов ответов

Это правило работает в связке с Правилами №1 (Чистая архитектура), №3 (Версионирование), №21 (Именование схем), №26 (Безопасность multi-tenancy) и Правилом №9 (Orval-хуки на фронтенде), формируя единый стандарт API-дизайна от бэкенда до фронтенда.