# 📋 Контекст для продолжения работы в новом чате

Скопируйте весь текст ниже и вставьте в начало нового чата.

---

## 1. О проекте

**Cool ERP** — мульти-tenant ERP-система. 

**Стек:**
- **Backend:** FastAPI + SQLAlchemy 2.0 (async) + PostgreSQL
- **Frontend:** React + Vite + TypeScript + shadcn/ui + Orval + React Query + React Hook Form + Zod

**Авторизация:** через Cookie (не JWT в заголовках). Axios настроен с `withCredentials: true`.

---

## 2. Свод всех правил проекта (полный список 1–37)

### ЧАСТЬ 1: BACKEND

**Правило №1 (Чистая архитектура и ORM):**
- Вычисляемые поля — через `@property` в моделях.
- `relationship` с `back_populates` и `lazy="selectin"`.
- Pydantic-схемы ответов: `model_config = ConfigDict(from_attributes=True)`.

**Правило №2 (Зарезервировано)** — свободно для будущего использования.

**Правило №3 (Зарезервировано)** — свободно для будущего использования.

**Правило №4 (Orval-совместимость API):**
Все списковые эндпоинты возвращают `ApiResponse[PaginatedResponse[T]]`.

**Правило №5 (Зарезервировано)** — свободно для будущего использования.

**Правило №6 (Зарезервировано)** — свободно для будущего использования.

**Правило №7 (Зарезервировано)** — свободно для будущего использования.

**Правило №8 (Зарезервировано)** — свободно для будущего использования.

**Правило №21 (Именование схем):**
Суффиксы `CreateSchema`, `UpdateSchema`, `ResponseSchema`.

**Правило №26 (Multi-tenancy):**
Фильтрация по `tenant_id` на уровне SQL. Суперадмины видят всё.

**Правило №28 (Схема БД):**
Явная `{"schema": "public"}` в `__table_args__`. Именованные `UniqueConstraint`.

**Правило №30 (M2M синхронизация):**
Связи M2M синхронизируются в `create`/`update` через `insert`/`delete`.

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

**Правило №9 (Orval-хуки):**
Использование сгенерированных Orval-хуков для запросов (`useGetXxx`, `useCreateXxx`, `useUpdateXxx`, `useDeleteXxx`).

**Правило №10 (Использование существующих моделей):**
Не создавать M2M-таблицы, если уже есть подходящая модель (например, `PermissionModel`).

**Правило №11 (Компактные таблицы):**
`py-1`, `align-top` для ячеек таблицы.

**Правило №12 (Поиск через form):**
Поиск через `<form onSubmit>`, два стейта: `searchInput` и `search`.

**Правило №13 (Фиксированная ширина таблицы):**
`table-fixed w-full` для стабильного отображения колонок.

**Правило №14 (Sticky-заголовки таблицы):**
Заголовки таблицы закрепляются при прокрутке.

**Правило №15 (Зарезервировано)** — свободно для будущего использования.

**Правило №16 (Удаление через AlertDialog):**
Подтверждение удаления через `AlertDialog` с `AlertDialogAction`.

**Правило №17 (Подсветка строки):**
Через `useEffect` с `setTimeout` для временной подсветки (3 секунды).

**Правило №18 (Умная навигация):**
Определение страницы после сохранения и автоматический переход.

**Правило №19 (Зарезервировано)** — свободно для будущего использования.

**Правило №20 (Сброс формы):**
При закрытии модалки через `reset(CREATE_DEFAULTS)`. Константа `CREATE_DEFAULTS` объявляется вне компонента или в его начале.

**Правило №22 (Разделение состояний поиска):**
`searchInput` (ввод) и `search` (отправка в API).

**Правило №23 (Подсветка сохранённой записи):**
В паре с Правилом №18: визуальное выделение только что сохранённой записи.

**Правило №24 (invalidateQueries ДО закрытия):**
Строгий порядок: `invalidateQueries` → `onOpenChange(false)` → `reset(CREATE_DEFAULTS)` → `onSaved`.

**Правило №25 (refetch после удаления):**
После успешного удаления вызвать `refetch()` для обновления списка.

**Правило №27 (ReferenceSelect для справочников) — РАСШИРЕННАЯ РЕДАКЦИЯ:**

1. **Запрет на ручной ввод UUID:** Категорически запрещён `<Input>` для ввода или отображения UUID справочных значений.
2. **Обязательный паттерн адаптера в `fetchFn`:**
   ```tsx
   fetchFn={async (params) => {
     const response = await getXxxXxxGet(params);
     return {
       items: response?.data?.items ?? [],
       total: response?.data?.total ?? 0,
     };
   }}
   ```
