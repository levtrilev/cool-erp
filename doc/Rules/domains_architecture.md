# Уточнённая архитектура модульного монолита: Ядро + Домены

## 1. Концепция: Ядро и Домены

### 1.1. Ядро (`core`) — платформа

Ядро — это **не домен**, а фундаментальная инфраструктура и общие справочники, доступные всем доменам.

**Сущности ядра:**

| Сущность | Назначение |
|----------|-----------|
| `tenants` | Организации (мульти-арендность) |
| `users` | Пользователи |
| `roles` | Роли |
| `sections` | Разделы доступа |
| `permissions` | Полномочия |
| `domains` | Домены (группировка типов документов) |
| `doctypes` | Типы документов (реестр) |
| `periods` | Периоды (новое) |
| `currencies` | Валюты (новое) |

**Характеристики ядра:**
- Общее для всех доменов
- Доступно через F-Keys и JOINs из любого домена
- **Не реплицируется** в домены (оно и так общее)
- Не содержит бизнес-логики доменов
- Не импортирует модели и сервисы доменов (зависимость однонаправленная: домен → ядро)

### 1.2. Домены (модули) — бизнес-логика

Домен — это **изолированная бизнес-область** со своими таблицами, моделями, сервисами и интерфейсом.

**Первый домен: `Operations`** (префикс `oper`)

| Сущность | Назначение |
|----------|-----------|
| `goods` | Товары |
| `legal_entities` | Юридические лица |
| `locations` | Локации / места |
| `persons` | Физические лица |
| `regions` | Регионы |
| `vat_invoices` | Счета-фактуры НДС |
| `warehouses` | Склады |
| `bank_accounts` | Банковские счета |

**Характеристики домена:**
- Изолирован от других доменов
- Имеет доступ к ядру (F-Keys, JOINs)
- Не имеет прямого доступа к таблицам других доменов
- Общается с другими доменами только через механизм репликации или сервисы

---

## 2. Правила взаимодействия

### 2.1. Матрица доступа

| Источник → Цель | Ядро | Домен А | Домен Б |
|-----------------|------|---------|---------|
| **Ядро** | ✅ | ❌ Запрещено | ❌ Запрещено |
| **Домен А** | ✅ | ✅ (внутри домена) | ❌ Только репликация |
| **Домен Б** | ✅ | ❌ Только репликация | ✅ (внутри домена) |

### 2.2. Разрешено

| Действие | Пример |
|----------|--------|
| Домен → Ядро: F-Keys | `oper_goods.tenant_id REFERENCES public.tenants(id)` |
| Домен → Ядро: JOINs | `oper_goods JOIN public.tenants ON ...` |
| Домен → Ядро: импорт сервисов | `from app.core.tenants.crud import crud_tenant` |
| Внутри домена: F-Keys | `oper_vat_invoices.goods_id REFERENCES oper_goods(id)` |
| Внутри домена: связи | `oper_warehouses.location_id → oper_locations.id` |
| Домен А → Домен Б: репликация | Через `core_outbox` / `core_replication_tasks` |
| Домен А → Домен Б: сервисы | Через публичный интерфейс сервиса домена Б |

### 2.3. Запрещено

| Действие | Почему |
|----------|--------|
| Ядро → Домен | Ядро не знает о доменах |
| Домен А → Домен Б: прямой SELECT | Нарушение изоляции |
| Домен А → Домен Б: F-Keys | Жёсткая связь между доменами |
| Домен А → Домен Б: импорт моделей | Обход изоляции на уровне кода |
| Домен А → Домен Б: JOIN | Прямой запрос к чужим таблицам |

---

## 3. Структура папок проекта

### 3.1. Бэкенд

