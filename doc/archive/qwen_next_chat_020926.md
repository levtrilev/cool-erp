# 📋 Контекст проекта Cool ERP
**Используй этот документ как стартовый промпт в новом чате.** 

## 🎯 О проекте

**Cool ERP** — модульный монолит для управления предприятием. Многопользовательская система с multi-tenancy (каждая организация изолирована).

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
│   ├── __init__.py                  # Явные импорты всех моделей (для SQLAlchemy)
│   ├── database.py                  # engine, Base, get_db
│   ├── config.py                    # settings (DATABASE_URL и т.д.)
│   ├── schemas.py                   # ApiResponse, PaginatedResponse
│   ├── auth/                        # 🔐 Аутентификация
│   │   ├── models.py                # UserSession
│   │   ├── crud.py                  # crud_auth (authenticate и т.д.)
│   │   ├── router.py
│   │   ├── security.py              # get_password_hash, verify_password
│   │   └── dependencies.py          # get_current_session
│   ├── users/                       # 👤 Пользователи
│   │   ├── models.py                # UserModel
│   │   ├── schemas.py
│   │   ├── crud.py                  # crud_user
│   │   └── router.py
│   ├── tenant/                      # 🏢 Организации (тенанты)
│   │   ├── models.py                # TenantModel
│   │   ├── schemas.py
│   │   ├── crud.py                  # crud_tenant
│   │   └── router.py
│   ├── role/                        # 🎭 Роли (планируется)
│   ├── permission/                  # 🔑 Полномочия (планируется)
│   └── group/                       # 👥 Группы (планируется)
│
├── inventory/                       # 📦 ДОМЕН "СКЛАД" (планируется)
├── assets/                          # 🏗️ ДОМЕН "ОСНОВНЫЕ СРЕДСТВА" (планируется)
├── cashflow/                        # 💰 ДОМЕН "ДЕНЕЖНЫЕ СРЕДСТВА" (планируется)
└── payable/                         # 💳 ДОМЕН "КРЕДИТОРСКАЯ ЗАДОЛЖЕННОСТЬ" (планируется)
```

### Frontend (`frontend/src/`)
```
frontend/src/
├── api/generated/                   # Orval (автогенерация)
├── components/ui/                   # shadcn/ui компоненты
├── core/                            # 🛡️ Домен безопасности
│   ├── auth/                        # LoginForm, LoginModal
│   ├── users/                       # AdminUsersPage, EditUserModal, CreateUserModal
│   ├── tenant/                      # TenantPage
│   └── RegisterModal.tsx
├── inventory/                       # 📦 (планируется)
├── assets/                          # 🏗️ (планируется)
└── ...
```

### Структура внутри каждого домена/сущности
В каждой папке сущности (`users/`, `tenant/`, `role/` и т.д.) файлы именуются **коротко**:
- `models.py` — SQLAlchemy модели
- `schemas.py` — Pydantic схемы (Base, Create, Update, Response)
- `crud.py` — CRUD-класс с экземпляром `crud_xxx`
- `router.py` — FastAPI роутер
- `services.py` — бизнес-логика (если нужна)
- `dependencies.py` — зависимости (если нужны)

**НЕ** использовать префиксы в именах файлов (`crud_user.py` → просто `crud.py`, т.к. папка уже называется `users/`).

---

## 🎯 Установленные правила

### Правило №1: Чистая архитектура (ПРИОРИТЕТ)
При работе со связанными данными **всегда** использовать:
1. **SQLAlchemy `relationship`** с `back_populates` и `lazy="selectin"` в моделях
2. **`@property`** в ORM-модели для вычисляемых полей (например, `user.tenant_name`)
3. **`from_attributes=True`** в Pydantic-схемах
4. **Автоматическую конвертацию** через `ModelSchema.model_validate(orm_object)`

**❌ ЗАПРЕЩЕНО:** ручные словари вида `{"id": user.id, "name": user.name, ...}` в роутерах.

### Правило №2: Полный CRUD
При создании нового CRUD-класса всегда реализовывать **полный набор**:
- `create`
- `get` (по ID)
- `get_by_*` (по уникальным полям)
- `get_multi` (список с поиском и фильтрами)
- `get_multi_paginated` (возвращает `tuple[list[Model], int]`)
- `update`
- `delete` (с защитой от удаления, если есть связанные записи)

### Правило №3: API версионирование
- Версия задаётся **только** через `prefix="/api/v1"` в `main.py`
- Домены **не знают** о версиях
- При появлении v2: создаётся `router_v2.py` рядом с `router.py`, неизменившиеся роутеры переиспользуются

### Правило №4: Orval-совместимость
- Все эндпоинты, возвращающие списки, используют `PaginatedResponse[Schema]`
- Для обёртки успеха используется `ApiResponse[Schema]` с полями `success`, `message`, `data`
- Явная конвертация ORM → Pydantic через `.model_validate()`

### Правило №5: Frontend
- Для сложных полей в формах использовать `<Controller>` из react-hook-form
- Разделять состояния: `searchInput` (для ввода) и `search` (для запроса) — поиск по кнопке/Enter, а не на каждый символ
- Toast-уведомления через `useToast()` из shadcn/ui

### Правило №6: Именование роутов
- Публичные эндпоинты: `/public/register`
- Внутренние (для админов): `/register`
- Префиксы роутеров: `/auth`, `/tenants`, `/users`, `/roles` и т.д.

---

## 🗄 Схема базы данных

### Таблица `public.tenants`
```sql
id uuid PK DEFAULT uuid_generate_v4()
name varchar(128) UNIQUE NOT NULL
active boolean DEFAULT true
description varchar(255)
```

### Таблица `public.users`
```sql
id uuid PK DEFAULT uuid_generate_v4()
name varchar NOT NULL
email varchar UNIQUE NOT NULL
password varchar NOT NULL
is_admin boolean DEFAULT false
tenant_id uuid FK → public.tenants.id NOT NULL
role_ids uuid[] (nullable)
is_superadmin boolean DEFAULT false
```

### Таблица `public.user_sessions`
```sql
session_token varchar(64) PK
user_id uuid FK → public.users.id ON DELETE CASCADE
created_at timestamptz
expires_at timestamptz
ip_address varchar(45)
user_agent varchar(512)
is_active varchar(1) DEFAULT '1'
```

---

## ✅ Что уже реализовано

### Backend
- ✅ Multi-tenancy с таблицей `tenants`
- ✅ Аутентификация через сессии (HTTP-only cookies)
- ✅ Публичная регистрация с умной логикой:
  - Если организация существует → пользователь как рядовой
  - Если не существует → создаётся новая, пользователь как админ
- ✅ CRUD для пользователей и тенантов
- ✅ Поиск с пагинацией (`get_multi_paginated`)
- ✅ Связи relationship между `UserModel` ↔ `TenantModel` и `UserModel` ↔ `UserSession`
- ✅ `@property tenant_name` в `UserModel` для автоматического извлечения названия организации

### Frontend
- ✅ `RegisterModal.tsx` с публичной регистрацией (поле `tenant_name`, условный рендеринг результата)
- ✅ `AdminUsersPage.tsx` с поиском по кнопке/Enter (разделение `searchInput`/`search`)
- ✅ `EditUserModal`, `CreateUserModal`
- ✅ Toast-уведомления, подсветка записей, умная навигация между страницами

---

## ⚠️ Известные проблемы / Технические долги


## 🚀 Следующие задачи (бэклог)

1. **UI для управления тенантами** — страница с CRUD для организаций
2. **Изоляция данных (Multi-tenancy)** — фильтрация по `tenant_id` во всех CRUD
3. **RBAC** — модели `Role`, `Permission`, `Group` + middleware для проверки прав
4. **Новые бизнес-модули**: `inventory`, `assets`, `cashflow`, `payable`

---

## 📝 Команды

```bash
# Backend
cd backend
uvicorn app.main:app --reload

# Frontend
cd frontend
npm run dev          # Dev-сервер
npm run gen          # Перегенерация Orval (бэкенд должен быть запущен!)
npm run build        # Production build
```
 