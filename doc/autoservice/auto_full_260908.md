Проект "Автосервис" на базе платформы "Cool ERP"

Техническое задание (ТЗ) / Постановка задачи на разработку функционала системы управления автосервисом. Документ структурирован по стандартам, понятным для бэкенд и фронтенд-разработчиков.
------------------------------
## Техническое задание: Система онлайн-бронирования и учета для автосервиса## 1. Термины и сущности (Data Model)

* Пост (Подъемник): Производственная единица. Имеет статус (активен/на обслуживании).
* Мастер: Сотрудник сервиса. Обладает ставкой/процентом для расчета ЗП (необходимо заложить в модель).
* Тайм-слот (Слот): Дискретная единица времени (базово — 1 час). Привязывается к дате, Посту и (опционально) Мастеру.
* Заказ (Бронирование): Запись, связывающая Клиента, Автомобиль, Слот(ы), Мастера, Статус и финансовые показатели.
* Лог (Аудит): Запись о действии пользователя (Кто, Что, Когда, Изменения).

------------------------------
## 2. Ролевая модель и права доступа (RBAC)

| Роль | Права и ограничения |
|---|---|
| Клиент | Самостоятельная регистрация/авторизация. Видит только свободные слоты без имен Мастеров. Может создать Заказ (указав авто и причину). Может отменить Заказ только в статусе Создан (до акцепта Мастером). Видит только свою историю. Лимит: 1 слот в день на 1 авто; макс. N слотов на будущее (настройка администратора). |
| Мастер | Видит только свои Заказы и расписание. Переводит Заказ в Акцептован (может изменить длительность слота от 30 мин до нескольких часов). Ставит отметку В работе (факт начала). Переводит в Завершен (вводит текст отчета и стоимость). |
| Менеджер | Полный операционный доступ: видит всё. Распределяет Мастеров по Постам. Создает расписание, исключает Посты/Мастеров из пула. Принимает оплату, закрывает кассу. |
| Администратор | Все права Менеджера + конфигурация системы: управление пользователями, роли, настройка системных параметров (например, лимит N заказов для Клиента). |

------------------------------
## 3. Жизненный цикл Заказа (Statuses)

   1. Создан (Черновик): Забронирован Клиентом. Доступна отмена Клиентом.
   2. Акцептован (Подтвержден): Мастер подтвердил заказ и скорректировал время. Отмена клиентом заблокирована.
   3. В работе: Выставлена отметка о фактическом начале.
   4. Выполнен: Мастер ввел текстовый отчет и финальную стоимость.
   5. Оплачен: Менеджер принял деньги в кассу. Заказ закрыт.
   6. Отменен: Аннулирован Клиентом или Менеджером.

------------------------------
## 4. Спецификация функциональных требований (Use Cases)## 4.1. Управление расписанием и графиком (Бэкенд/Админ-панель)

* Фиксированный день: Задается базовое рабочее время (например, 09:00 - 18:00).
* Планирование 1-го уровня (Краткосрочное): Менеджер жестко связывает пару [Пост + Мастер] на конкретные слоты.
* Планирование 2-го уровня (Долгосрочное): Возможность выставить Слот [Пост] в статус "Доступен для бронирования" без назначения конкретного Мастера.
* Исключение из пула: Менеджер может заблокировать конкретный Пост или Мастера на определенный период (ремонт, отпуск). Существующие в этом интервале заказы должны подсвечиваться как "Требуют переноса".

## 4.2. Логика изменения длительности (Мастер)

* При акцепте Мастер может изменить длительность Слота:
* Уменьшение: до 0.5 часа (освобождает остаток часа для других).
   * Увеличение: до нескольких часов. Система должна проверить, что следующие слоты на данном Посту свободны. Если заняты — выдать ошибку валидации (требуется перенос на другой Пост/время).

## 4.3. Ограничения для Клиента (Валидация API)

* Запрет на бронирование > 1 слота в день на один и тот же госномер/VIN автомобиля.
* Запрет на бронирование > N (значение из конфига, например, 3) активных заказов на будущие периоды суммарно.

## 4.4. Финал работы и Касса

* Форма завершения работы (Мастер): Поле ввода (string, text) + Поле стоимости (decimal).
* Печать заказ-квитанции: Генерация PDF/HTML-формы для печати (содержит: Дата, Клиент, Авто, Мастер, Пост, Перечень работ из текста, Итоговая сумма).
* Прием оплаты: Фиксация транзакции в БД с обязательной транзакционной привязкой к ID Заказа (что автоматически дает связку с Постом и Мастером).

------------------------------
## 5. Требования к отчетности (BI / Analytics)
Необходимо реализовать два отчета с фильтрацией по Дата Начала и Дата Окончания периода:

   1. Ведомость о доходах:
   * Группировка: [День] -> [Мастер] и [Пост].
      * Метрики: Сумма выручки (только по заказам в статусе Оплачен).
   2. Ведомость по зарплате:
   * Группировка: [Мастер].
      * Метрики: Общая стоимость выполненных им работ, расчетная ЗП (согласно формуле из профиля мастера, заложить базово Сумма * Процент_Мастера).
   