```
backend/app/
├── main.py                            # FastAPI app, CORS, подключение роутеров
│
├── core/                              # ═══ ЯДРО (платформа) ═══
│   ├── __init__.py
│   ├── database.py                    # Base, get_db, engine, async_session
│   ├── schemas.py                     # ApiResponse, PaginatedResponse
│   ├── exceptions.py                  # Общие исключения
│   │
│   ├── crud/
│   │   └── base.py                    # CRUDBase + @with_db_error_handling
│   │
│   ├── auth/                          # Аутентификация и авторизация
│   │   ├── dependencies.py            # CurrentUser, DBSession, SuperAdminUser
│   │   ├── security.py                # get_current_session, хеширование
│   │   ├── models.py                  # UserSession
│   │   ├── crud.py
│   │   ├── schemas.py
│   │   └── router.py
│   │
│   ├── events/                        # Механизм репликации МЕЖДУ ДОМЕНАМИ
│   │   ├── models.py                  # core_outbox, core_inbox, core_replication_tasks
│   │   ├── outbox.py                  # Публикация событий
│   │   ├── inbox.py                   # Обработка событий
│   │   └── replicator.py             # Фоновый процесс синхронизации
│   │
│   ├── tenants/                       # Справочник: Организации
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── service.py
│   │   └── router.py
│   │
│   ├── users/                         # Пользователи
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── service.py
│   │   └── router.py
│   │
│   ├── roles/                         # Роли
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── service.py
│   │   └── router.py
│   │
│   ├── sections/                      # Разделы доступа
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── service.py
│   │   └── router.py
│   │
│   ├── permissions/                   # Полномочия
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── service.py
│   │   └── router.py
│   │
│   ├── domains/                       # Домены (группировка типов документов)
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── service.py
│   │   └── router.py
│   │
│   ├── doctypes/                      # Типы документов
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── service.py
│   │   ├── router.py
│   │   └── document_base.py           # DocumentAccessMixin, DocumentLifecycleMixin
│   │
│   ├── periods/                       # НОВОЕ: Периоды
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── service.py
│   │   └── router.py
│   │
│   └── currencies/                    # НОВОЕ: Валюты
│       ├── models.py
│       ├── schemas.py
│       ├── crud.py
│       ├── service.py
│       └── router.py
│
├── operations/                        # ═══ ДОМЕН: Операции (префикс `oper`) ═══
│   ├── __init__.py                    # Публичный интерфейс домена
│   │
│   ├── replica/                       # Реплики из ДРУГИХ ДОМЕНОВ (не из ядра)
│   │   ├── models.py                  # OperXxxReplica
│   │   ├── schemas.py
│   │   └── handlers.py               # Обработчики событий репликации
│   │
│   ├── goods/                         # Товары
│   │   ├── models.py                  # OperGoodsModel
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── service.py
│   │   └── router.py
│   │
│   ├── legal_entities/                # Юридические лица
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── service.py
│   │   └── router.py
│   │
│   ├── locations/                     # Локации
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── service.py
│   │   └── router.py
│   │
│   ├── persons/                       # Физические лица
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── service.py
│   │   └── router.py
│   │
│   ├── regions/                       # Регионы
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── service.py
│   │   └── router.py
│   │
│   ├── vat_invoices/                  # Счета-фактуры НДС
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── service.py
│   │   └── router.py
│   │
│   ├── warehouses/                    # Склады
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── service.py
│   │   └── router.py
│   │
│   └── bank_accounts/                 # Банковские счета
│       ├── models.py
│       ├── schemas.py
│       ├── crud.py
│       ├── service.py
│       └── router.py
│
└── {future_domain}/                   # Будущие домены
    └── ...
```

### 3.2. Фронтенд

```
frontend/src/
├── App.tsx                            # Роутинг
├── main.tsx                           # Точка входа
│
├── core/                              # ═══ ЯДРО (платформа) ═══
│   ├── api/
│   │   └── generated/                 # Orval-сгенерированный клиент
│   │       ├── fastAPI.schemas.ts
│   │       ├── tenants/
│   │       ├── users/
│   │       ├── roles/
│   │       ├── sections/
│   │       ├── permissions/
│   │       ├── doctypes/
│   │       ├── domains/
│   │       ├── periods/
│   │       └── currencies/
│   │
│   ├── tenants/
│   │   ├── TenantsPage.tsx
│   │   └── EditTenantModal.tsx
│   │
│   ├── users/
│   │   ├── AdminUsersPage.tsx
│   │   ├── EditUserModal.tsx
│   │   └── CreateUserModal.tsx
│   │
│   ├── roles/
│   │   ├── AdminRolesPage.tsx
│   │   ├── EditRoleModal.tsx
│   │   ├── PermissionsTab.tsx
│   │   └── UsersTab.tsx
│   │
│   ├── sections/
│   ├── permissions/
│   ├── doctypes/
│   ├── domains/
│   ├── periods/                       # НОВОЕ
│   └── currencies/                    # НОВОЕ
│
├── operations/                        # ═══ ДОМЕН: Операции ═══
│   ├── goods/
│   │   ├── GoodsPage.tsx
│   │   └── EditGoodModal.tsx
│   │
│   ├── legal_entities/
│   │   ├── LegalEntitiesPage.tsx
│   │   └── EditLegalEntityModal.tsx
│   │
│   ├── locations/
│   ├── persons/
│   ├── regions/
│   ├── vat_invoices/
│   ├── warehouses/
│   └── bank_accounts/
│
├── shared/                            # ОБЩИЕ КОМПОНЕНТЫ (не привязаны к домену)
│   ├── ui/                            # shadcn/ui
│   │   ├── button.tsx
│   │   ├── input.tsx
│   │   ├── dialog.tsx
│   │   ├── table.tsx
│   │   └── use-toast.ts
│   │
│   └── reusable/                      # Универсальные компоненты
│       ├── ReferenceSelect.tsx
│       ├── ReferenceMultiSelectChips.tsx
│       └── PermissionsTab.tsx         # Если переиспользуется
│
└── lib/
    ├── hooks/
    │   └── useResizableColumns.ts
    └── utils.ts
```

