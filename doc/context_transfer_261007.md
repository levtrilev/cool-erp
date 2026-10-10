# 📋 Контекст для продолжения работы в новом чате

Скопируйте весь текст ниже и вставьте в начало нового чата.

---

## 1. О проекте

**Cool ERP** — мульти-tenant ERP-система. Стек: **FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL** на бэкенде, **React + Vite + TypeScript + shadcn/ui + Orval + React Query + React Hook Form + Zod** на фронтенде. Авторизация через **Cookie** (не JWT в заголовках). Axios настроен с `withCredentials: true`.

---

## 2. Свод всех правил проекта (актуальные)

### ЧАСТЬ 1: BACKEND

**Правило №1 (Чистая архитектура и ORM):**
- Вычисляемые поля — через `@property` в моделях.
- `relationship` с `back_populates` и `lazy="selectin"`.
- Pydantic-схемы ответов: `model_config = ConfigDict(from_attributes=True)`.

**Правило №4 (Orval-совместимость API):**
- Все списковые эндпоинты возвращают `ApiResponse[PaginatedResponse[T]]`.

**Правило №21 (Именование схем):** Суффиксы `CreateSchema`, `UpdateSchema`, `ResponseSchema`.

**Правило №26 (Multi-tenancy):** Фильтрация по `tenant_id` на уровне SQL. Суперадмины видят всё.

**Правило №28 (Схема БД):** Явная `{"schema": "public"}` в `__table_args__`. Именованные `UniqueConstraint`.

**Правило №30 (M2M синхронизация):** Связи M2M синхронизируются в `create`/`update` через `insert`/`delete`.

**Правило №31 (Приоритет CRUDBase):**
- Все CRUD наследуются от `CRUDBase[Model, CreateSchema, UpdateSchema]`.
- Переопределение только при специфичной логике.
- Имена параметров базового класса не менять: `obj_in`, `db_obj`, `user_is_superadmin`.

**Правило №32 (Аннотированные типы):**
- Запрещён `Depends(...)` в значениях по умолчанию.
- Используются алиасы: `SuperAdminUser`, `CurrentUser`, `DBSession` из `dependencies.py`.

**Правило №33 (Запрет присваивания в @property):**
- `@property` — read-only. Присваивание `item.field = value` запрещено.
- Pydantic читает `@property` автоматически через `from_attributes=True`.

### ЧАСТЬ 2: FRONTEND

**Правило №11:** Компактные таблицы (`py-1`, `align-top`).
**Правило №12:** Поиск через `<form onSubmit>`, два стейта: `searchInput` и `search`.
**Правило №16:** Удаление через `AlertDialog`.
**Правило №20:** Сброс формы при закрытии модалки через `reset(CREATE_DEFAULTS)`.
**Правило №22:** Разделение `searchInput` (ввод) и `search` (отправка в API).
**Правило №24:** `invalidateQueries` ДО закрытия модалки.
**Правило №25:** `refetch()` после удаления.
**Правило №29:** Изменяемая ширина колонок через `useResizableColumns`.

**Правило №27 (ReferenceSelect для справочников):**
- Запрещён `<Input>` для UUID.
- Обязательный паттерн адаптера в `fetchFn`:
```tsx
fetchFn={async (params) => {
  const response = await getXxxXxxGet(params);
  return {
    items: response?.data?.items ?? [],
    total: response?.data?.total ?? 0,
  };
}}
```
- Для доп. колонок: `columns={[{ column: "description", label: "Описание" }]}` (ключ `column`, не `key`).
- Проп `labelField` НЕ существует в компоненте.
- Изменение `ReferenceSelect.tsx` запрещено.

**Правило №34 (Switch в формах):**
- Через `Controller`: `checked={field.value}`, `onCheckedChange={field.onChange}`.
- Рядом `Label` с `htmlFor`, меняющий цвет и иконку (`CheckCircle2`/`PauseCircle`).
- В Zod-схеме: `z.boolean().optional()`. В `defaultValues`: `is_active: true`.

---

## 3. Ключевые архитектурные решения

### Базовый CRUD с декоратором обработки ошибок
В `base_crud.py` есть декоратор `@with_db_error_handling("action")`, который автоматически:
- Перехватывает `IntegrityError`, `SQLAlchemyError`, `Exception`
- Делает `await db.rollback()`
- Логирует `[ModelName.action] ErrorType: ...`
- Возвращает `HTTPException(400/500)` с понятным текстом

### Cookie-авторизация
- Axios: `withCredentials: true`
- CORS: `allow_credentials=True`, `allow_origins=["http://localhost:5173"]` (не `"*"`)
- Cookie: `samesite="lax"`, `secure=False` (для localhost)
- В `dependencies.py`: `getattr(current_user, "is_superadmin", False)` (не `.get()`, т.к. это ORM-объект)

### Сброс форм
Константа `CREATE_DEFAULTS` вне или в начале компонента, используется в `useForm({ defaultValues })` и `reset()` при закрытии модалки.

### Миграции БД
Через отдельные SQL-скрипты (не Alembic autogenerate). Таблицы создаются вручную.

---

## 4. Текущее состояние модулей

### ✅ Полностью рабочие модули:
- **auth** (Cookie-based, `dependencies.py` с `SuperAdminUser`, `CurrentUser`, `DBSession`)
- **users**
- **tenants** (включая `EditTenantModal` с эталонным Switch)
- **roles** (CRUD + роутер + фронтенд)
- **domains** (models, schemas, crud, router, DomainsPage.tsx)
- **doctypes** (models, schemas, crud, router, DoctypesPage.tsx с ReferenceSelect для domain)
- **permissions** (models, schemas, crud, router — уже существуют)

