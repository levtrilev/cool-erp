# Правило №5: Именование роутов

Все API-эндпоинты в проекте **ОБЯЗАТЕЛЬНО** должны следовать строгой системе именования, разделяющей публичные (незащищённые) и внутренние (защищённые) маршруты, а также использовать консистентные префиксы для каждого домена.

**СТРОГИЕ ТРЕБОВАНИЯ:**
* **Публичные эндпоинты** (регистрация, восстановление пароля, публичные справочники): `/public/register`, `/public/restore-password`
* **Внутренние эндпоинты** (для авторизованных пользователей): `/register`, `/restore-password`, `/me`, `/roles/`
* **Префиксы роутеров** — во множественном числе: `/auth`, `/tenants`, `/users`, `/roles`, `/permissions`, `/sections`, `/doctypes`

---

### 1. Обоснование (Почему это важно)

1. **Безопасность:** Чёткое разделение публичных и защищённых маршрутов позволяет легко настраивать middleware аутентификации. Все эндпоинты без префикса `/public/` автоматически требуют валидный JWT-токен.
2. **Аудит и мониторинг:** В логах сервера и системах мониторинга (Prometheus, Grafana) сразу видно, какие эндпоинты доступны анонимно, а какие требуют авторизации.
3. **Предсказуемость API:** Разработчик фронтенда, зная префикс `/public/`, понимает, что для вызова этого эндпоинта не нужен токен авторизации.
4. **Соответствие REST-стандартам:** Префиксы во множественном числе (`/roles`, `/users`) соответствуют REST-архитектуре, где URL представляет коллекцию ресурсов.
5. **Защита от ошибок:** Единая система именования исключает ситуации, когда один разработчик создаёт `/role/`, а другой — `/roles/`, что приводит к дублированию и путанице.

---

### 2. Обязательные требования к реализации

#### 2.1. Публичные эндпоинты (без авторизации)
Все эндпоинты, доступные **без JWT-токена**, **ОБЯЗАТЕЛЬНО** должны иметь префикс `/public/`:
* Регистрация: `/public/register`
* Восстановление пароля: `/public/restore-password`
* Подтверждение email: `/public/verify-email`
* Публичные справочники (если есть): `/public/doctypes`

#### 2.2. Внутренние эндпоинты (с авторизацией)
Все эндпоинты, требующие авторизации, **НЕ ДОЛЖНЫ** иметь префикс `/public/`:
* Текущий пользователь: `/me`
* Список ролей: `/roles/`
* Создание пользователя: `/users/`
* Обновление тенанта: `/tenants/{id}`

#### 2.3. Префиксы роутеров
Префиксы роутеров **ОБЯЗАТЕЛЬНО** должны:
* Быть во множественном числе (Правило №7)
* Использовать нижний регистр
* Не содержать суффиксов с именем сущности
* Соответствовать имени домена

✅ **Правильно:** `/auth`, `/tenants`, `/users`, `/roles`, `/permissions`, `/sections`, `/doctypes`
❌ **Неправильно:** `/tenant`, `/user`, `/role`, `/users-list`, `/api-roles`

#### 2.4. Версионирование
Версия API задаётся **ТОЛЬКО** через `prefix="/api/v1"` в `main.py` (Правило №3). Роутеры не знают о версии:

```python
# ✅ ПРАВИЛЬНО: Версия задаётся в main.py
app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(roles_router, prefix="/api/v1/roles")

# ❌ НЕПРАВИЛЬНО: Версия внутри роутера
router = APIRouter(prefix="/api/v1/roles")  # ❌ Роутер не должен знать о версии
```

---

### 3. Примеры кода

#### ✅ ПРАВИЛЬНО: Структура роутеров

**Аутентификация (`backend/app/core/auth/router.py`):**
```python
from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["Auth"])

# ✅ Публичный эндпоинт — регистрация
@router.post("/public/register")
async def public_register(data: RegisterSchema, db: AsyncSession = Depends(get_db)):
    # Логика регистрации без авторизации
    pass

# ✅ Публичный эндпоинт — восстановление пароля
@router.post("/public/restore-password")
async def public_restore_password(data: RestorePasswordSchema, db: AsyncSession = Depends(get_db)):
    pass

# ✅ Внутренний эндпоинт — текущий пользователь (требует авторизации)
@router.get("/me")
async def get_current_user(
    current_user: UserModel = Depends(get_current_session),
):
    return current_user

# ✅ Внутренний эндпоинт — смена пароля
@router.post("/change-password")
async def change_password(
    data: ChangePasswordSchema,
    current_user: UserModel = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
):
    pass
```