---

## 4. Правила именования таблиц

### 4.1. Ядро — без префикса

Таблицы ядра сохраняют текущие имена (без префикса) для минимизации миграции:

| Таблица | Префикс | Пример |
|---------|---------|--------|
| Организации | Нет | `tenants` |
| Пользователи | Нет | `users` |
| Роли | Нет | `roles` |
| Разделы | Нет | `sections` |
| Полномочия | Нет | `permissions` |
| Типы документов | Нет | `doctypes` |
| Домены | Нет | `domains` |
| Периоды (новое) | Нет | `periods` |
| Валюты (новое) | Нет | `currencies` |
| Инфраструктура репликации | `core_` | `core_outbox`, `core_inbox`, `core_replication_tasks` |
| Сессии | Нет | `user_sessions` |

**Обоснование:** существующие таблицы уже созданы без префикса. Переименование потребует миграции всех F-Keys. Для новых таблиц ядра (`periods`, `currencies`) тоже не используем префикс для единообразия. Префикс `core_` используется только для технической инфраструктуры репликации.

### 4.2. Домены — с префиксом

Каждый домен имеет свой уникальный префикс:

| Домен | Префикс | Примеры таблиц |
|-------|---------|---------------|
| Ядро (инфраструктура) | `core_` | `core_outbox`, `core_inbox`, `core_replication_tasks` |
| Operations | `oper_` | `oper_goods`, `oper_legal_entities`, `oper_vat_invoices` |
| (будущие) | — | — |

### 4.3. Реплики между доменами

Реплики таблиц из других доменов получают суффикс `_replica`:

```
{домен}_{сущность_источника}_replica
```

Примеры:
```
-- В домене Operations реплика таблицы из будущего домена "sales"
oper_sales_orders_replica

-- В будущем домене "sales" реплика товаров из Operations
sales_oper_goods_replica
```

**Важно:** реплики создаются **только между доменами**. Таблицы ядра не реплицируются — они доступны напрямую через F-Keys.

---

## 5. Схема БД: Ядро + Домен Operations

### 5.1. Таблицы ядра (существующие + новые)

```sql
-- ═══════════════════════════════════════════════════
-- ЯДРО: Существующие таблицы (без изменений)
-- ═══════════════════════════════════════════════════

-- Организации (существует)
-- public.tenants

-- Пользователи (существует)
-- public.users

-- Роли (существует)
-- public.roles

-- Разделы доступа (существует)
-- public.sections

-- Полномочия (существует)
-- public.permissions

-- Типы документов (существует)
-- public.doctypes

-- Домены (существует)
-- public.domains

-- ═══════════════════════════════════════════════════
-- ЯДРО: Новые таблицы
-- ═══════════════════════════════════════════════════

-- Периоды (НОВОЕ)
CREATE TABLE public.periods (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES public.tenants(id),
    name            VARCHAR(128) NOT NULL,          -- "2026 Q1", "Январь 2026"
    start_date      DATE NOT NULL,
    end_date        DATE NOT NULL,
    is_closed       BOOLEAN NOT NULL DEFAULT false, -- Закрыт ли период
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, name)
);

-- Валюты (НОВОЕ)
CREATE TABLE public.currencies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code            VARCHAR(3) NOT NULL UNIQUE,      -- "RUB", "USD", "EUR"
    name            VARCHAR(128) NOT NULL,           -- "Российский рубль"
    symbol          VARCHAR(16),                     -- "₽", "$", "€"
    decimal_places  SMALLINT NOT NULL DEFAULT 2,     -- Количество знаков после запятой
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ═══════════════════════════════════════════════════
-- ЯДРО: Инфраструктура репликации МЕЖДУ ДОМЕНАМИ
-- ═══════════════════════════════════════════════════

-- Исходящие события (транзакционный outbox)
CREATE TABLE public.core_outbox (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type      VARCHAR(128) NOT NULL,          -- 'goods.created', 'invoice.updated'
    source_domain   VARCHAR(64) NOT NULL,           -- 'operations'
    aggregate_type  VARCHAR(128) NOT NULL,          -- 'oper_goods'
    aggregate_id    UUID NOT NULL,                  -- ID сущности
    payload         JSONB NOT NULL,                 -- Данные события
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed       BOOLEAN NOT NULL DEFAULT false,
    processed_at    TIMESTAMPTZ
);

CREATE INDEX idx_core_outbox_unprocessed
    ON public.core_outbox (processed, occurred_at)
    WHERE processed = false;

-- Обработанные события (идемпотентность)
CREATE TABLE public.core_inbox (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id        UUID NOT NULL UNIQUE REFERENCES public.core_outbox(id),
    consumer_domain VARCHAR(64) NOT NULL,            -- 'operations', 'sales', ...
    processed_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Очередь задач на синхронизацию
CREATE TABLE public.core_replication_tasks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id        UUID NOT NULL REFERENCES public.core_outbox(id),
    target_domain   VARCHAR(64) NOT NULL,            -- 'operations', 'sales', ...
    target_table    VARCHAR(128) NOT NULL,           -- 'sales_oper_goods_replica'
    operation       VARCHAR(32) NOT NULL,            -- 'upsert', 'delete'
    payload         JSONB NOT NULL,
    status          VARCHAR(32) NOT NULL DEFAULT 'pending',
    attempts        INTEGER NOT NULL DEFAULT 0,
    last_error      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at    TIMESTAMPTZ,
    next_retry_at   TIMESTAMPTZ
);
```