------------------------------
## 6. Системные и Технические требования (Non-Functional)

* Логирование действий (Audit Log): Любой запрос, изменяющий состояние БД (POST/PUT/DELETE), должен записываться в таблицу логов: timestamp, user_id, action_type, entity_name, entity_id, payload_changes (желательно в формате JSONB).
* Конкурентность (Race Conditions): При одновременном бронировании одного слота двумя клиентами, база данных должна использовать пессимистическую блокировку (SELECT FOR UPDATE) или механизм транзакций isolation level SERIALIZABLE, чтобы исключить double-booking.

# 📋 Актуализированные правила проекта Cool ERP

## 🎯 О проекте

**Cool ERP** — модульный монолит для управления предприятием. Многопользовательская система с multi-tenancy (каждая организация изолирована).

---

## 🛠 Технологический стек

### Backend
- **FastAPI** + Python 3.11+
- **SQLAlchemy 2.0** (async, Mapped/mapped_column стиль)
- **Pydantic v2** (с `model_config = {"from_attributes": True}`)
- **PostgreSQL** (схема `public`, UUID через `uuid_generate_v4()`)
- **Alembic** для миграций

### Frontend
- **React 18** + **TypeScript** + **Vite**
- **Tailwind CSS** + **shadcn/ui**
- **React Hook Form** + **Zod** (валидация)
- **TanStack Query (React Query)** — управление серверным состоянием
- **Orval** — автогенерация типобезопасных API-клиентов из OpenAPI
- **Lucide React** — иконки

---

## 📁 Структура проекта

### Backend (`backend/app/`)
```
backend/app/
├── main.py                          # Точка входа, регистрация роутеров
├── core/                            # 🛡️ ДОМЕН БЕЗОПАСНОСТИ И RBAC
│   ├── __init__.py                  # Явные импорты всех моделей
│   ├── database.py                  # engine, Base, get_db
│   ├── config.py                    # settings
│   ├── schemas.py                   # ApiResponse, PaginatedResponse
│   ├── auth/                        # 🔐 Аутентификация
│   ├── users/                       # 👤 Пользователи
│   ├── tenants/                     # 🏢 Организации
│   ├── roles/                       # 🎭 Роли
│   ├── permissions/                 # 🔑 Полномочия
│   └── groups/                      # 👥 Группы
├── inventory/                       # 📦 ДОМЕН "СКЛАД"
├── assets/                          # 🏗️ ДОМЕН "ОСНОВНЫЕ СРЕДСТВА"
├── cashflow/                        # 💰 ДОМЕН "ДЕНЕЖНЫЕ СРЕДСТВА"
└── payable/                         # 💳 ДОМЕН "КРЕДИТОРСКАЯ ЗАДОЛЖЕННОСТЬ"
```

### Frontend (`frontend/src/`)
```
frontend/src/
├── api/generated/                   # Orval (автогенерация)
├── components/ui/                   # shadcn/ui компоненты
├── lib/reusable/                    # Переиспользуемые компоненты
│   └── ReferenceSelect.tsx          # Универсальный справочник
├── core/                            # 🛡️ Домен безопасности
│   ├── auth/
│   ├── users/
│   ├── tenants/
│   └── ...
├── inventory/
├── assets/
└── ...
```

---

# ЧАСТЬ 1. АРХИТЕКТУРА И BACKEND

## Правило №1: Чистая архитектура (ПРИОРИТЕТ)
При работе со связанными данными **всегда** использовать:
1. **SQLAlchemy `relationship`** с `back_populates` и `lazy="selectin"` в моделях
2. **`@property`** в ORM-модели для вычисляемых полей (например, `user.tenant_name`)
3. **`from_attributes=True`** в Pydantic-схемах
4. **Автоматическую конвертацию** через `ModelSchema.model_validate(orm_object)`

**❌ ЗАПРЕЩЕНО:** ручные словари вида `{"id": user.id, "name": user.name, ...}` в роутерах.

## Правило №2: Полный CRUD
При создании нового CRUD-класса всегда реализовывать **полный набор**:
- `create`
- `get` (по ID)
- `get_by_*` (по уникальным полям)
- `get_multi` (список с поиском и фильтрами)
- `get_multi_paginated` (возвращает `tuple[list[Model], int]`)
- `update`
- `delete` (с защитой от удаления, если есть связанные записи)

## Правило №3: API версионирование
- Версия задаётся **только** через `prefix="/api/v1"` в `main.py`
- Домены **не знают** о версиях
- При появлении v2: создаётся `router_v2.py` рядом с `router.py`, неизменившиеся роутеры переиспользуются

## Правило №4: Orval-совместимость (Backend)
- Все эндпоинты, возвращающие списки, используют `PaginatedResponse[Schema]`
- Для обёртки успеха используется `ApiResponse[Schema]` с полями `success`, `message`, `data`
- Явная конвертация ORM → Pydantic через `.model_validate()`