### 🔧 В процессе доработки:
- **Вкладка "Полномочия"** в модалке редактирования Роли. Нужно добавить кнопку "Добавить" с `ReferenceSelect` для выбора doctype из справочника (фильтрованного по `tenant_id` роли).

---

## 5. Модель Permission (существующая, НЕ менять)

```python
class PermissionModel(Base):
    __tablename__ = "permissions"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID]  # PK
    role_id: Mapped[uuid.UUID]  # FK -> roles.id
    tenant_id: Mapped[uuid.UUID]  # FK -> tenants.id
    doctype: Mapped[str]  # Строка! Не UUID. Например "invoices"
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

**Важно:** Поле `doctype` — это **строка** (код типа документа), а не UUID. В `ReferenceSelect` нужно подменять `id` на `item.doctype` в адаптере.

---

## 6. Модель Role (обновлённая)

```python
class RoleModel(Base):
    __tablename__ = "roles"
    __table_args__ = {"schema": "public"}
    
    id, tenant_id, name, description, is_active  # стандартные поля
    
    tenant = relationship("TenantModel", lazy="selectin")
    permissions = relationship("PermissionModel", back_populates="role", lazy="selectin", cascade="all, delete-orphan")
    
    @property
    def permissions_count(self) -> int: ...
```

---

## 7. Сигнатура ReferenceSelect (актуальная)

```tsx
export function ReferenceSelect<T extends ReferenceItem>({
  fetchFn,       // (params) => Promise<{ items: T[], total: number }>
  queryKey,      // string[]
  value,         // string
  onValueChange, // (value: string) => void
  placeholder,   // string
  disabled,      // boolean
  limit,         // number
  heading,       // string
  columns,       // Array<{ column: keyof T; label: string }>  ← ключ "column"!
}: ReferenceSelectProps<T>)
```

---

## 8. Текущая задача

Доработать вкладку **"Полномочия"** в модалке редактирования Роли:
1. Кнопка "Добавить" открывает `ReferenceSelect` для выбора doctype.
2. Справочник фильтруется по `tenant_id` роли (параметр `available_for_tenant_id`).
3. При выборе doctype создаётся запись `PermissionModel` через существующий `POST /permissions/`.
4. Список текущих полномочий отображается с флагами доступа.
5. Удаление через `DELETE /permissions/{id}` с подтверждением `AlertDialog`.
6. В `ReferenceSelect` адаптере `id` подменяется на `item.doctype` (строка).

---

## 9. Структура проекта

```
backend/
  app/
    core/
      auth/dependencies.py      # SuperAdminUser, CurrentUser, DBSession
      base_crud.py              # CRUDBase + @with_db_error_handling
      schemas.py                # ApiResponse, PaginatedResponse
      database.py               # Base, get_db
      users/                    # models, schemas, crud, router
      tenants/                  # models, schemas, crud, router
      roles/                    # models, schemas, crud, router
      permissions/              # models, schemas, crud, router (существует!)
      domains/                  # models, schemas, crud, router
      doctypes/                 # models, schemas, crud, router
    main.py                     # FastAPI app, CORS, include_router

frontend/
  src/
    api/generated/              # Orval-сгенерированные хуки и функции
    core/
      roles/EditRoleModal.tsx   # Модалка редактирования роли (вкладки)
      doctypes/DoctypesPage.tsx # Эталонный ReferenceSelect для domain
      tenants/EditTenantModal.tsx # Эталонный Switch
    lib/reusable/
      ReferenceSelect.tsx       # Универсальный компонент справочника
      TenantMultiSelect.tsx     # Мультиселект тенантов
    hooks/useResizableColumns.ts
```

---

## 10. Известные "грабли" (не наступать повторно)

| Проблема | Решение |
| :--- | :--- |
| `"self" is not accessed` в CRUD | Использовать `self.model` вместо прямого имени модели |
| `Type of parameter "self" is unknown` | Наследовать от `CRUDBase[Model, Create, Update]` |
| `Method overrides in incompatible manner` | Имена параметров совпадают с базовым классом: `obj_in`, `db_obj` |
| `ResponseValidationError: tuple` | Нет запятой после `return ApiResponse(...)`. `PaginatedResponse(...)` со скобками |
| `CORS error` на конкретном запросе | Искать 500/401 в терминале Uvicorn, а не чинить CORS |
| `AttributeError: .get() on ORM` | Использовать `getattr(obj, "attr")`, а не `obj.get("attr")` |
| `IntegrityError is not defined` | Импортировать `from sqlalchemy.exc import IntegrityError` |
| `Type 'undefined' not assignable to 'boolean'` | Zod: `.optional()`, `defaultValues`: `true`, Switch: `field.value` |
| `Resolver type mismatch` | Не использовать `.default()` в Zod-схеме, только `.optional()` |
| `Switch не переключается` | Паттерн из `EditTenantModal`: `checked={field.value}`, `onCheckedChange={field.onChange}` |
| `ReferenceSelect type error` | Адаптер в `fetchFn`, не менять `ReferenceSelect.tsx` |
| `role_doctypes unknown import` | Не нужна M2M таблица, использовать существующую `PermissionModel` |
| Старые значения в форме создания | `reset(CREATE_DEFAULTS)` при закрытии модалки |

---

Вставьте этот контекст в новый чат и продолжите с задачи №8 (вкладка "Полномочия").