### 5.2. Таблицы домена Operations

```sql
-- ═══════════════════════════════════════════════════
-- ДОМЕН: Операции (префикс `oper`)
-- ═══════════════════════════════════════════════════

-- Регионы
CREATE TABLE public.oper_regions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255) NOT NULL,
    code            VARCHAR(32),                      -- Код региона
    country_code    VARCHAR(2),                       -- ISO 3166-1 alpha-2
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Юридические лица
CREATE TABLE public.oper_legal_entities (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES public.tenants(id),  -- ✅ F-Key на ядро
    name            VARCHAR(255) NOT NULL,
    legal_name      VARCHAR(512),                     -- Полное юридическое название
    tax_id          VARCHAR(64),                      -- ИНН / налоговый идентификатор
    registration_number VARCHAR(64),                  -- ОГРН / регистрационный номер
    region_id       UUID REFERENCES public.oper_regions(id),  -- ✅ F-Key внутри домена
    address         TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, tax_id)
);

-- Физические лица
CREATE TABLE public.oper_persons (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES public.tenants(id),  -- ✅ F-Key на ядро
    first_name      VARCHAR(128) NOT NULL,
    middle_name     VARCHAR(128),
    last_name       VARCHAR(128),
    tax_id          VARCHAR(64),                      -- ИНН физического лица
    phone           VARCHAR(32),
    email           VARCHAR(255),
    region_id       UUID REFERENCES public.oper_regions(id),  -- ✅ F-Key внутри домена
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Локации
CREATE TABLE public.oper_locations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES public.tenants(id),  -- ✅ F-Key на ядро
    name            VARCHAR(255) NOT NULL,
    address         TEXT,
    region_id       UUID REFERENCES public.oper_regions(id),  -- ✅ F-Key внутри домена
    location_type   VARCHAR(64),                      -- Тип локации: "склад", "офис", "магазин"
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Склады
CREATE TABLE public.oper_warehouses (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES public.tenants(id),  -- ✅ F-Key на ядро
    location_id     UUID REFERENCES public.oper_locations(id),  -- ✅ F-Key внутри домена
    name            VARCHAR(255) NOT NULL,
    code            VARCHAR(64),                      -- Код склада
    warehouse_type  VARCHAR(64),                      -- Тип: "основной", "транзитный"
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, code)
);

-- Товары
CREATE TABLE public.oper_goods (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES public.tenants(id),  -- ✅ F-Key на ядро
    name            VARCHAR(255) NOT NULL,
    code            VARCHAR(64),                      -- Артикул / код товара
    unit            VARCHAR(32),                      -- Единица измерения: "шт", "кг", "л"
    currency_id     UUID REFERENCES public.currencies(id),  -- ✅ F-Key на ядро
    price           NUMERIC(18,4),                    -- Базовая цена
    vat_rate        NUMERIC(5,2),                     -- Ставка НДС: 0, 10, 20
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, code)
);

-- Банковские счета
CREATE TABLE public.oper_bank_accounts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES public.tenants(id),  -- ✅ F-Key на ядро
    legal_entity_id UUID NOT NULL REFERENCES public.oper_legal_entities(id),  -- ✅ F-Key внутри домена
    bank_name       VARCHAR(255),
    account_number  VARCHAR(64) NOT NULL,
    routing_number  VARCHAR(64),                      -- БИК / SWIFT
    currency_id     UUID REFERENCES public.currencies(id),  -- ✅ F-Key на ядро
    is_primary      BOOLEAN NOT NULL DEFAULT false,   -- Основной счёт
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, account_number, routing_number)
);

-- Счета-фактуры НДС (наиболее сложная сущность)
CREATE TABLE public.oper_vat_invoices (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES public.tenants(id),  -- ✅ F-Key на ядро
    period_id       UUID REFERENCES public.periods(id),  -- ✅ F-Key на ядро

    -- Связи внутри домена
    goods_id        UUID REFERENCES public.oper_goods(id),
    seller_id       UUID REFERENCES public.oper_legal_entities(id),  -- Продавец
    buyer_id        UUID REFERENCES public.oper_legal_entities(id),  -- Покупатель
    warehouse_id    UUID REFERENCES public.oper_warehouses(id),
    bank_account_id UUID REFERENCES public.oper_bank_accounts(id),

    -- Данные документа
    invoice_number  VARCHAR(64),                      -- Номер счёта-фактуры
    invoice_date    DATE NOT NULL,
    amount          NUMERIC(18,4) NOT NULL,           -- Сумма без НДС
    vat_amount      NUMERIC(18,4) NOT NULL DEFAULT 0, -- Сумма НДС
    total_amount    NUMERIC(18,4) NOT NULL,           -- Итого с НДС
    currency_id     UUID REFERENCES public.currencies(id),  -- ✅ F-Key на ядро

    -- Аудит (связь с ядром)
    created_by_user_id UUID REFERENCES public.users(id),  -- ✅ F-Key на ядро
    updated_by_user_id UUID REFERENCES public.users(id),  -- ✅ F-Key на ядро

    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, invoice_number, invoice_date)
);

-- Индексы
CREATE INDEX idx_oper_goods_tenant ON public.oper_goods (tenant_id);
CREATE INDEX idx_oper_goods_code ON public.oper_goods (tenant_id, code);
CREATE INDEX idx_oper_vat_invoices_tenant ON public.oper_vat_invoices (tenant_id);
CREATE INDEX idx_oper_vat_invoices_date ON public.oper_vat_invoices (invoice_date);
CREATE INDEX idx_oper_vat_invoices_period ON public.oper_vat_invoices (period_id);
CREATE INDEX idx_oper_legal_entities_tenant ON public.oper_legal_entities (tenant_id);
CREATE INDEX idx_oper_warehouses_tenant ON public.oper_warehouses (tenant_id);
CREATE INDEX idx_oper_bank_accounts_entity ON public.oper_bank_accounts (legal_entity_id);
```