## Правило №5: Именование роутов
- Публичные эндпоинты: `/public/register`
- Внутренние (для админов): `/register`
- Префиксы роутеров: `/auth`, `/tenants`, `/users`, `/roles` и т.д.

## Правило №6: Именование файлов в доменах
В каждой папке сущности файлы именуются **коротко**, БЕЗ префиксов:
- `models.py` — SQLAlchemy модели
- `schemas.py` — Pydantic схемы
- `crud.py` — CRUD-класс с экземпляром `crud_xxx`
- `router.py` — FastAPI роутер
- `services.py` — бизнес-логика (если нужна)
- `dependencies.py` — зависимости (если нужны)

**❌ ЗАПРЕЩЕНО:** `crud_user.py`, `router_tenant.py` и т.п.

## Правило №7: Именование сущностей во множественном числе
Все сущности, папки доменов и таблицы в базе данных именуются **во множественном числе**:
- ✅ `tenants`, `users`, `roles`, `permissions`, `groups`
- ❌ `tenant`, `user`, `role`, `permission`, `group`

Это применяется к:
- Названиям папок: `backend/app/core/tenants/`, `frontend/src/core/tenants/`
- Названиям таблиц БД: `public.tenants`, `public.users`
- Названиям переменных в коде: `tenants`, `users` (НЕ `tenant`, `user` для коллекций)

---

# ЧАСТЬ 2. FRONTEND — ОБЩИЕ ПРАВИЛА

## Правило №8: Frontend — формы и состояния
- Для сложных полей в формах использовать `<Controller>` из react-hook-form
- **Разделять состояния:** `searchInput` (для ввода) и `search` (для запроса) — поиск по кнопке/Enter, а не на каждый символ
- Toast-уведомления через `useToast()` из shadcn/ui

## Правило №9: Использование Orval хуков
Вместо `useQuery`/`useMutation` напрямую использовать сгенерированные Orval хуки:
```tsx
// ✅ Правильно
const { data, isLoading, refetch } = useReadTenantsTenantsGet({ skip, limit, search });
const deleteMutation = useDeleteTenantTenantsTenantIdDelete();
const createMutation = useCreateTenantTenantsPost();
const updateMutation = useUpdateTenantTenantsTenantIdPut();

// ❌ Неправильно
const { data } = useQuery({ queryKey: [...], queryFn: () => readTenantsTenantsGet(...) });
```

## Правило №10: Импорт типов из Orval
- **Функции** (API-вызовы) — из `@/api/generated/<domain>/<domain>`
- **Типы** (схемы) — из `@/api/generated/fastAPI.schemas`

```tsx
// ✅ Правильно
import { useReadTenantsTenantsGet } from "@/api/generated/tenants/tenants";
import type { TenantResponseSchema } from "@/api/generated/fastAPI.schemas";

// ❌ Неправильно
import { TenantResponseSchema } from "@/api/generated/tenants/tenants"; // не экспортируется
```

## Правило №21: Именование Pydantic-схем
Все классы Pydantic-схем (`Base`, `Create`, `Update`, `Response` и т.д.) **обязательно** должны заканчиваться словом `Schema`.

**Примеры:**
- ✅ `SectionBaseSchema`, `SectionCreateSchema`, `SectionUpdateSchema`, `SectionResponseSchema`
- ❌ `SectionBase`, `SectionCreate`, `TenantResponse`, `UserUpdate`

---

# ЧАСТЬ 3. FRONTEND — СПИСОЧНЫЕ ФОРМЫ (CRUD СТРАНИЦЫ)

## Правило №11: Компактные отступы для десктопа
Все списочные формы должны использовать компактные отступы, чтобы помещаться на экране без прокрутки:
- Контейнер: `container mx-auto px-4 py-3` (НЕ `py-8` или больше)
- Заголовок: `text-xl font-bold` (НЕ `text-3xl`)
- Блок заголовка: `flex flex-col md:flex-row justify-between items-start md:items-center gap-2 mb-2`
- Счётчик записей: `<p className="text-xs text-muted-foreground mt-0.5">Всего: {total}</p>`

## Правило №12: Поиск через form
Поиск должен быть обёрнут в `<form>` для перехвата Enter:
```tsx
<form onSubmit={handleSearch} className="flex gap-2 flex-1 md:flex-initial">
  <Input
    placeholder="Поиск..."
    value={searchInput}
    onChange={(e) => setSearchInput(e.target.value)}
    className="w-full md:w-64"
  />
  <Button type="submit" variant="secondary">
    <Search className="h-4 w-4 mr-2" />
    Найти
  </Button>
</form>
```

## Правило №13: Таблица с компактным форматированием
- Обёртка таблицы: `<div className="rounded-md border bg-card">`
- Заголовки таблицы: `className="h-10 py-2"`
- Ячейки данных: `className="py-1"` (НЕ стандартные padding)
- Пустое состояние: `className="text-center text-muted-foreground py-8"`

## Правило №14: Первая колонка как ссылка для редактирования
НЕ использовать отдельную кнопку редактирования. Вместо этого первая колонка должна быть кликабельной ссылкой:
```tsx
<TableCell className="py-1">
  <button
    type="button"
    onClick={() => handleEdit(item)}
    className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer text-left font-medium"
  >
    {item.name}
  </button>
</TableCell>
```