3. **Подмена ID для строковых идентификаторов:** Если справочник использует строковый ID (например, `doctype`), его нужно подменить в адаптере:
   ```tsx
   const items = (response?.data?.items ?? []).map((item) => ({
     ...item,
     id: item.doctype, // Подмена UUID на строковый код
     name: item.doctype_name || item.doctype, // Гарантированное наличие поля name
   }));
   ```
4. **Формат дополнительных колонок:** Ключ `column` (не `key`!):
   ```tsx
   columns={[{ column: "description", label: "Описание" }]}
   ```
5. **✅ ОБЯЗАТЕЛЬНО: Использование `selectedLabel`:** Для мгновенного отображения имеющегося значения в режиме редактирования **обязательно** передавать проп:
   ```tsx
   selectedLabel={initialData?.related_name ?? "Выберите..."}
   ```
   Это гарантирует, что текстовая метка отобразится сразу при открытии модалки, не дожидаясь завершения асинхронного запроса `fetchFn`.
6. **🚫 ЗАПРЕЩЕНО:** Использовать `useEffect` с `queryClient.prefetchQuery` или `queryClient.setQueryData` исключительно для того, чтобы заставить `ReferenceSelect` показать название выбранного элемента. Это антипаттерн, решаемый только через проп `selectedLabel`.
7. **Неизменяемость компонента:** Проп `labelField` в компоненте НЕ существует. Прямое изменение файла `ReferenceSelect.tsx` запрещено.

**Правило №29 (Изменяемая ширина колонок):**
Через хук `useResizableColumns` с сохранением в localStorage.

**Правило №34 (Switch в формах):**
Через `Controller`: `checked={field.value}`, `onCheckedChange={field.onChange}`.
Рядом `Label` с `htmlFor`, меняющий цвет и иконку (`CheckCircle2`/`PauseCircle`).
В Zod-схеме: `z.boolean().optional()`. В `defaultValues`: `is_active: true`.

**Правило №35 (Вынесение модальных окон в отдельный компонент):**
Модальное окно редактирования (и создания) сущности **всегда** должно быть вынесено в отдельный компонент (например, `EditDoctypeModal.tsx`, `EditRoleModal.tsx`). Страница списка отвечает только за отображение данных и передачу `initialData`, а вся логика формы, валидации и мутаций инкапсулирована в модалке.

**Обязательные пропсы модального окна:**
```tsx
interface EditXxxModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData: XxxResponseSchema | null; // null = режим создания
  onSaved: (id: string, name?: string) => Promise<void>;
}
```

**Правило №36 (Безопасная обработка ошибок):**
В блоках `catch` и `onError` **запрещено** использовать тип `any`. Всегда использовать `unknown` с безопасным приведением типа:
```tsx
catch (error: unknown) {
  const err = error as { response?: { data?: { detail?: string } } };
  toast({
    variant: "destructive",
    title: "Ошибка",
    description: err?.response?.data?.detail || "Не удалось выполнить действие",
  });
}
```

**Правило №37 (Синхронизация формы при открытии модалки):**
При открытии модалки на редактирование данные из `initialData` должны синхронизироваться с формой через `useEffect` с зависимостями `[open, initialData, reset]`.

**🚫 КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО** вызывать `setState` (например, `setSelectedSectionIds`) внутри `useEffect` — это вызывает каскадные рендеры.

**Альтернативы для производных состояний:**
1. **Подход №1 (рекомендуется):** Интеграция в форму через `watch()` из `react-hook-form`.
2. **Подход №2:** Паттерн с `key` на контейнере для принудительного пересоздания компонента.

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
- `auth` (Cookie-based, `dependencies.py` с `SuperAdminUser`, `CurrentUser`, `DBSession`)
- `users`
- `tenants` (включая `EditTenantModal` с эталонным Switch)
- `roles` (CRUD + роутер + фронтенд)
- `domains` (models, schemas, crud, router, DomainsPage.tsx)
- `doctypes` (models, schemas, crud, router, DoctypesPage.tsx с ReferenceSelect для domain)
- `permissions` (models, schemas, crud, router — уже существуют)

### 🔧 В процессе доработки:
- Вкладка "Полномочия" в модалке редактирования Роли. Нужно добавить кнопку "Добавить" с `ReferenceSelect` для выбора doctype из справочника (фильтрованного по `tenant_id` роли).

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

