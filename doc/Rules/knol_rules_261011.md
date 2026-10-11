изложи прочие важные сведения о проекта, такие как общие сведения, структура папок, "грабли проекта", не вошедшие в правила для backend & frontend

# 📋 Прочие важные сведения о проекте Cool ERP

Этот документ дополняет формальные правила Backend и Frontend и содержит общую архитектуру, структуру, конфигурацию и известные "грабли" проекта.

## 0. Формат предоставления результатов в чате
я работаю с тобой в чате. Мне нужно удобно скопировать созданные/измененные файлы *.tsx. Поэтому показывай полный текст нового/изменённого компонента *.tsx в специальном окне-компоненте для кода typescript либо python

---

## 1. Общие сведения о проекте

**Cool ERP** — мульти-tenant ERP-система для управления документами, ролями и полномочиями.

### Стек технологий

| Слой | Технологии |
|------|-----------|
| **Backend** | Python 3.12, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, Pydantic v2 |
| **Frontend** | React 18, Vite, TypeScript (strict), shadcn/ui, Tailwind CSS |
| **API-клиент** | Orval (генерация из OpenAPI), React Query (TanStack Query) |
| **Формы** | React Hook Form + Zod (валидация) |
| **Авторизация** | Cookie-based (не JWT в заголовках) |
| **Миграции БД** | Ручные SQL-скрипты (не Alembic autogenerate) |

### Авторизация (Cookie-based)

- **Axios** настроен с `withCredentials: true`
- **CORS** на бэкенде: `allow_credentials=True`, `allow_origins=["http://localhost:5173"]` (не `"*"`)
- **Cookie**: `samesite="lax"`, `secure=False` (для localhost)
- В `dependencies.py` используется `getattr(current_user, "is_superadmin", False)`, а не `.get()`, так как `current_user` — это ORM-объект, а не словарь

### База данных

- PostgreSQL с явной схемой `public`
- Все таблицы создаются через ручные SQL-скрипты
- UUID используется как первичный ключ во всех таблицах
- Связи настраиваются через `relationship` с `back_populates` и `lazy="selectin"`

---

## 2. Структура проекта

### Backend

```
backend/
├── app/
│   ├── main.py                          # FastAPI app, CORS, include_router
│   ├── core/
│   │   ├── database.py                  # Base, get_db, engine, async_session
│   │   ├── schemas.py                   # ApiResponse, PaginatedResponse
│   │   ├── crud/
│   │   │   └── base.py                  # CRUDBase + @with_db_error_handling
│   │   ├── auth/
│   │   │   ├── dependencies.py          # SuperAdminUser, CurrentUser, DBSession
│   │   │   ├── router.py
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   └── crud.py
│   │   ├── users/
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── crud.py
│   │   │   └── router.py
│   │   ├── tenants/
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── crud.py
│   │   │   └── router.py
│   │   ├── roles/
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── crud.py
│   │   │   └── router.py
│   │   ├── permissions/
│   │   │   ├── models.py               # PermissionModel (существующая, НЕ менять)
│   │   │   ├── schemas.py
│   │   │   ├── crud.py
│   │   │   └── router.py
│   │   ├── domains/
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── crud.py
│   │   │   └── router.py
│   │   └── doctypes/
│   │       ├── models.py
│   │       ├── schemas.py
│   │       ├── crud.py
│   │       └── router.py
│   └── ...
├── requirements.txt
└── .env
```

### Frontend

```
frontend/
├── src/
│   ├── App.tsx                          # Роутинг, импорты страниц
│   ├── main.tsx                         # Точка входа, QueryClientProvider
│   ├── api/
│   │   └── generated/                   # Orval-сгенерированные хуки и функции
│   │       ├── fastAPI.schemas.ts       # Все типы (ResponseSchema, CreateSchema и т.д.)
│   │       ├── doctypes/doctypes.ts
│   │       ├── domains/domains.ts
│   │       ├── roles/roles.ts
│   │       ├── permissions/permissions.ts
│   │       ├── tenants/tenants.ts
│   │       └── authentication/authentication.ts
│   ├── components/
│   │   ├── ui/                          # shadcn/ui компоненты
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── alert-dialog.tsx
│   │   │   ├── table.tsx
│   │   │   ├── switch.tsx
│   │   │   ├── label.tsx
│   │   │   └── use-toast.ts
│   │   └── hooks/
│   │       └── useResizableColumns.ts   # Хук для изменения ширины колонок
│   ├── core/
│   │   ├── doctypes/
│   │   │   ├── DoctypesPage.tsx         # Страница списка типов документов
│   │   │   └── EditDoctypeModal.tsx     # Модалка создания/редактирования
│   │   ├── roles/
│   │   │   ├── RolesPage.tsx
│   │   │   ├── EditRoleModal.tsx        # Модалка с вкладками
│   │   │   └── PermissionsTab.tsx       # Вкладка "Полномочия"
│   │   ├── tenants/
│   │   │   ├── TenantsPage.tsx
│   │   │   └── EditTenantModal.tsx      # Эталонный Switch
│   │   ├── users/
│   │   │   ├── UsersPage.tsx
│   │   │   └── EditUserModal.tsx        # Эталонный ReferenceSelect с selectedLabel
│   │   └── domains/
│   │       └── DomainsPage.tsx
│   ├── lib/
│   │   ├── reusable/
│   │   │   ├── ReferenceSelect.tsx      # Универсальный компонент справочника (НЕ менять)
│   │   │   └── TenantMultiSelect.tsx    # Мультиселект тенантов
│   │   └── utils.ts
│   └── hooks/
│       └── useResizableColumns.ts
├── orval.config.ts                      # Конфигурация генерации Orval
├── tsconfig.json
├── tsconfig.app.json
└── vite.config.ts
```