## Правило №15: Пагинация с номерами страниц
Использовать массив номеров страниц с логикой отображения максимум 5 элементов:
```tsx
{Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
  let pageNum = i + 1;
  if (totalPages > 5 && page > 3) {
    pageNum = page - 2 + i;
  }
  if (pageNum > totalPages) return null;
  return (
    <PaginationItem key={pageNum}>
      <PaginationLink
        isActive={page === pageNum}
        onClick={() => setPage(pageNum)}
        className="cursor-pointer"
      >
        {pageNum}
      </PaginationLink>
    </PaginationItem>
  );
})}
```

## Правило №16: Кнопка удаления с AlertDialog
Кнопка удаления должна использовать `AlertDialog` для подтверждения (**НЕ** `confirm()`):
```tsx
<AlertDialog open={deleteId === item.id} onOpenChange={(open) => !open && setDeleteId(null)}>
  <AlertDialogTrigger asChild>
    <Button
      variant="ghost"
      size="icon"
      className="text-destructive hover:text-destructive hover:bg-destructive/10"
    >
      <Trash2 className="h-4 w-4" />
    </Button>
  </AlertDialogTrigger>
  <AlertDialogContent>...</AlertDialogContent>
</AlertDialog>
```

## Правило №17: Подсветка строки после создания/обновления
После успешного создания или обновления записи строка в таблице должна подсвечиваться жёлтым цветом на 3 секунды:
- Состояние: `const [highlightedId, setHighlightedId] = useState<string | null>(null);`
- Автосброс через `useEffect` с `setTimeout(3000)`
- Класс подсветки на `TableRow`:
```tsx
<TableRow
  className={
    highlightedId === item.id
      ? "bg-yellow-100 dark:bg-yellow-900/30 transition-colors duration-300"
      : ""
  }
>
```

## Правило №18: Умные toast-уведомления с навигацией
После создания/обновления записи необходимо определить, на какой странице она находится.

**ПОРЯДОК ДЕЙСТВИЙ (СТРОГО СОБЛЮДАТЬ):**
1. ✅ **СНАЧАЛА** вызвать `refetch()` для обновления данных текущей страницы
2. ✅ **ПОТОМ** проверить, есть ли запись на текущей странице
3. ✅ Если запись на текущей странице → **подсветить строку**
4. ✅ Если записи нет на текущей странице → **искать в полном списке** и показать toast с кнопкой "Перейти"

```tsx
const handleItemCreated = async (newId: string) => {
  // ✅ ШАГ 1: Обновляем данные текущей страницы
  const result = await refetch();
  const currentItems = result.data?.items || [];
  
  // ✅ ШАГ 2: Проверяем, есть ли запись на текущей странице
  const itemExists = currentItems.some((i) => i.id === newId);

  if (itemExists) {
    // ✅ ШАГ 3: Запись на текущей странице - подсвечиваем
    setHighlightedId(newId);
    toast({ title: "Создано", description: "Запись добавлена и выделена в списке" });
    return;
  }

  // ✅ ШАГ 4: Записи нет на текущей странице - ищем в полном списке
  try {
    const allData = await readAllItems({ limit: 1000, skip: 0 });
    const itemIndex = allData.items.findIndex((i) => i.id === newId);
    const targetPage = Math.floor(itemIndex / limit) + 1;

    toast({
      title: "Создано",
      description: `Запись переместилась на страницу ${targetPage}`,
      action: (
        <Button variant="outline" size="sm" onClick={() => {
          setPage(targetPage);
          setTimeout(() => setHighlightedId(newId), 500);
        }}>
          Перейти
        </Button>
      ),
    });
  } catch (error) {
    console.error("Ошибка поиска записи:", error);
    toast({
      variant: "destructive",
      title: "Ошибка",
      description: "Не удалось определить местоположение записи",
    });
  }
};
```

## Правило №19: Callback-и из модалок в страницу
Модалки создания/редактирования должны принимать callback-и от родительской страницы:
- `onItemCreated: (newId: string) => void` — для модалки создания
- `onItemUpdated: (itemId: string, itemName: string) => void` — для модалки редактирования

Эти callback-и вызываются после успешного сохранения и отвечают за подсветку и навигацию.

## Правило №20: Модальные компоненты редактирования
Все модальные компоненты редактирования (EditTenantModal, EditUserModal и т.п.) **ОБЯЗАТЕЛЬНО** должны:

1. **Проверка на null** — обёртка `{editing<Имя> && (...)}`
2. **Key для перемонтирования** — `key={editing<Имя>.id}`