**Роли (`backend/app/core/roles/router.py`):**
```python
from fastapi import APIRouter

# ✅ Префикс во множественном числе
router = APIRouter(prefix="/roles", tags=["Roles"])

# ✅ Все эндпоинты ролей — внутренние (требуют авторизации)
@router.get("/", response_model=ApiResponse[PaginatedResponse[RoleResponseSchema]])
async def get_roles(...):
    pass

@router.post("/save", response_model=ApiResponse[RoleResponseSchema])
async def save_role(...):
    pass

@router.delete("/{role_id}", response_model=ApiResponse[RoleResponseSchema])
async def delete_role(...):
    pass
```

**Регистрация в `main.py`:**
```python
from fastapi import FastAPI
from app.core.auth.router import router as auth_router
from app.core.roles.router import router as roles_router
from app.core.users.router import router as users_router
from app.core.tenants.router import router as tenants_router
from app.core.permissions.router import router as permissions_router
from app.core.sections.router import router as sections_router
from app.core.doctypes.router import router as doctypes_router

app = FastAPI(title="Cool ERP", version="1.0.0")

# ✅ Версия задаётся ТОЛЬКО здесь, в main.py
app.include_router(auth_router, prefix="/api/v1")
app.include_router(roles_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(tenants_router, prefix="/api/v1")
app.include_router(permissions_router, prefix="/api/v1")
app.include_router(sections_router, prefix="/api/v1")
app.include_router(doctypes_router, prefix="/api/v1")
```

**Итоговая карта URL:**
```
POST   /api/v1/auth/public/register          ← Публичный (без JWT)
POST   /api/v1/auth/public/restore-password  ← Публичный (без JWT)
GET    /api/v1/auth/me                       ← Внутренний (с JWT)
POST   /api/v1/auth/change-password          ← Внутренний (с JWT)

GET    /api/v1/roles/                        ← Внутренний (с JWT)
POST   /api/v1/roles/save                    ← Внутренний (с JWT)
DELETE /api/v1/roles/{role_id}               ← Внутренний (с JWT)

GET    /api/v1/users/                        ← Внутренний (с JWT)
POST   /api/v1/users/                        ← Внутренний (с JWT)

GET    /api/v1/tenants/                      ← Внутренний (с JWT)
POST   /api/v1/tenants/                      ← Внутренний (с JWT)

GET    /api/v1/permissions/                  ← Внутренний (с JWT)
GET    /api/v1/sections/                     ← Внутренний (с JWT)
GET    /api/v1/doctypes/                     ← Внутренний (с JWT)
```

#### ❌ НЕПРАВИЛЬНО: Нарушения правила

**1. Отсутствие префикса `/public/` для публичных эндпоинтов:**
```python
# ❌ ОШИБКА: Регистрация без префикса /public/
@router.post("/register")  # ❌ Должно быть /public/register
async def register(data: RegisterSchema):
    pass
```
*Почему это плохо:* Middleware аутентификации может случайно заблокировать этот эндпоинт, или наоборот — публичный эндпоинт останется без защиты, если middleware настроен на блокировку всех маршрутов без `/public/`.

**2. Префикс роутера в единственном числе:**
```python
# ❌ ОШИБКА: Префикс в единственном числе
router = APIRouter(prefix="/role", tags=["Role"])  # ❌ Должно быть /roles

@router.get("/")
async def get_roles():
    pass
```
*Почему это плохо:* Нарушает REST-стандарты и Правило №7. URL `/role` подразумевает один объект, а эндпоинт возвращает список.

**3. Версия внутри роутера:**
```python
# ❌ ОШИБКА: Роутер знает о версии API
router = APIRouter(prefix="/api/v1/roles")  # ❌ Версия должна быть в main.py

@router.get("/")
async def get_roles():
    pass
```
*Почему это плохо:* При переходе на v2 придётся менять все роутеры. Версия должна задаваться централизованно.

