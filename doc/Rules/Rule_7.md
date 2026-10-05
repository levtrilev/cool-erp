# Правило №7: Именование сущностей во множественном числе

Все сущности, папки доменов и таблицы в базе данных **ОБЯЗАТЕЛЬНО** именуются во множественном числе. Это правило применяется единообразно ко всем уровням проекта: от структуры файловой системы до именования переменных в коде.

✅ **Правильно:** `tenants`, `users`, `roles`, `permissions`, `groups`, `sections`, `doctypes`
❌ **Неправильно:** `tenant`, `user`, `role`, `permission`, `group` (для коллекций и доменов)

---

### 1. Обоснование (Почему это важно)

1. **Семантическая точность:** Папка `tenants` содержит код, работающий со **множеством** организаций (CRUD-методы, роутеры, схемы). Имя во множественном числе точно отражает назначение модуля.
2. **Единообразие с REST API:** REST-архитектура исторически использует множественное число в URL (`/api/v1/roles`, `/api/v1/users`). Совпадение именования папок и URL упрощает навигацию по коду.
3. **Согласованность с БД:** Таблицы в PostgreSQL (`public.tenants`, `public.roles`) также именуются во множественном числе. Единое правило исключает путаницу при маппинге ORM → БД.
4. **Предсказуемость:** Разработчик, открывающий проект, мгновенно понимает, что `backend/app/core/users/` — это модуль для работы с пользователями, а не какой-то специфический пользователь.
5. **Избежание коллизий:** Когда папка называется `user`, а внутри неё класс `UserModel`, возникает путаница. Когда папка — `users`, а класс — `UserModel`, различие очевидно.

---

### 2. Обязательные требования к реализации

#### 2.1. Папки доменов (Backend и Frontend)
Все папки доменов **ОБЯЗАТЕЛЬНО** именуются во множественном числе:
```text
backend/app/core/
 ├── users/          # ✅ ПРАВИЛЬНО
 ├── tenants/        # ✅ ПРАВИЛЬНО
 ├── roles/          # ✅ ПРАВИЛЬНО
 ├── permissions/    # ✅ ПРАВИЛЬНО
 ├── sections/       # ✅ ПРАВИЛЬНО
 ├── doctypes/       # ✅ ПРАВИЛЬНО
 └── groups/         # ✅ ПРАВИЛЬНО
```

#### 2.2. Таблицы в базе данных
Все таблицы в PostgreSQL **ОБЯЗАТЕЛЬНО** именуются во множественном числе:
```sql
public.tenants        -- ✅ ПРАВИЛЬНО
public.users          -- ✅ ПРАВИЛЬНО
public.roles          -- ✅ ПРАВИЛЬНО
public.permissions    -- ✅ ПРАВИЛЬНО
```

#### 2.3. Переменные для коллекций
Все переменные, содержащие массивы или списки сущностей, **ОБЯЗАТЕЛЬНО** именуются во множественном числе:
```typescript
const users: UserResponseSchema[] = data?.data?.items || []; // ✅
const roles: RoleResponseSchema[] = data?.data?.items || []; // ✅
```

#### 2.4. URL-эндпоинты
Все маршруты API **ОБЯЗАТЕЛЬНО** используют множественное число:
```python
app.include_router(users_router, prefix="/api/v1/users")     # ✅
app.include_router(roles_router, prefix="/api/v1/roles")     # ✅
```

---

### 3. Примеры кода

#### ✅ ПРАВИЛЬНО: Структура домена