```tsx
// ✅ Правильно
{editUser && (
  <EditUserModal
    key={editUser.id}
    open={editModalOpen}
    onOpenChange={setEditModalOpen}
    user={editUser}
    onUserUpdated={handleUserUpdated}
  />
)}

// ❌ Неправильно (без проверки на null) — TS ошибка
<EditUserModal
  open={editModalOpen}
  user={editUser}        // ← 'editUser' is possibly 'null'
  onUserUpdated={handleUserUpdated}
/>

// ❌ Неправильно (без key) — форма кэширует значения предыдущей записи
{editUser && (
  <EditUserModal
    open={editModalOpen}
    user={editUser}
    onUserUpdated={handleUserUpdated}
  />
)}
```

**Зачем:** React-hook-form кэширует значения формы. При смене записи без `key` компонент не перемонтируется и показывает данные предыдущей записи. `key={id}` принудительно пересоздаёт компонент.

## Правило №22: Обязательная структура состояний списочной страницы

Каждая списочная CRUD-страница (`XxxPage.tsx`) **ОБЯЗАТЕЛЬНО** должна содержать следующий набор состояний:

```tsx
// --- Состояния поиска и пагинации ---
const [searchInput, setSearchInput] = useState("");  // для ввода
const [search, setSearch] = useState("");             // для запроса (меняется по Enter)
const [page, setPage] = useState(1);
const [limit] = useState(10);

// --- Состояния модалок ---
const [isCreateOpen, setIsCreateOpen] = useState(false);
const [editModalOpen, setEditModalOpen] = useState(false);
const [editingXxx, setEditingXxx] = useState<XxxResponseSchema | null>(null);
const [deleteXxxId, setDeleteXxxId] = useState<string | null>(null);

// --- Подсветка строки ---
const [highlightedXxxId, setHighlightedXxxId] = useState<string | null>(null);
```

**Критические требования:**
1. ✅ **Разделять `searchInput` и `search`** — поиск выполняется ТОЛЬКО по нажатию кнопки/Enter, а не на каждый символ.
2. ✅ **Автосброс подсветки** через `useEffect`:
```tsx
useEffect(() => {
  if (highlightedXxxId) {
    const timer = setTimeout(() => setHighlightedXxxId(null), 3000);
    return () => clearTimeout(timer);
  }
}, [highlightedXxxId]);
```
3. ✅ **Обработка загрузки и ошибок** — обязательный рендер `Loader2` при `isLoading` и текста ошибки при `isError`.

## Правило №23: Алгоритм умной навигации после создания/обновления (ОБЯЗАТЕЛЬНО)

Обработчики `handleXxxCreated` и `handleXxxUpdated` **ОБЯЗАТЕЛЬНО** должны следовать **строгому 4-шаговому алгоритму**:

1. **СНАЧАЛА `await refetch()`**, потом проверка
2. Использовать **прямую функцию** `readXxxXxxGet` (импортируется из Orval), а **НЕ** хук `useReadXxxXxxGet`
3. **`setTimeout(..., 500)`** перед подсветкой при переходе на другую страницу
4. **Обработка `catch`** с `console.error` и деструктивным toast

## Правило №24: Обязательный вызов `invalidateQueries` в модалке

Каждая модалка редактирования/создания **ОБЯЗАТЕЛЬНО** должна инвалидировать кэш **ДО** вызова callback родителя:

```tsx
onSuccess: async () => {
  // ✅ 1. СНАЧАЛА инвалидируем кэш
  queryClient.invalidateQueries({ queryKey: ["xxx"] });
  // ✅ 2. ЗАКРЫВАЕМ модалку
  onOpenChange(false);
  // ✅ 3. ПОТОМ вызываем callback родителя (с await!)
  await onXxxUpdated(xxx.id, data.name);
}
```

**Порядок строго фиксирован**: `invalidateQueries` → `onOpenChange(false)` → `await onXxxUpdated(...)`.

## Правило №25: Обязательный `refetch()` после удаления

После успешного удаления записи **ОБЯЗАТЕЛЬНО** вызывать `await refetch()` для обновления списка:

```tsx
const handleDelete = (xxxId: string) => {
  deleteMutation.mutate(
    { xxxId },
    {
      onSuccess: async () => {
        toast({ title: "Запись удалена", description: "..." });
        await refetch(); // ← ОБЯЗАТЕЛЬНО!
        setDeleteXxxId(null);
      },
      // ...
    },
  );
};
```

---

# ЧАСТЬ 4. (Правило 26): Безопасность Multi-Tenancy

# ЧАСТЬ 5. ПЕРЕИСПОЛЬЗУЕМЫЙ КОМПОНЕНТ REFERENCESELECT

## Правило №27: Обязательное использование компонента ReferenceSelect для справочников

**Все** выпадающие списки для выбора из справочника (тенанты, разделы, категории и т.д.) **ОБЯЗАТЕЛЬНО** должны использовать переиспользуемый компонент `ReferenceSelect`, расположенный в `frontend/src/lib/reusable/ReferenceSelect.tsx`.

### 🎯 Зачем нужен ReferenceSelect

Стандартный `<Select>` из shadcn/ui не подходит для справочников с большим количеством записей, потому что:
- Загружает все записи сразу (проблема с производительностью при 1000+ записях)
- Не поддерживает поиск
- Не поддерживает пагинацию
- Закрывается при вводе текста (конфликт с Radix UI)

