# Cool ERP

[![GitHub license](https://img.shields.io/github/license/levtrilev/cool-erp)](LICENSE)
<!-- [![GitHub stars](https://img.shields.io/github/stars/levtrilev/cool-erp)](https://github.com/levtrilev/cool-erp/stargazers) -->

**Cool ERP** (https://coolerp.ru) — это мультиарендная, модульная, легко расширяемая корпоративная ERP-система с открытым кодом, специально адаптированная для надежной ИИ-генерации новых функций. Монорепозиторий FastAPI/Orval + Vite/React/TailwindCSS/TanStackQuery.

**Cool ERP** — это система, построенная на принципах **«явное управление» и «безопасность по умолчанию»**. Ни один слой доступа не предоставляет прав «по умолчанию» и не снимает ограничений автоматически. Применена гибридная моделью разграничения доступа (RBAC + ABAC)

🌐 **Официальный сайт проекта:** [coolerp.ru](https://coolerp.ru) (under construction)

Для старта разработки собственной ERP-системы с чистого листа на базе шаблона под лицензией MIT (которая позволяет свободно модифицировать, коммерциализировать и закрывать исходный код) классические ERP-гиганты вроде Odoo (LGPL/коммерческая) или ERPNext (GPL) не подойдут из-за инфекционного характера их лицензий, требующих открывать ваш код.
**Cool ERP** попадает в один ряд с лучшими готовыми Open Source шаблонами, каркасы (boilerplates) и платформами с лицензией MIT для разработки своей ERP

## Ближайшие аналоги:
* 1. FastAPI React Starter by raythurman2386:
https://github.com/raythurman2386/fastapi-react-starter

* 2. Full-Stack FastAPI Template (by Tiangolo):
https://github.com/fastapi/full-stack-fastapi-template
---

## 📄 Лицензия

Этот проект распространяется под лицензией **MIT**. Подробности в файле [LICENSE](LICENSE).

---

## 🚀 Ключевые особенности:
- 🔐 **Гибридная модель доступа** (ТЗ §8): роли × разделы × типы документов × теги × уровни
- 🏢 **Полная изоляция данных** между организациями (мульти-тенантность на уровне SQL)
- 📄 **Универсальный документный контракт** — единая модель для любых типов документов
- ⚡ **Двухуровневая система блокировок** — оптимистическая (`version` → 409) + пессимистическая (`/lock` → 423)
- 🏷️ **Тег-ориентированная видимость** — документы с тегами `регион:сибирь`, `гриф:секретно` видны только обладателям соответствующих допусков

---

## 🛠️ Стек технологий

* **Backend:** FastAPI + SQLAlchemy 2.0 async + Pydantic v2
* **Frontend:** React + TS + Vite + Tailwind + shadcn/ui + RHF + Zod + React Query (TanStack) + Orval
* **База данных:** PostgreSQL

---

### 🧩 Оркестрация ИИ (AI) на основе правил
Разработка ведётся по **строгому своду правил**, покрывающих:
- Типобезопасность на всех слоях (от моделей до API)
- Паттерны форм, поиска, модалок, таблиц
- Мультиарендность на уровне SQL
- Обработку ошибок и уведомления

---


## 🤝 Участие в разработке (Contributing)

Мы рады любому вкладу в развитие проекта! Чтобы внести изменения:
1. Сделайте форк репозитория.
2. Создайте ветку для вашей фичи (`git checkout -b feature/AmazingFeature`).
3. Закоммитьте изменения (`git commit -m 'Add some AmazingFeature'`).
4. Отправьте ветку в origin (`git push origin feature/AmazingFeature`).
5. Откройте Pull Request.

---


## 🚀 Почему этот проект крутой для контрибьюторов

### 🛠 Технологический стек

| Слой | Технологии |
|------|------------|
| **Backend** | Python 3.12 · FastAPI · SQLAlchemy 2.0 (async) · Pydantic v2 |
| **Frontend** | React 18 · Vite · TypeScript (strict) · shadcn/ui · Tailwind CSS |
| **API-клиент** | Orval (генерация из OpenAPI) · TanStack Query |
| **Формы** | React Hook Form + Zod |
| **База данных** | PostgreSQL · ручные SQL-миграции · схема `public` |
| **Авторизация** | Cookie-based (`httponly`, `samesite=lax`) |

### 🏗️ Архитектура, которой можно гордиться

✅ **Модульный монолит** — каждый домен (`auth`, `tenant`, `user`) в отдельной папке  
✅ **Чистая структура** — `models.py`, `schemas.py`, `crud.py`, `router.py` в каждом модуле  
✅ **Разделение ответственности** — CRUD для работы с БД, Services для бизнес-логики  
✅ **Типобезопасность end-to-end** — от Pydantic-схем до TypeScript-интерфейсов  
✅ **Автоматическая генерация API** — Orval создаёт хуки React Query из OpenAPI  

--- 

## 📞 Контакты

* **Email:** levtrishankov@yandex.ru
* **Telegram:** [@coolerp_community](https://t.me/coolerp) (under construction)


## 📦 Быстрый старт (under construction)

### Требования (under construction)
Перед началом убедитесь, что у вас установлены:
* Node.js (версии 18 и выше)
* Docker (опционально)

### Установка (under construction)

1. Склонируйте репозиторий:
   ```bash
   git clone https://github.com/levtrilev/cool-erp.git
   cd coolerp
   ```

2. Установите зависимости:
   ```bash
   npm install
   ```

3. Настройте конфигурацию:
   Создайте файл `.env` на основе примера `.env.example` и укажите ваши настройки БД.(under construction)

4. Запустите проект в режиме разработки:
   ```bash
   npm run dev
   ```

---

## Текущее состояние разработки Cool ERP (**06 ноября 2026**)

### 1. Подсистема контроля доступа (RBAC + ABAC, ТЗ v2.1) — ✅ реализована

Компонент: `app/core/access/service.py` (`AccessService`).

- `resolve_access()` — 9 шагов ТЗ §8.2: тенант → роли → разделы → permission →
  максимальный уровень → переключатели тегов → правило «нет тегов» → тег-проверка → финал.
- `build_access_filter()` / `build_replica_access_filter()` — SQL-фильтр видимости
  для списков (RLS-семантика, ТЗ §2.6), включая тег-условия на уровне SQL
  (операторы `&&`, `<@`, GIN-индексы; без `func.*` — Правило №44).
- Уровни: 4 (полный) > 3 (редактор) > 2 (автор) > 1 (читатель) > 0 (нет).
- `can_delete = (флаг роли) OR (уровень ≥ 2)`; потолок раздела «Общий»:
  для не-Суперадмина уровень 1, `can_delete = false` (§4.3.3).
- Создание/перемещение в раздел «Общий» — только Суперадмин (Вариант D).
- Протоколы типизации: `DocumentProtocol`, `DocumentClassProtocol`,
  `ReplicaClassProtocol` (каст `typing_cast` в точке вызова — Правило №47).
- **Ограничение периода**: таблица `user_role_grants` (ТЗ §10) не создана;
  роли читаются через `user.role_ids` (fallback обратной совместимости, ТЗ §8.2 ШАГ 2).

---

### 2. Контракт документов и блокировки (Правило №40) — ✅ реализовано

- Миксины: `DocumentAccessMixin` (5 полей ТЗ §3.3) + `DocumentLifecycleMixin`
  (статус, номер, дата, version, editing_*, аудит времени, мягкое удаление).
- Двойная блокировка: оптимистическая (`version`, 409) + пессимистическая
  (`editing_by_user_id`/`editing_since`, таймаут 30 мин, 423, атомарный захват
  `UPDATE … WHERE … RETURNING`).
- CRUD-контракт: `get_multi`, `get_for_user`, `create_for_user`,
  `acquire_editing_lock`, `release_editing_lock`, `save_with_version`, `mark_deleted`.
- Эндпоинты документного модуля: `GET/POST /`, `GET/PUT/DELETE /{id}`,
  `POST/DELETE /{id}/lock`.
- Фронтенд-паттерн (Правило №39): название-ссылка, иконка замка,
  режим `readOnly` при 423/403, освобождение блокировки при закрытии.

---

### 3. Репликация между доменами (ТЗ v1.1) — ✅ инфраструктура готова

- Таблицы: `core_outbox`, `core_inbox`, `core_sequence_counters`,
  `core_replication_tasks`, `core_replication_progress`, `core_replication_metrics`.
- `Replicator` (фоновый процесс, lifespan): поллинг 2 c, батчи 50, строгий порядок
  по `ordering_key` + `sequence_no`, идемпотентность, экспоненциальные ретраи,
  адвайзорные блокировки, `FOR UPDATE SKIP LOCKED`.
- Реплики хранят полный контракт доступа (5 полей) и проверяются через
  `AccessService` в домене-получателе.
- Реестр обработчиков `register_handler()`; публикация событий — в транзакции
  бизнес-изменения (outbox-паттерн).

---

### 4. Состояние модулей

#### Backend

| Модуль | Статус | Примечания |
|---|---|---|
| `core/auth` | ✅ готов | Только login/logout/user |
| `core/users` | ✅ готов | Публичная регистрация с созданием организации и полной структурой доступа |
| `core/tenants`, `sections`, `roles`, `permissions` | ✅ готовы | |
| `core/doctypes`, `domains` | ✅ готовы | Домены: `prefix`, `is_active`; фильтр doctypes по `domain_id` |
| `core/notes` | ✅ эталон | Серверные сортировка/фильтрация (`NoteSortField`, `SortOrder`, `filter_*`) |
| `core/access` | ✅ готов | См. раздел 3 |
| `core/events` | ✅ готов | См. раздел 5 |
| `business_partners/companies` | ✅ готов | AccessService + блокировки + сервисный слой |
| `inventory/warehouses` | ✅ готов | То же |
| `sales/goods`, `sales/regions` | ✅ готовы | То же |

#### Frontend

| Компонент/страница | Статус | Примечания |
|---|---|---|
| Auth-guard (`AppLayout`, `ProtectedRoute`) | ✅ готов | Render-редирект при 401; `AUTH_USER_QUERY_OPTIONS` (1 запрос на сессию) |
| `LoginPage`, `PublicHomePage` | ✅ готовы | |
| `RegisterPage` (публичная регистрация) | 🚧 в работе | Готово + будет автовход после регистрации |
| `NotesPage` + `EditNoteModal` | ✅ эталон | Пагинация, копирование, меню сортировки/фильтров колонок (серверные), блокировки, readOnly |
| `ColumnHeaderMenu` | ✅ готов | 4 состояния меню (фильтр/сортировка/комбинация) |
| `AdminRolesPage` + `EditRoleModal` | ✅ готовы | Вкладки, черновики, индикаторы изменений, режим копирования |
| `DomainsPage` + `EditDomainModal` | ✅ готовы | Вкладки «Основное» + «Типы документов» (таблица с открытием EditDoctypeModal) |
| `DoctypesPage`, `AdminUsersPage`, `AdminTenantsPage`, `AdminSectionsPage`, `TagsPage` | ✅ готовы | |
| Страницы companies / warehouses / goods / regions | ✅ готовы | |

---

### 5. Тестирование

Комплект: `backend/tests/test_access_control/` — **42 теста, все зелёные**.

- Параметризация по 3 доменам (companies, warehouses, goods).
- Покрытие слоёв ТЗ: тенант, раздел (включая платформенный «Общий»),
  permission, роль без разделов, уровни доступа, `can_delete` (авто при ≥ 2),
  автор удаляет только свои, читатель не создаёт/не изменяет/не удаляет,
  захват блокировки требует уровень ≥ 2.
- Фикстуры идемпотентны (`conftest.py`), документы создаются напрямую в БД
  (`create_document_in_db`) независимо от CRUD.

Команды:

```powershell
cd backend;  pytest tests/test_access_control/ -v --tb=short
cd frontend; npm run api:gen   # после изменений backend-схем
```

---

### 6. Дорожная карта (не реализовано)

| № | Задача | Источник |
|---|---|---|
| 1 | Таблица `user_role_grants` (сроки действия назначений) | ТЗ §10 |
| 2 | Делегирование прав | ТЗ §11 |
| 3 | Аудит настроек доступа и данных (`access_audit_log`, `data_audit_log`) | ТЗ §12 |
| 4 | Подписка на события `LISTEN/NOTIFY` (сейчас поллинг) | ТЗ архитектуры §10.2 |
| 5 | Тег-фильтрация в UI документов (редактирование `or_tags`/`and_tags`) | ТЗ §6 |

---