**Backend (`backend/app/core/roles/`):**
```python
# models.py
class RoleModel(Base):
    __tablename__ = "roles"  # ✅ Множественное число
    __table_args__ = {"schema": "public"}
    # ...

# schemas.py
class RoleBaseSchema(BaseModel):  # ✅ Имя класса в единственном (один объект)
    name: str

class RoleCreateSchema(RoleBaseSchema):
    pass

class RoleResponseSchema(RoleBaseSchema):
    id: uuid.UUID

# crud.py
class CRUDRole:
    def __init__(self, model):
        self.model = model
    
    async def get_multi(self, db: AsyncSession, ...) -> tuple[list[RoleModel], int]:
        # ✅ Возвращает список (множество) объектов
        pass

crud_role = CRUDRole(RoleModel)

# router.py
router = APIRouter(prefix="/roles", tags=["Roles"])  # ✅ URL во множественном

@router.get("/", response_model=ApiResponse[PaginatedResponse[RoleResponseSchema]])
async def get_roles(...) -> list[RoleResponseSchema]:  # ✅ Возвращает множество
    pass
```

**Frontend (`frontend/src/core/roles/`):**
```tsx
// RolesPage.tsx
export const RolesPage = () => {
  const { data } = useReadRolesRolesGet({ skip: 0, limit: 10 });
  
  // ✅ Переменная для коллекции во множественном числе
  const roles: RoleResponseSchema[] = data?.data?.items || [];
  
  return (
    <div>
      <h1>Роли</h1>
      {roles.map((role) => (  // ✅ Итерация: role (единственное) из roles (множественное)
        <TableRow key={role.id}>
          <TableCell>{role.name}</TableCell>
        </TableRow>
      ))}
    </div>
  );
};
```

#### ❌ НЕПРАВИЛЬНО: Использование единственного числа для доменов

```text
backend/app/core/
 ├── user/           # ❌ ОШИБКА: должно быть users/
 ├── tenant/         # ❌ ОШИБКА: должно быть tenants/
 ├── role/           # ❌ ОШИБКА: должно быть roles/
 └── permission/     # ❌ ОШИБКА: должно быть permissions/
```

```python
# ❌ ОШИБКА: Таблица в единственном числе
class RoleModel(Base):
    __tablename__ = "role"  # ❌ Должно быть "roles"
```

```python
# ❌ ОШИБКА: URL в единственном числе
router = APIRouter(prefix="/role", tags=["Role"])  # ❌ Должно быть "/roles"
```

```tsx
// ❌ ОШИБКА: Переменная для коллекции в единственном числе
const role: RoleResponseSchema[] = data?.data?.items || [];  // ❌ Должно быть roles
```

---

### 4. Нюансы и лучшие практики

#### 4.1. Различие между "доменом" и "классом"
Важно понимать разницу:
* **Папка домена** — во множественном числе (`users/`), так как содержит код для работы со всеми пользователями.
* **Класс модели/схемы** — в единственном числе (`UserModel`, `UserResponseSchema`), так как представляет **один** объект.
* **Переменная коллекции** — во множественном (`users`), так как содержит **много** объектов.
* **Переменная одного объекта** — в единственном (`user`), так как содержит **один** объект.

```tsx
// ✅ Правильное сочетание
const users: UserResponseSchema[] = data?.data?.items || [];  // Коллекция
const currentUser: UserResponseSchema | null = users[0];       // Один объект
```

#### 4.2. Исключения: Составные сущности
Для составных сущностей множественное число применяется к **последнему слову**:
* ✅ `user_roles` (роли пользователей) — но лучше избегать таких таблиц
* ✅ `role_permissions` — но в нашем проекте это просто `permissions`
* ✅ `document_line_items` — строки документа

#### 4.3. Английские неправильные множественные формы
Следуйте стандартным английским правилам:
* `user` → `users` (не `useres`)
* `tenant` → `tenants`
* `role` → `roles`
* `permission` → `permissions`
* `group` → `groups`
* `section` → `sections`
* `doctype` → `doctypes`
* `person` → `people` (но в проекте лучше использовать `users`)
* `index` → `indices` или `indexes` (в БД обычно `indexes`)

#### 4.4. Связь с другими правилами

**Правило №6 (Именование файлов):**
Файлы внутри папки домена именуются коротко, без префиксов:
```text
backend/app/core/users/
 ├── models.py      # ✅ (не user_models.py)
 ├── schemas.py     # ✅ (не user_schemas.py)
 ├── crud.py        # ✅ (не crud_user.py)
 └── router.py      # ✅ (не router_user.py)
```