`ReferenceSelect` решает все эти проблемы:
- ✅ Серверная пагинация (по 10 записей на страницу)
- ✅ Серверный поиск с debounce (300 мс)
- ✅ Клавиатурная навигация (стрелки + Enter)
- ✅ Поддержка дополнительных колонок
- ✅ Автоматическое открытие на странице выбранного элемента
- ✅ Безопасная фильтрация по tenant_id на бэкенде

### 📦 Архитектура компонента

```tsx
// frontend/src/lib/reusable/ReferenceSelect.tsx

import { useState, useEffect, useMemo, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, ChevronsUpDown, Loader2, ChevronLeft, ChevronRight, ChevronsRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

// ✅ Универсальный тип для элемента справочника
export interface ReferenceItem {
  id: string;
  name: string;
  [key: string]: unknown; // Позволяет обращаться к произвольным полям
}

// ✅ Тип возвращаемых данных для пагинированного запроса
export interface PaginatedReferenceResponse<T extends ReferenceItem> {
  items: T[];
  total: number;
}

// ✅ Тип для описания дополнительных колонок
export interface ReferenceColumn {
  column: string; // Имя поля в объекте (например, "description")
  label: string;  // Заголовок колонки (например, "Описание")
}

// ✅ Пропсы компонента
export interface ReferenceSelectProps<T extends ReferenceItem> {
  fetchFn: (params: { skip: number; limit: number; search?: string }) => Promise<PaginatedReferenceResponse<T>>;
  queryKey: string[];
  value: string | undefined;
  onValueChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  limit?: number;              // Количество записей на странице (по умолчанию 10)
  selectedLabel?: string;      // Название выбранного элемента (для мгновенного отображения)
  heading?: string;            // Заголовок окна выбора
  columns?: ReferenceColumn[]; // Дополнительные колонки
}

export function ReferenceSelect<T extends ReferenceItem>({
  fetchFn,
  queryKey,
  value,
  onValueChange,
  placeholder = "Выберите...",
  disabled = false,
  limit = 10,
  selectedLabel,
  heading,
  columns,
}: ReferenceSelectProps<T>) {
  // ... (полный код компонента см. ниже)
}
```

### 📄 Актуальная версия компонента (полный код)