---

## 3. Архитектурные паттерны

### 3.1. Базовый CRUD с декоратором обработки ошибок

В `base_crud.py` есть декоратор `@with_db_error_handling("action")`, который автоматически:
- Перехватывает `IntegrityError`, `SQLAlchemyError`, `Exception`
- Делает `await db.rollback()`
- Логирует `[ModelName.action] ErrorType: ...`
- Возвращает `HTTPException(400/500)` с понятным текстом

```python
@with_db_error_handling("create")
async def create(self, db: AsyncSession, obj_in: CreateSchema) -> Model:
    db_obj = self.model(**obj_in.model_dump())
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj
```

### 3.2. Универсальные обёртки ответов

```python
# schemas.py
class ApiResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: T | None = None

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
```

### 3.3. Аннотированные зависимости

```python
# dependencies.py
DBSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[UserModel, Depends(get_current_user)]
SuperAdminUser = Annotated[UserModel, Depends(get_current_superadmin)]
```

### 3.4. Cookie-авторизация (полный цикл)

```python
# Backend: Установка cookie
response.set_cookie(
    key="access_token",
    value=token,
    httponly=True,
    samesite="lax",
    secure=False,  # True в продакшене
    max_age=3600,
)

# Frontend: Axios настроен на отправку cookie
const api = axios.create({
  baseURL: "http://localhost:8000",
  withCredentials: true,  // ← Критично!
});
```

---

## 4. Ключевые модели данных

### PermissionModel (существующая, НЕ менять)

```python
class PermissionModel(Base):
    __tablename__ = "permissions"
    __table_args__ = {"schema": "public"}
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"))
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    doctype: Mapped[str]  # ← Строка! Не UUID. Например "invoices"
    doctype_name: Mapped[str | None]
    full_access: Mapped[bool]
    author: Mapped[bool]
    reader: Mapped[bool]
    editor: Mapped[bool]
    can_delete: Mapped[bool]
    access_by_tags: Mapped[bool]
    or_tags: Mapped[list[str] | dict[str, None] | None]  # JSONB
    and_tags: Mapped[list[str] | dict[str, None] | None]  # JSONB
    no_tags: Mapped[list[str] | dict[str, None] | None]  # JSONB
    role_name: Mapped[str | None]  # Денормализованное
    tenant_name: Mapped[str | None]  # Денормализованное
    
    role = relationship("RoleModel", back_populates="permissions", lazy="selectin")
    tenant = relationship("TenantModel", lazy="selectin")
```

**Важно:** Поле `doctype` — это строка (код типа документа), а не UUID. В `ReferenceSelect` нужно подменять `id` на `item.doctype` в адаптере.

### RoleModel (обновлённая)

```python
class RoleModel(Base):
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),
        {"schema": "public"}
    )
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id"))
    name: Mapped[str]
    description: Mapped[str | None]
    is_active: Mapped[bool] = mapped_column(default=True)
    
    tenant = relationship("TenantModel", lazy="selectin")
    permissions = relationship(
        "PermissionModel", 
        back_populates="role", 
        lazy="selectin", 
        cascade="all, delete-orphan"
    )
    
    @property
    def permissions_count(self) -> int:
        return len(self.permissions)
```

### DomainBaseSchema (для ReferenceSelect)

```python
class DomainBaseSchema(BaseModel):
    name: str          # ← Используется как label в ReferenceSelect
    description: str | None = None
```

---

## 5. Сигнатура ReferenceSelect (актуальная)