### 5.3. Визуализация связей

```
┌─────────────────────────────────────────────────────────────────────┐
│                          ЯДРО (платформа)                            │
│                                                                     │
│  tenants ──────┬──────────────────────────────────────────────────  │
│  users ────────┤                                                    │
│  roles         │  F-Keys из доменов                                 │
│  sections      │                                                    │
│  permissions   │                                                    │
│  doctypes      │                                                    │
│  domains       │                                                    │
│  periods ◄─────┤──── oper_vat_invoices.period_id                   │
│  currencies ◄──┤──── oper_goods.currency_id                        │
│                │     oper_vat_invoices.currency_id                  │
│                │     oper_bank_accounts.currency_id                 │
│  core_outbox   │  ← Инфраструктура репликации между доменами       │
│  core_inbox    │                                                    │
│  core_replica..│                                                    │
└────────────────┼────────────────────────────────────────────────────┘
                 │
                 │  F-Keys (разрешено)
                 │
┌────────────────┼────────────────────────────────────────────────────┐
│                ▼                                                    │
│         ДОМЕН: Операции (префикс `oper`)                            │
│                                                                     │
│  oper_regions ◄──── oper_legal_entities.region_id                   │
│       ▲              oper_persons.region_id                         │
│       │              oper_locations.region_id                       │
│       │                                                             │
│  oper_locations ◄── oper_warehouses.location_id                     │
│                                                                     │
│  oper_goods                                                         │
│       ▲                                                             │
│       │                                                             │
│  oper_vat_invoices ──► oper_legal_entities (seller, buyer)          │
│       │             ──► oper_warehouses                             │
│       │             ──► oper_bank_accounts                          │
│       │                                                             │
│  oper_bank_accounts ──► oper_legal_entities                         │
│                                                                     │
│  replica/  ← Реплики из ДРУГИХ ДОМЕНОВ (не из ядра)                │
└─────────────────────────────────────────────────────────────────────┘
                 │
                 │  ❌ Прямые запросы запрещены
                 │  ✅ Только репликация через core_outbox
                 │
┌────────────────┼────────────────────────────────────────────────────┐
│                ▼                                                    │
│     ДОМЕН: {будущий домен} (префикс `???`)                          │
│  ...                                                                │
│  replica/                                                           │
│     └── ???_oper_goods_replica  ← Реплика товаров из Operations    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 6. Структура моделей в SQLAlchemy

### 6.1. Пример модели домена

```python
# backend/app/operations/goods/models.py
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.core.currencies.models import CurrencyModel
    from app.core.tenants.models import TenantModel