```tsx
import { useState, useEffect, useMemo, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { Check, ChevronsUpDown, Loader2, ChevronLeft, ChevronRight, ChevronsRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

export interface ReferenceItem {
  id: string;
  name: string;
  [key: string]: unknown;
}

export interface PaginatedReferenceResponse<T extends ReferenceItem> {
  items: T[];
  total: number;
}

export interface ReferenceColumn {
  column: string;
  label: string;
}

export interface ReferenceSelectProps<T extends ReferenceItem> {
  fetchFn: (params: { skip: number; limit: number; search?: string }) => Promise<PaginatedReferenceResponse<T>>;
  queryKey: string[];
  value: string | undefined;
  onValueChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  limit?: number;
  selectedLabel?: string;
  heading?: string;
  columns?: ReferenceColumn[];
}

export function ReferenceSelect<T extends ReferenceItem>({
  fetchFn,
  queryKey,
  value,
  onValueChange,
  placeholder = "Выберите...",
  disabled = false,
  limit = 10,
  selectedLabel,
  heading,
  columns,
}: ReferenceSelectProps<T>) {
  const [open, setOpen] = useState(false);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [localLabel, setLocalLabel] = useState<string | undefined>(undefined);

  const fetchFnRef = useRef(fetchFn);
  useEffect(() => {
    fetchFnRef.current = fetchFn;
  }, [fetchFn]);

  const hasColumns = columns && columns.length > 0;

  const handleOpenChange = (isOpen: boolean) => {
    setOpen(isOpen);
    if (isOpen) {
      setSelectedIndex(0);
    }
  };

  // При открытии справочника с выбранным значением находим страницу элемента
  useEffect(() => {
    if (open && value) {
      fetchFnRef.current({ limit: 1000, skip: 0 })
        .then((allData) => {
          if (allData?.items) {
            const index = allData.items.findIndex((item) => item.id === value);
            if (index !== -1) {
              const targetPage = Math.floor(index / limit) + 1;
              setPage(targetPage);
              setSelectedIndex(index % limit);
            }
          }
        })
        .catch((error) => {
          console.error("Ошибка поиска страницы элемента:", error);
        });
    }
  }, [open, value, limit]);

  // Debounce для поиска (300 мс)
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput);
      setPage(1);
      setSelectedIndex(0);
    }, 300);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const { data, isLoading } = useQuery({
    queryKey: [...queryKey, page, search],
    queryFn: () =>
      fetchFn({
        skip: (page - 1) * limit,
        limit,
        search: search || undefined,
      }),
    staleTime: 5 * 60 * 1000,
    enabled: open,
  });

  const items = useMemo(() => data?.items ?? [], [data?.items]);
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / limit);

  const handlePageChange = (newPage: number) => {
    setPage(newPage);
    setSelectedIndex(0);
  };

  const displayLabel = useMemo(() => {
    if (value) {
      if (localLabel) return localLabel;
      const found = items.find((item) => item.id === value);
      if (found) return found.name;
      if (selectedLabel) return selectedLabel;
    }
    return placeholder;
  }, [value, localLabel, items, selectedLabel, placeholder]);

  const handleSelect = (itemId: string) => {
    const selectedItem = items.find((i) => i.id === itemId);
    if (selectedItem) {
      setLocalLabel(selectedItem.name);
    }
    onValueChange(itemId);
    setOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (items.length === 0) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => {
        const next = Math.min(prev + 1, items.length - 1);
        setTimeout(() => {
          const el = document.getElementById(`cmd-item-${items[next].id}`);
          el?.scrollIntoView({ block: "nearest" });
        }, 0);
        return next;
      });
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => {
        const next = Math.max(prev - 1, 0);
        setTimeout(() => {
          const el = document.getElementById(`cmd-item-${items[next].id}`);
          el?.scrollIntoView({ block: "nearest" });
        }, 0);
        return next;
      });
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (items[selectedIndex]) {
        handleSelect(items[selectedIndex].id);
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      setOpen(false);
    }
  };

  const renderPagination = () => {
    if (totalPages <= 1) return null;

    const pages: React.ReactNode[] = [];
    const maxVisible = 5;
    let startPage = Math.max(1, page - Math.floor(maxVisible / 2));
    let endPage = Math.min(totalPages, startPage + maxVisible - 1);

    if (endPage - startPage + 1 < maxVisible) {
      startPage = Math.max(1, endPage - maxVisible + 1);
    }

    pages.push(
      <Button key="prev" size="sm" variant="outline" className="h-8 w-8 p-0" disabled={page === 1} onClick={() => handlePageChange(Math.max(1, page - 1))}>
        <ChevronLeft className="h-4 w-4" />
      </Button>
    );

    if (startPage > 1) {
      pages.push(<Button key="first" size="sm" variant="outline" className="h-8 w-8 p-0" onClick={() => handlePageChange(1)}>1</Button>);
      if (startPage > 2) pages.push(<span key="dots1" className="px-1 text-muted-foreground">...</span>);
    }

    for (let i = startPage; i <= endPage; i++) {
      pages.push(
        <Button key={i} size="sm" variant={page === i ? "default" : "outline"} className="h-8 w-8 p-0" onClick={() => handlePageChange(i)}>
          {i}
        </Button>
      );
    }

    if (endPage < totalPages) {
      if (endPage < totalPages - 1) pages.push(<span key="dots2" className="px-1 text-muted-foreground">...</span>);
      pages.push(
        <Button key="last" size="sm" variant="outline" className="h-8 px-2" onClick={() => handlePageChange(totalPages)}>
          End <ChevronsRight className="h-3 w-3 ml-1" />
        </Button>
      );
    }

    pages.push(
      <Button key="next" size="sm" variant="outline" className="h-8 w-8 p-0" disabled={page === totalPages} onClick={() => handlePageChange(Math.min(totalPages, page + 1))}>
        <ChevronRight className="h-4 w-4" />
      </Button>
    );

    return <div className="flex items-center justify-center gap-1 pt-2 border-t mt-2">{pages}</div>;
  };

  return (
    <Popover open={open} onOpenChange={handleOpenChange}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between font-normal"
          disabled={disabled}
        >
          <span className={cn("truncate", !value && "text-muted-foreground")}>
            {isLoading && !displayLabel ? (
              <span className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" /> Загрузка...
              </span>
            ) : (
              displayLabel
            )}
          </span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      
      <PopoverContent 
        className={cn(
          "p-0 overflow-hidden",
          hasColumns ? "min-w-[480px] max-w-[90vw]" : "w-[--radix-popover-trigger-width]"
        )}
        align="start"
        sideOffset={4}
      >
        <Command shouldFilter={false} className="min-h-[240px]">
          {heading && (
            <div className="px-3 py-1.5 border-b font-medium text-sm bg-muted/50">
              {heading}
            </div>
          )}
          
          <CommandInput
            placeholder="Поиск по названию..."
            value={searchInput}
            onValueChange={setSearchInput}
            className="h-8 border-0 focus-visible:ring-0 pl-3"
            onKeyDown={handleKeyDown}
          />

          {hasColumns && (
            <div className="flex items-center gap-4 px-3 py-1 border-b bg-muted/30 text-xs font-medium text-muted-foreground">
              <div className="w-4 mr-2 shrink-0" />
              <span className="flex-1 min-w-0">Название</span>
              {columns.map((col) => (
                <span key={col.column} className="w-[140px] shrink-0 truncate">
                  {col.label}
                </span>
              ))}
            </div>
          )}
          
          <CommandList className="max-h-[min(330px,60vh)] overflow-y-auto">
            <CommandEmpty className="py-2 text-center text-sm text-muted-foreground">
              {isLoading ? "Загрузка..." : "Ничего не найдено"}
            </CommandEmpty>
            
            {items.map((item, index) => (
              <CommandItem
                key={item.id}
                id={`cmd-item-${item.id}`}
                value={item.id}
                className={cn(
                  "cursor-pointer px-3 py-1",
                  index === selectedIndex && "bg-accent text-accent-foreground"
                )}
                onSelect={() => handleSelect(item.id)}
                onMouseEnter={() => setSelectedIndex(index)}
              >
                <Check
                  className={cn(
                    "mr-2 h-4 w-4 shrink-0",
                    value === item.id ? "opacity-100" : "opacity-0"
                  )}
                />
                
                {hasColumns ? (
                  <div className="flex-1 flex items-center gap-4 min-w-0">
                    <span className="flex-1 truncate text-sm font-medium">
                      {item.name}
                    </span>
                    {columns.map((col) => (
                      <span
                        key={col.column}
                        className="w-[140px] shrink-0 truncate text-sm text-muted-foreground"
                      >
                        {item[col.column] != null ? String(item[col.column]) : "—"}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span className="truncate text-sm">{item.name}</span>
                )}
              </CommandItem>
            ))}
          </CommandList>
          
          {renderPagination()}
        </Command>
      </PopoverContent>
    </Popover>
  );
}
```