```tsx
interface ReferenceItem {
  id: string;
  name: string;
  [key: string]: unknown;
}

interface ReferenceSelectProps<T extends ReferenceItem> {
  fetchFn: (params: { skip: number; limit: number; search?: string }) => 
    Promise<{ items: T[]; total: number }>;
  queryKey: string[];
  value: string;
  onValueChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  limit?: number;
  heading?: string;
  columns?: Array<{ column: keyof T; label: string }>;  // ← ключ "column"!
  selectedLabel?: string;  // ← Для мгновенного отображения при редактировании
}
```

**Файл `ReferenceSelect.tsx` НЕЛЬЗЯ изменять.** Все адаптации данных происходят на уровне пропсов.

---

## 6. Текущее состояние модулей

| Модуль | Backend | Frontend | Статус |
|--------|---------|----------|--------|
| `auth` | ✅ models, schemas, crud, router, dependencies | ✅ LoginPage | Полностью рабочий |
| `users` | ✅ models, schemas, crud, router | ✅ UsersPage, EditUserModal | Полностью рабочий |
| `tenants` | ✅ models, schemas, crud, router | ✅ TenantsPage, EditTenantModal | Полностью рабочий |
| `roles` | ✅ models, schemas, crud, router | ✅ RolesPage, EditRoleModal | Полностью рабочий |
| `permissions` | ✅ models, schemas, crud, router | 🔧 PermissionsTab (в процессе) | Backend готов, фронтенд дорабатывается |
| `domains` | ✅ models, schemas, crud, router | ✅ DomainsPage | Полностью рабочий |
| `doctypes` | ✅ models, schemas, crud, router | ✅ DoctypesPage, EditDoctypeModal | Полностью рабочий |

---

## 7. "Грабли проекта" (известные проблемы и их решения)

| № | Проблема | Симптом | Решение |
|---|----------|---------|---------|
| 1 | `"self" is not accessed` в CRUD | Предупреждение линтера | Использовать `self.model` вместо прямого имени модели в методах |
| 2 | `Type of parameter "self" is unknown` | Ошибка Pyright | Наследовать от `CRUDBase[Model, CreateSchema, UpdateSchema]` с явными дженериками |
| 3 | `Method overrides in incompatible manner` | Ошибка типизации | Имена параметров должны совпадать с базовым классом: `obj_in`, `db_obj`, `is_superadmin` |
| 4 | `ResponseValidationError: tuple` | 500 ошибка на бэкенде | Нет запятой после `return ApiResponse(...)`. `PaginatedResponse(...)` должен быть со скобками, а не кортежем |
| 5 | `CORS error` на конкретном запросе | Ошибка в консоли браузера | Искать 500/401 в терминале Uvicorn, а не чинить CORS. CORS — это следствие, а не причина |
| 6 | `AttributeError: .get() on ORM` | `AttributeError: 'UserModel' object has no attribute 'get'` | Использовать `getattr(obj, "attr", default)`, а не `obj.get("attr")`, так как это ORM-объект, а не словарь |
| 7 | `IntegrityError is not defined` | `NameError` в CRUD | Импортировать `from sqlalchemy.exc import IntegrityError` |
| 8 | `Type 'undefined' not assignable to 'boolean'` | Ошибка TypeScript в Switch | Zod: `.optional()` (не `.default()`), `defaultValues`: `true`, Switch: `checked={field.value}` |
| 9 | `Resolver type mismatch` | Ошибка TypeScript в useForm | Не использовать `.default()` в Zod-схеме, только `.optional()` |
| 10 | Switch не переключается | Визуально не реагирует на клик | Паттерн из EditTenantModal: `checked={field.value}`, `onCheckedChange={field.onChange}`, `Label` с `htmlFor` |
| 11 | `ReferenceSelect type error` | `Property 'name' is missing` | Добавить адаптер в `fetchFn`, маппящий `name`. Не менять `ReferenceSelect.tsx` |
| 12 | `role_doctypes unknown import` | Ошибка импорта | Не нужна M2M таблица. Использовать существующую `PermissionModel` |
| 13 | Старые значения в форме создания | При открытии "Создать" видны данные от "Редактировать" | `reset(CREATE_DEFAULTS)` при закрытии модалки (Правило №20) |
| 14 | Домен не отображается при редактировании | Пустое поле ReferenceSelect | Использовать проп `selectedLabel={initialData?.domain_name ?? "Выберите..."}` (Правило №27) |
| 15 | `setState` в `useEffect` вызывает каскадные рендеры | Предупреждение React | Использовать `watch()` из react-hook-form или паттерн с `key` (Правило №37) |
| 16 | `unexpected any` в catch/onError | Предупреждение линтера | Использовать `unknown` с безопасным приведением типа (Правило №36) |
| 17 | `session.user` AttributeError | `'UserModel' object has no attribute 'user'` | Зависимость `CurrentUser` возвращает сам объект пользователя. Использовать `session.is_superadmin` напрямую |
| 18 | `PermissionUpdateSchema` не совместим с `PermissionCreateSchema` | Ошибка типизации в CRUD | В методе `update` использовать `PermissionUpdateSchema`, а не `CreateSchema` (Правило №31) |
| 19 | `TS1261: Already included file name differs only in casing` | Ошибка сборки `npm run build` | Переименовать файл в два этапа (TEMP → правильное имя). Очистить кэш Vite. Перезапустить VS Code |
| 20 | `Cannot find name 'reset'` | Ошибка TypeScript | Добавить `reset` в деструктуризацию `useForm`: `const { control, handleSubmit, reset } = useForm(...)` |
| 21 | `Cannot find name 'CREATE_DEFAULTS'` | Ошибка TypeScript | Объявить константу `CREATE_DEFAULTS` вне компонента или в его начале |
| 22 | `Property 'items' does not exist on type '{}'` | Ошибка TypeScript при работе с кэшем | Явно типизировать `queryClient.getQueryData()` через `as { items?: ...; total?: number }` |