**Важно:** Поле `doctype` — это строка (код типа документа), а не UUID. В `ReferenceSelect` нужно подменять `id` на `item.doctype` в адаптере.

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
  selectedLabel, // ✅ string — для мгновенного отображения при редактировании
}: ReferenceSelectProps<T>)
```

---

## 8. Текущая задача

Доработать вкладку "Полномочия" в модалке редактирования Роли:
- Кнопка "Добавить" открывает `ReferenceSelect` для выбора doctype.
- Справочник фильтруется по `tenant_id` роли (параметр `available_for_tenant_id`).
- При выборе doctype создаётся запись `PermissionModel` через существующий `POST /permissions/`.
- Список текущих полномочий отображается с флагами доступа.
- Удаление через `DELETE /permissions/{id}` с подтверждением `AlertDialog`.
- В `ReferenceSelect` адаптере `id` подменяется на `item.doctype` (строка).

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
|----------|---------|
| "self" is not accessed в CRUD | Использовать `self.model` вместо прямого имени модели |
| Type of parameter "self" is unknown | Наследовать от `CRUDBase[Model, Create, Update]` |
| Method overrides in incompatible manner | Имена параметров совпадают с базовым классом: `obj_in`, `db_obj` |
| ResponseValidationError: tuple | Нет запятой после `return ApiResponse(...)`. `PaginatedResponse(...)` со скобками |
| CORS error на конкретном запросе | Искать 500/401 в терминале Uvicorn, а не чинить CORS |
| AttributeError: .get() on ORM | Использовать `getattr(obj, "attr")`, а не `obj.get("attr")` |
| IntegrityError is not defined | Импортировать `from sqlalchemy.exc import IntegrityError` |
| Type 'undefined' not assignable to 'boolean' | Zod: `.optional()`, `defaultValues`: `true`, Switch: `field.value` |
| Resolver type mismatch | Не использовать `.default()` в Zod-схеме, только `.optional()` |
| Switch не переключается | Паттерн из `EditTenantModal`: `checked={field.value}`, `onCheckedChange={field.onChange}` |
| ReferenceSelect type error | Адаптер в `fetchFn`, не менять `ReferenceSelect.tsx` |
| role_doctypes unknown import | Не нужна M2M таблица, использовать существующую `PermissionModel` |
| Старые значения в форме создания | `reset(CREATE_DEFAULTS)` при закрытии модалки |
| Домен не отображается при редактировании | Использовать проп `selectedLabel={initialData?.domain_name ?? "Выберите..."}` в `ReferenceSelect` |
| setState в useEffect вызывает каскадные рендеры | Использовать `watch()` из `react-hook-form` или паттерн с `key` |
| unexpected any в catch/onError | Использовать `unknown` с безопасным приведением типа |

---

## 11. Эталонные примеры кода

### EditUserModal.tsx — эталон использования `selectedLabel` в ReferenceSelect

```tsx
<Controller
  name="tenant_id"
  control={control}
  render={({ field }) => (
    <ReferenceSelect
      fetchFn={async (params) => {
        const response = await readTenantsTenantsGet(params);
        return {
          items: response?.items ?? [],
          total: response?.total ?? 0,
        };
      }}
      queryKey={["tenants", "active"]}
      value={field.value || ""}
      onValueChange={field.onChange}
      placeholder="Выберите организацию"
      selectedLabel={user?.tenant_name ?? "Выберите организацию"} // ✅ КЛЮЧЕВОЙ ПРОП
      heading="Выберите организацию"
      columns={[{ column: "description", label: "Описание" }]}
    />
  )}
/>
```

### Синхронизация формы при открытии модалки (Правило №37)

```tsx
useEffect(() => {
  if (open) {
    if (initialData) {
      reset({
        name: initialData.name || "",
        description: initialData.description || "",
        is_active: initialData.is_active ?? true,
      });
    } else {
      reset(CREATE_DEFAULTS);
    }
  }
}, [open, initialData, reset]);
```

### Безопасная обработка ошибок (Правило №36)

```tsx
catch (error: unknown) {
  const err = error as { response?: { data?: { detail?: string } } };
  toast({
    variant: "destructive",
    title: "Ошибка",
    description: err?.response?.data?.detail || "Не удалось выполнить действие",
  });
}
```

---

Вставьте этот контекст в новый чат и продолжите с задачи №8 (вкладка "Полномочия").