**Правило №21 (Именование Pydantic-схем):**
Схемы используют имя сущности в единственном числе + суффикс:
```python
class UserResponseSchema(BaseModel): ...  # ✅ Один объект
class RoleCreateSchema(BaseModel): ...    # ✅ Один объект
```

**Правило №28 (Схема `public`):**
Таблицы в БД именование во множественном числе + префикс `public.`:
```python
ForeignKey("public.users.id")  # ✅
```

#### 4.5. Именование переменных в циклах
При итерации по коллекции используйте **единственное число** для элемента:
```tsx
// ✅ ПРАВИЛЬНО
roles.map((role) => <TableRow key={role.id}>{role.name}</TableRow>);
users.map((user) => <div key={user.id}>{user.name}</div>);

// ❌ НЕПРАВИЛЬНО
roles.map((roles) => ...);  // ❌ Элемент не должен быть во множественном
users.map((u) => ...);       // ❌ Сокращения запутывают
```

#### 4.6. Именование callback-ов
Callback-и для работы с одной сущностью — в единственном числе:
```tsx
const handleRoleSaved = (id: string, name: string) => { ... }  // ✅ Одна роль
const handleUserDeleted = (id: string) => { ... }              // ✅ Один пользователь
```

Callback-и для работы с множеством — во множественном:
```tsx
const handleRolesSync = (roles: RoleResponseSchema[]) => { ... }  // ✅ Много ролей
```

#### 4.7. Именование в localStorage
Ключи для `localStorage` также используют множественное число:
```typescript
localStorage.setItem("roles-table-widths", ...);  // ✅
localStorage.setItem("users-table-widths", ...);  // ✅
```

---

### 5. Связь с REST API и URL

Правило №7 напрямую связано с REST-архитектурой:

| HTTP Метод | URL | Описание |
| :--- | :--- | :--- |
| `GET` | `/api/v1/roles` | Получить список ролей |
| `GET` | `/api/v1/roles/{id}` | Получить одну роль |
| `POST` | `/api/v1/roles` | Создать роль |
| `PUT` | `/api/v1/roles/{id}` | Обновить роль |
| `DELETE` | `/api/v1/roles/{id}` | Удалить роль |

URL всегда во множественном числе, так как эндпоинт представляет **коллекцию** ресурсов, даже если мы обращаемся к одному элементу через `{id}`.

---

### 6. Чек-лист для разработчика

При создании нового домена или рефакторинге проверьте:

**Структура проекта:**
- [ ] Папка домена на бэкенде названа во множественном числе (`users/`, `roles/`)?
- [ ] Папка домена на фронтенде названа во множественном числе?
- [ ] Импорты используют правильный путь (`@/core/users/...`)?

**База данных:**
- [ ] Таблица в БД названа во множественном числе (`users`, `roles`)?
- [ ] В `__tablename__` модели указано множественное число?
- [ ] В `ForeignKey` указан правильный путь (`public.users.id`)?

**API:**
- [ ] Префикс роутера во множественном числе (`/roles`, `/users`)?
- [ ] URL эндпоинтов соответствуют REST-стандарту?

**Код:**
- [ ] Переменные для коллекций во множественном числе (`const roles = ...`)?
- [ ] Переменные для одного объекта в единственном числе (`const role = ...`)?
- [ ] В циклах `.map()` используется единственное число для элемента?
- [ ] Callback-и для одной сущности в единственном числе (`handleRoleSaved`)?
- [ ] Ключи `localStorage` во множественном числе (`roles-table-widths`)?

**Исключения (документированы):**
- [ ] Если используется единственное число для папки (например, `auth/` — это не коллекция, а процесс), это явно обосновано?

Следование этому правилу гарантирует, что структура проекта Cool ERP будет интуитивно понятной, предсказуемой и соответствующей общепринятым стандартам индустрии. Любой разработчик, открывший проект, мгновенно сориентируется в его структуре, а единообразие именования снизит когнитивную нагрузку при работе с разными доменами.