---

## 8. Эталонные примеры кода

### Эталон Switch (из EditTenantModal)

```tsx
<Controller
  name="is_active"
  control={control}
  render={({ field }) => (
    <>
      <Switch id="is_active" checked={field.value} onCheckedChange={field.onChange} />
      <Label
        htmlFor="is_active"
        className={`flex items-center gap-2 cursor-pointer font-medium transition-colors ${
          field.value ? "text-green-600 dark:text-green-400" : "text-red-500 dark:text-red-400"
        }`}
      >
        {field.value ? (
          <><CheckCircle2 className="h-4 w-4" /> Активен</>
        ) : (
          <><PauseCircle className="h-4 w-4" /> Неактивен</>
        )}
      </Label>
    </>
  )}
/>
```

### Эталон ReferenceSelect с selectedLabel (из EditUserModal)

```tsx
<Controller
  name="tenant_id"
  control={control}
  render={({ field }) => (
    <ReferenceSelect
      fetchFn={async (params) => {
        const response = await readTenantsTenantsGet(params);
        return { items: response?.items ?? [], total: response?.total ?? 0 };
      }}
      queryKey={["tenants", "active"]}
      value={field.value || ""}
      onValueChange={field.onChange}
      placeholder="Выберите организацию"
      selectedLabel={user?.tenant_name ?? "Выберите организацию"}
      heading="Выберите организацию"
      columns={[{ column: "description", label: "Описание" }]}
    />
  )}
/>
```

### Эталон обработки ошибок (из EditUserModal)

```tsx
onError: (error: unknown) => {
  let message = "Ошибка обновления пользователя";
  if (error && typeof error === "object" && "response" in error) {
    const response = (error as { response?: { data?: { detail?: string } } }).response;
    if (response?.data?.detail) {
      message = response.data.detail;
    }
  }
  toast({ variant: "destructive", title: "Ошибка", description: message });
}
```

### Эталон синхронизации формы (из EditUserModal)

```tsx
useEffect(() => {
  if (open && user) {
    reset({
      name: user.name,
      email: user.email,
      password: "",
      tenant_id: user.tenant_id || "",
    });
  }
}, [open, user, reset]);
```

---

## 9. Конфигурационные файлы

### orval.config.ts

Генерация API-клиента из OpenAPI-спецификации бэкенда. Запуск: `npm run generate:api`.

### tsconfig.app.json

Включает `"include": ["src"]`. Важно: `forceConsistentCasingInFileNames` включён по умолчанию — регистр импортов должен точно совпадать с именами файлов.

### vite.config.ts

Стандартная конфигурация Vite + React. Прокси для API обычно настроен на `http://localhost:8000`.

---

## 10. Команды разработки

| Команда | Описание |
|---------|----------|
| `cd backend && uvicorn app.main:app --reload` | Запуск бэкенда с автоперезагрузкой |
| `cd frontend && npm run dev` | Запуск фронтенда (Vite dev server) |
| `cd frontend && npm run generate:api` | Генерация Orval-клиента из OpenAPI |
| `cd frontend && npm run build` | Сборка фронтенда (tsc + vite build) |

---

Этот документ вместе с правилами Backend и Frontend составляет **полную базу знаний** проекта Cool ERP для переноса в новый чат.