class OperGoodsModel(Base):
    """Товары — домен Операции."""

    __tablename__ = "oper_goods"  # ✅ Префикс домена
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )

    # ✅ F-Key на ядро
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.tenants.id"),  # ✅ Ссылка на ядро
        nullable=False,
        index=True,
    )

    # Специфичные поля домена
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    price: Mapped[float | None] = mapped_column(Numeric(18, 4), nullable=True)
    vat_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()")
    )

    # ✅ F-Key на ядро (валюта)
    currency_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.currencies.id"),  # ✅ Ссылка на ядро
        nullable=True,
    )

    # ✅ Связь с ядром для денормализации
    tenant: Mapped["TenantModel"] = relationship(
        "TenantModel", lazy="selectin"
    )
    currency: Mapped["CurrencyModel"] = relationship(
        "CurrencyModel", lazy="selectin"
    )

    @property
    def tenant_name(self) -> str | None:
        return self.tenant.name if self.tenant else None

    @property
    def currency_code(self) -> str | None:
        return self.currency.code if self.currency else None
```

### 6.2. Пример модели с внутренними связями домена

```python
# backend/app/operations/warehouses/models.py
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.core.tenants.models import TenantModel
    from app.operations.locations.models import OperLocationModel


class OperWarehouseModel(Base):
    """Склады — домен Операции."""

    __tablename__ = "oper_warehouses"
    __table_args__ = {"schema": "public"}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("uuid_generate_v4()"),
    )

    # ✅ F-Key на ядро
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.tenants.id"),
        nullable=False,
        index=True,
    )

    # ✅ F-Key ВНУТРИ домена
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("public.oper_locations.id"),  # ✅ Ссылка на таблицу своего домена
        nullable=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    warehouse_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()")
    )

    # Связи
    tenant: Mapped["TenantModel"] = relationship("TenantModel", lazy="selectin")
    location: Mapped["OperLocationModel"] = relationship(
        "OperLocationModel", lazy="selectin"
    )

    @property
    def tenant_name(self) -> str | None:
        return self.tenant.name if self.tenant else None

    @property
    def location_name(self) -> str | None:
        return self.location.name if self.location else None
```

---

## 7. Механизм репликации между доменами

Репликация нужна **только между доменами**, не между ядром и доменами. Ядро доступно напрямую через F-Keys и JOINs.

### 7.1. Когда нужна репликация

| Сценарий | Пример | Нужна репликация? |
|----------|--------|:---:|
| Домен использует данные ядра | `oper_goods.tenant_id → tenants.id` | ❌ Нет (прямой F-Key) |
| Домен А использует данные домена Б | `sales_orders.goods_id → oper_goods.id` | ✅ Да (репликация) |
| Домен А отображает имя сущности из домена Б | Название товара в заказе | ✅ Да (репликация) |

### 7.2. Пример реплики

Если будущий домен `sales` (префикс `sales`) нуждается в данных о товарах из домена `operations`:

```python
# backend/app/sales/replica/models.py
class SalesOperGoodsReplica(Base):
    """Реплика товаров из домена Операции для домена Продажи."""

    __tablename__ = "sales_oper_goods_replica"
    __table_args__ = {"schema": "public"}

    # ID оригинальной сущности (БЕЗ ForeignKey на чужой домен)
    goods_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )

    # Скопированные данные
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )

    # Метаданные синхронизации
    replica_version: Mapped[int] = mapped_column(default=1)
    replica_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
```

### 7.3. Обработчик репликации в домене-источнике

При изменении товара в домене `operations` публикуется событие:

```python
# backend/app/operations/goods/service.py
class GoodsService:
    async def create_goods(
        self,
        db: AsyncSession,
        goods_in: OperGoodsCreateSchema,
    ) -> OperGoodsModel:
        """Создание товара + публикация события для репликации."""
        new_goods = await crud_goods.create(db, obj_in=goods_in)

        # ✅ Публикуем событие для других доменов (если они существуют)
        await outbox.publish(
            db,
            event_type="goods.created",
            source_domain="operations",
            aggregate_type="oper_goods",
            aggregate_id=new_goods.id,
            payload={
                "id": str(new_goods.id),
                "name": new_goods.name,
                "code": new_goods.code,
                "tenant_id": str(new_goods.tenant_id),
                "is_deleted": False,
            },
        )
        # commit выполняется в роутере (Бэкенд Правило №31)
        return new_goods