**4. Смешение публичных и внутренних эндпоинтов:**
```python
# ❌ ОШИБКА: Публичный и внутренний эндпоинты в одном роутере без разделения
router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/public/info")  # ❌ Не должно быть /public/ внутри /users
async def public_user_info():
    pass

@router.get("/")
async def get_users():
    pass
```
*Почему это плохо:* Нарушает семантику. Публичные эндпоинты должны быть в своём роутере (например, `/auth/public/`), а не разбросаны по доменам.

**5. Использование суффиксов в префиксе:**
```python
# ❌ ОШИБКА: Суффиксы в префиксе
router = APIRouter(prefix="/users-list")   # ❌ Должно быть /users
router = APIRouter(prefix="/api-roles")    # ❌ Должно быть /roles
router = APIRouter(prefix="/tenant-mgmt")  # ❌ Должно быть /tenants
```
*Почему это плохо:* Избыточные суффиксы затрудняют навигацию по API и не соответствуют REST-стандартам.

---

### 4. Нюансы и лучшие практики

#### 4.1. Middleware аутентификации
Middleware должен проверять наличие JWT-токена для всех маршрутов, **КРОМЕ** тех, что начинаются с `/public/`:

```python
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # ✅ Публичные эндпоинты пропускаем без проверки токена
    if request.url.path.startswith("/api/v1/auth/public/"):
        return await call_next(request)
    
    # ✅ Для всех остальных — проверяем JWT
    token = request.headers.get("Authorization")
    if not token:
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
    
    return await call_next(request)
```

#### 4.2. Группировка публичных эндпоинтов
Если публичных эндпоинтов много, их можно вынести в отдельный роутер:

```python
# backend/app/core/auth/public_router.py
from fastapi import APIRouter

public_router = APIRouter(prefix="/auth/public", tags=["Auth Public"])

@public_router.post("/register")
async def register(...):
    pass

@public_router.post("/restore-password")
async def restore_password(...):
    pass

# В main.py:
app.include_router(public_router, prefix="/api/v1")
```

#### 4.3. Swagger UI и документация
Используйте `tags` для группировки эндпоинтов в Swagger UI:
```python
router = APIRouter(prefix="/roles", tags=["Roles"])  # ✅ Группа "Roles" в Swagger
```
Это позволяет разработчикам фронтенда быстро находить нужные эндпоинты в документации.

#### 4.4. Именование параметров URL
Параметры URL **ОБЯЗАТЕЛЬНО** должны использовать `snake_case`:
```python
# ✅ ПРАВИЛЬНО: snake_case
@router.get("/{role_id}")
async def get_role(role_id: uuid.UUID):
    pass

# ❌ НЕПРАВИЛЬНО: camelCase или другие стили
@router.get("/{roleId}")  # ❌ Должно быть role_id
async def get_role(roleId: uuid.UUID):
    pass
```

#### 4.5. HTTP-методы
Соблюдайте стандартные HTTP-методы:
* `GET` — чтение (список или один объект)
* `POST` — создание
* `PUT` — полное обновление
* `PATCH` — частичное обновление
* `DELETE` — удаление

Для агрегирующих операций (например, сохранение роли с полномочиями) допускается использование `POST` с описательным именем:
```python
@router.post("/save")  # ✅ Агрегирующая операция
async def save_role(...):
    pass
```

#### 4.6. Связь с Правилом №7 (Множественное число)
Префиксы роутеров всегда во множественном числе, так как представляют **коллекцию** ресурсов:
* `/roles` — коллекция ролей
* `/users` — коллекция пользователей
* `/tenants` — коллекция организаций

Даже если эндпоинт работает с одним объектом (`GET /roles/{id}`), URL остаётся во множественном числе, так как мы обращаемся к элементу коллекции.

#### 4.7. Связь с Правилом №3 (Версионирование)
Версия API (`/api/v1`) задаётся **ТОЛЬКО** в `main.py`. Роутеры не знают о версии:
```python
# ✅ ПРАВИЛЬНО: Роутер не знает о версии
router = APIRouter(prefix="/roles")

# В main.py:
app.include_router(router, prefix="/api/v1")

# ❌ НЕПРАВИЛЬНО: Роутер знает о версии
router = APIRouter(prefix="/api/v1/roles")
```