### 🔧 Использование в формах создания

**Обязательный паттерн** для модалок создания (`CreateXxxModal.tsx`):

```tsx
import { Controller } from "react-hook-form";
import { ReferenceSelect } from "@/lib/reusable/ReferenceSelect";
import { readTenantsTenantsGet } from "@/api/generated/tenants/tenants";

// Внутри компонента:
const { control } = useForm<CreateUserFormData>({
  resolver: zodResolver(createUserSchema),
  defaultValues: {
    tenant_id: "",
  },
});

// В JSX:
<Controller
  name="tenant_id"
  control={control}
  render={({ field }) => (
    <ReferenceSelect
      fetchFn={async (params) => {
        const response = await readTenantsTenantsGet(params);
        // ✅ Адаптация ответа Orval под формат ReferenceSelect
        return {
          items: response?.items ?? [],
          total: response?.total ?? 0,
        };
      }}
      queryKey={["tenants", "active"]}
      value={field.value || ""}
      onValueChange={field.onChange}
      placeholder="Выберите организацию"
      heading="Выберите организацию"
    />
  )}
/>
```

### 🔧 Использование в формах редактирования

**Обязательный паттерн** для модалок редактирования (`EditXxxModal.tsx`):

```tsx
import { Controller } from "react-hook-form";
import { ReferenceSelect } from "@/lib/reusable/ReferenceSelect";
import { readTenantsTenantsGet } from "@/api/generated/tenants/tenants";

// Внутри компонента:
const { control } = useForm<EditUserFormData>({
  resolver: zodResolver(editUserSchema),
  defaultValues: {
    tenant_id: "",
  },
});

// В JSX:
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
      heading="Выберите организацию"
      // ✅ Передаём название для мгновенного отображения
      selectedLabel={user?.tenant_name}
    />
  )}
/>
```

### 📋 Обязательные требования при использовании ReferenceSelect

1. ✅ **Всегда использовать `<Controller>`** из react-hook-form для связывания с формой
2. ✅ **Адаптировать `fetchFn`** — возвращать `{ items, total }`, а не сырой ответ Orval
3. ✅ **Передавать `selectedLabel`** в формах редактирования для мгновенного отображения
4. ✅ **Использовать `heading`** для заголовка окна выбора
5. ✅ **Использовать `columns`** для отображения дополнительных полей (если нужно)

### 🚫 ЗАПРЕЩЕНО

- ❌ Использовать стандартный `<Select>` из shadcn/ui для справочников
- ❌ Загружать все записи справочника сразу (без пагинации)
- ❌ Реализовывать поиск на клиенте (только серверный поиск)
- ❌ Передавать `tenant_id` из фронтенда для фильтрации (только бэкенд)

---

## 📋 Финальный чек-лист для нового домена

При создании нового домена (например, `inventory`) проверить:

### Backend:
- [ ] Модель имеет `tenant_id` с `ForeignKey`
- [ ] CRUD фильтрует по `tenant_id` (кроме суперадмина)
- [ ] Роутер передаёт `session.tenant_id` и `user.is_superadmin`
- [ ] Эндпоинт защищён `get_current_session`

### Frontend:
- [ ] Страница использует `ReferenceSelect` для справочников
- [ ] Модалки используют `<Controller>` для связывания с формой
- [ ] Передаётся `selectedLabel` в формах редактирования
- [ ] Используется `heading` и `columns` (если нужно)

---

## 🎯 Заключение

Эти 27 правил покрывают все аспекты разработки в проекте Cool ERP:
- **Часть 1** (Правила 1–7): Архитектура и Backend
- **Часть 2** (Правила 8–10, 21): Frontend — общие
- **Часть 3** (Правила 11–20, 22–25): Frontend — списочные формы
- **Часть 4** (Правило 26): Безопасность Multi-Tenancy
- **Часть 5** (Правило 27): Переиспользуемый компонент ReferenceSelect