```

### 7.4. Обработчик репликации в домене-получателе

```python
# backend/app/sales/replica/handlers.py
class OperGoodsReplicaHandler:
    """Обработчик репликации товаров из домена Операции."""

    def get_target_table(self) -> str:
        return "sales_oper_goods_replica"

    async def apply(
        self,
        db: AsyncSession,
        payload: dict[str, Any],
        operation: str,
    ) -> None:
        goods_id = payload["id"]

        if operation == "delete":
            # Мягкое удаление реплики
            stmt = select(SalesOperGoodsReplica).where(
                SalesOperGoodsReplica.goods_id == goods_id
            )
            result = await db.execute(stmt)
            replica = result.scalar_one_or_none()
            if replica:
                replica.is_deleted = True
                replica.replica_version += 1
                replica.replica_synced_at = datetime.now(timezone.utc)
        else:
            # Upsert реплики
            stmt = select(SalesOperGoodsReplica).where(
                SalesOperGoodsReplica.goods_id == goods_id
            )
            result = await db.execute(stmt)
            replica = result.scalar_one_or_none()

            if replica is None:
                replica = SalesOperGoodsReplica(
                    goods_id=goods_id,
                    name=payload["name"],
                    code=payload.get("code"),
                    tenant_id=payload["tenant_id"],
                )
                db.add(replica)
            else:
                replica.name = payload["name"]
                replica.code = payload.get("code")
                replica.tenant_id = payload["tenant_id"]
                replica.is_deleted = payload.get("is_deleted", False)
                replica.replica_version += 1
                replica.replica_synced_at = datetime.now(timezone.utc)


# Регистрация обработчика при старте приложения
register_handler(
    domain="sales",
    aggregate_type="oper_goods",
    handler=OperGoodsReplicaHandler(),
)
```

---

## 8. Публичный интерфейс домена

Каждый домен имеет файл `__init__.py`, определяющий публичный интерфейс — то, что другие домены могут импортировать:

```python
# backend/app/operations/__init__.py
"""
Домен: Операции
Публичный интерфейс (разрешён для импорта другими доменами)
"""
from app.operations.goods.service import goods_service
from app.operations.legal_entities.service import legal_entity_service
from app.operations.warehouses.service import warehouse_service

# ✅ Другие домены импортируют ТОЛЬКО из этого файла:
# from app.operations import goods_service
#
# ❌ Запрещено импортировать внутренние модули:
# from app.operations.goods.models import OperGoodsModel  ← НЕЛЬЗЯ

__all__ = ["goods_service", "legal_entity_service", "warehouse_service"]
```

---

## 9. Статическая проверка изоляции доменов

### 9.1. Правило импортов

```toml
# pyproject.toml или .import-linter

[tool.import-linter]
# Домен 'operations' не может импортировать из других доменов
[[tool.import-linter.contracts]]
name = "operations-isolation"
type = "forbidden"
source_modules = ["app.operations"]
forbidden_modules = [
    "app.sales",
    "app.hr",
    # ... другие домены
]
# Но можно импортировать из ядра
allow_modules = ["app.core"]
```

### 9.2. Проверка в CI

```bash
#!/bin/bash
# scripts/check_domain_isolation.sh

echo "Проверка изоляции доменов..."

# Проверяем, что домены не импортируют друг друга
for domain_dir in backend/app/*/; do
    domain_name=$(basename "$domain_dir")
    if [ "$domain_name" = "core" ] || [ "$domain_name" = "__pycache__" ]; then
        continue
    fi

    for other_domain_dir in backend/app/*/; do
        other_domain=$(basename "$other_domain_dir")
        if [ "$other_domain" = "core" ] || [ "$other_domain" = "$domain_name" ] || [ "$other_domain" = "__pycache__" ]; then
            continue
        fi

        # Проверяем импорты моделей и CRUD чужих доменов
        if grep -r "from app\.$other_domain" "$domain_dir" --include="*.py" | grep -v "replica/" | grep -v "__init__.py" | grep -v ".service"; then
            echo "❌ НАРУШЕНИЕ: Домен '$domain_name' импортирует из домена '$other_domain'"
            exit 1
        fi
    done
done

echo "✅ Изоляция доменов проверена"
```

---

## 10. План миграции и создания домена

### Этап 1: Создание структуры папок

```bash
# Бэкенд
mkdir -p backend/app/operations/{goods,legal_entities,locations,persons,regions,vat_invoices,warehouses,bank_accounts,replica}