#### 4.8. Связь с Правилом №6 (Именование файлов)
Файл роутера называется `router.py` (без префикса с именем сущности):
```text
backend/app/core/roles/
 ├── router.py  # ✅ (НЕ router_role.py)
```

#### 4.9. Связь с Правилом №4 (Orval-совместимость)
Все эндпоинты, возвращающие списки, используют `PaginatedResponse[Schema]`:
```python
@router.get("/", response_model=ApiResponse[PaginatedResponse[RoleResponseSchema]])
async def get_roles(...):
    pass
```

---

### 5. Типичные ошибки и их исправление

| Ошибка | Исправление |
| :--- | :--- |
| `@router.post("/register")` (без `/public/`) | `@router.post("/public/register")` |
| `prefix="/role"` (единственное число) | `prefix="/roles"` |
| `prefix="/api/v1/roles"` (версия в роутере) | `prefix="/roles"` + версия в `main.py` |
| `prefix="/users-list"` (суффикс) | `prefix="/users"` |
| `@router.get("/{roleId}")` (camelCase) | `@router.get("/{role_id}")` (snake_case) |
| `@router.put("/{id}")` (абстрактное имя) | `@router.put("/{role_id}")` (конкретное имя) |

---

### 6. Чек-лист для разработчика

При создании нового роутера проверьте:

**Префиксы:**
- [ ] Префикс роутера во множественном числе (`/roles`, `/users`)?
- [ ] Префикс использует нижний регистр?
- [ ] Отсутствуют ли суффиксы (`-list`, `-mgmt`, `-api`)?
- [ ] Версия API (`/api/v1`) задаётся в `main.py`, а не в роутере?

**Публичные эндпоинты:**
- [ ] Все эндпоинты без авторизации имеют префикс `/public/`?
- [ ] Регистрация: `/public/register`?
- [ ] Восстановление пароля: `/public/restore-password`?

**Внутренние эндпоинты:**
- [ ] Все эндпоинты с авторизацией НЕ имеют префикса `/public/`?
- [ ] Текущий пользователь: `/me`?
- [ ] Параметры URL в `snake_case` (`{role_id}`, а не `{roleId}`)?

**HTTP-методы:**
- [ ] `GET` используется для чтения?
- [ ] `POST` используется для создания?
- [ ] `PUT`/`PATCH` используется для обновления?
- [ ] `DELETE` используется для удаления?

**Документация:**
- [ ] Указан ли `tags` для группировки в Swagger?
- [ ] Все эндпоинты имеют `response_model`?
- [ ] Списковые эндпоинты используют `PaginatedResponse`?

**Middleware:**
- [ ] Middleware аутентификации пропускает маршруты с `/public/`?
- [ ] Все остальные маршруты требуют JWT-токен?

---

### 7. Таблица соответствий

| Домен | Префикс роутера | Публичные эндпоинты | Внутренние эндпоинты |
| :--- | :--- | :--- | :--- |
| Аутентификация | `/auth` | `/public/register`, `/public/restore-password` | `/me`, `/change-password` |
| Пользователи | `/users` | — | `/`, `/{user_id}`, `/save` |
| Организации | `/tenants` | — | `/`, `/{tenant_id}`, `/save` |
| Роли | `/roles` | — | `/`, `/{role_id}`, `/save` |
| Полномочия | `/permissions` | — | `/`, `/{permission_id}` |
| Разделы | `/sections` | — | `/`, `/{section_id}` |
| Типы документов | `/doctypes` | — | `/`, `/{doctype_id}` |

---

Следование этому правилу гарантирует, что API Cool ERP будет:
✅ **Безопасным** — чёткое разделение публичных и защищённых маршрутов
✅ **Предсказуемым** — единая система именования для всех доменов
✅ **Соответствующим стандартам** — REST-архитектура, snake_case, множественное число
✅ **Легко масштабируемым** — добавление новых доменов не требует придумывания новых префиксов
✅ **Документированным** — Swagger UI автоматически группирует эндпоинты по тегам

Это правило работает в связке с Правилами №3 (Версионирование), №4 (Orval-совместимость), №6 (Именование файлов), №7 (Множественное число) и №26 (Безопасность multi-tenancy), формируя единый стандарт API-дизайна проекта.