# Фронтенд
mkdir -p frontend/src/operations/{goods,legal_entities,locations,persons,regions,vat_invoices,warehouses,bank_accounts}
```

### Этап 2: Создание таблиц БД

1. Создать таблицы `periods` и `currencies` в ядре
2. Создать таблицы `core_outbox`, `core_inbox`, `core_replication_tasks` в ядре
3. Создать таблицы домена `oper_*`

### Этап 3: Создание моделей, схем, CRUD, сервисов, роутеров

Для каждой сущности домена:
1. `models.py` — модель SQLAlchemy с префиксом `oper_`
2. `schemas.py` — Pydantic-схемы
3. `crud.py` — CRUD-класс, наследующий `CRUDBase`
4. `service.py` — бизнес-логика + публикация событий
5. `router.py` — FastAPI-роутер

### Этап 4: Подключение роутеров в `main.py`

```python
# backend/app/main.py
from app.operations.goods.router import router as oper_goods_router
from app.operations.legal_entities.router import router as oper_legal_entities_router
# ... остальные роутеры домена

app.include_router(oper_goods_router, prefix="/operations")
app.include_router(oper_legal_entities_router, prefix="/operations")
# ...
```

### Этап 5: Фронтенд

1. Обновить `orval.config.ts` для генерации клиента
2. Создать страницы и модалки для каждой сущности домена
3. Настроить роутинг

### Этап 6: Тестирование

1. Проверить, что домен не импортирует из других доменов
2. Проверить, что ядро не импортирует из доменов
3. Проверить, что репликация работает между доменами (когда появятся другие домены)

---

## 11. Будущая масштабируемость

### 11.1. Вынос домена на отдельный сервер

Если домен `operations` будет вынесен на отдельный сервер:

```
Сервер 1 (Ядро + Домен A):
├── Таблицы ядра: tenants, users, roles, ...
├── Таблицы домена A: oper_goods, oper_legal_entities, ...
└── Реплики из домена B: oper_sales_orders_replica, ...

Сервер 2 (Ядро + Домен B):
├── Таблицы ядра: tenants, users, roles, ...  ← Синхронизация ядра
├── Таблицы домена B: sales_orders, ...
└── Реплики из домена A: sales_oper_goods_replica, ...
```

**Что понадобится:**
1. Синхронизация данных ядра между серверами (пока не проектируем)
2. Репликация между доменами уже спроектирована (механизм `core_outbox`)
3. Префиксы таблиц позволяют чётко определить, какие таблицы принадлежат какому домену

### 11.2. Распределение домена между филиалами

Если домен `operations` будет распределён между удалёнными филиалами:

```
Филиал 1 (Ядро + часть операций):
├── Таблицы ядра: tenants, users, roles, ...
└── Таблицы домена (часть): oper_goods (только товары филиала 1)

Филиал 2 (Ядро + часть операций):
├── Таблицы ядра: tenants, users, roles, ...
└── Таблицы домена (часть): oper_goods (только товары филиала 2)

Центральный сервер:
├── Таблицы ядра (полные)
└── Агрегированные данные из филиалов
```

Префиксы `oper_` позволяют легко идентифицировать таблицы домена при репликации между филиалами.

---

## 12. Итоговая сводка

| Аспект | Решение |
|--------|---------|
| **Ядро** | `core`: `tenants`, `users`, `roles`, `sections`, `permissions`, `doctypes`, `domains`, `periods`, `currencies` |
| **Домены** | Изолированные бизнес-модули с префиксами таблиц |
| **Первый домен** | `Operations` (префикс `oper`) |
| **Сущности Operations** | `goods`, `legal_entities`, `locations`, `persons`, `regions`, `vat_invoices`, `warehouses`, `bank_accounts` |
| **Доступ домен → ядро** | ✅ Разрешён (F-Keys, JOINs) |
| **Доступ домен → домен** | ❌ Только репликация или сервисы |
| **Доступ ядро → домен** | ❌ Запрещён |
| **Репликация ядра** | ❌ Не нужна (ядро общее) |
| **Репликация между доменами** | ✅ Через `core_outbox` / `core_replication_tasks` |
| **Префиксы таблиц** | Ядро: без префикса; домены: `oper_`, `sales_`, и т.д. |
| **Структура папок** | `app/core/` для ядра, `app/operations/` для домена |
| **Будущая масштабируемость** | Префиксы позволяют выносить домены на отдельные серверы |

Если эта архитектура принята, следующим шагом будет детальная проработка каждой сущности домена `Operations`: модели, схемы, CRUD, сервисы, роутеры и фронтенд. Сообщите, с какой сущности начать.