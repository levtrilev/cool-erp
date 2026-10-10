# Cool ERP

[![GitHub license](https://img.shields.io/github/license/levtrilev/cool-erp)](LICENSE)
<!-- [![GitHub stars](https://img.shields.io/github/stars/levtrilev/cool-erp)](https://github.com/levtrilev/cool-erp/stargazers) -->

**Cool ERP** (https://coolerp.ru) — это модульная, легко расширяемая ERP-система с открытым кодом, специально адаптированная для надежной ИИ-генерации новых функций. Монорепозиторий FastAPI/Orval + Vite/React/TailwindCSS/TanStackQuery.

🌐 **Официальный сайт проекта:** [coolerp.ru](https://coolerp.ru) (under construction)

Для старта разработки собственной ERP-системы с чистого листа на базе шаблона под лицензией MIT (которая позволяет свободно модифицировать, коммерциализировать и закрывать исходный код) классические ERP-гиганты вроде Odoo (LGPL/коммерческая) или ERPNext (GPL) не подойдут из-за инфекционного характера их лицензий, требующих открывать ваш код.
**Cool ERP** попадает в один ряд с лучшими готовыми Open Source шаблонами, каркасы (boilerplates) и платформами с лицензией MIT для разработки своей ERP

## Ближайшие аналоги:
* 1. FastAPI React Starter by raythurman2386:
https://github.com/raythurman2386/fastapi-react-starter

* 2. Full-Stack FastAPI Template (by Tiangolo):
https://github.com/fastapi/full-stack-fastapi-template
---

## 🚀 Основные возможности (under construction)

* **Управление складом:** учет остатков, перемещения, инвентаризация.
* **CRM-модуль:** ведение базы клиентов, история взаимодействия, воронка продаж.
* **Финансы:** контроль доходов и расходов, аналитические отчеты.
* **Интеграции:** поддержка сторонних сервисов по API.

---

## 🛠️ Стек технологий

* **Backend:** FastAPI + SQLAlchemy 2.0 async + Pydantic v2
* **Frontend:** React + TS + Vite + Tailwind + shadcn/ui + RHF + Zod + React Query (TanStack) + Orval
* **База данных:** PostgreSQL

---

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

## 🗺️ Дорожная карта (Roadmap) (under construction)

- [x] Разработка базового модуля CRM
- [x] Интеграция с базой данных
- [ ] Запуск складского модуля (в процессе)
- [ ] Мобильное приложение

---

## 🤝 Участие в разработке (Contributing)

Мы рады любому вкладу в развитие проекта! Чтобы внести изменения:
1. Сделайте форк репозитория.
2. Создайте ветку для вашей фичи (`git checkout -b feature/AmazingFeature`).
3. Закоммитьте изменения (`git commit -m 'Add some AmazingFeature'`).
4. Отправьте ветку в origin (`git push origin feature/AmazingFeature`).
5. Откройте Pull Request.

---

## 📄 Лицензия

Этот проект распространяется под лицензией **MIT**. Подробности в файле [LICENSE](LICENSE).

---

## 📞 Контакты

* **Email:** levtrishankov@yandex.ru
* **Telegram:** [@coolerp_community](https://t.me/coolerp) (under construction)

## 🚀 Почему этот проект крутой для контрибьюторов

### 💎 Технический стек мечты

**Backend:**
- **FastAPI** — самый быстрый Python-фреймворк с автоматической документацией
- **SQLAlchemy 2.0** (async) — современный ORM с полной поддержкой async/await
- **Pydantic v2** — валидация данных на стероидах
- **PostgreSQL** — надёжная БД для enterprise-решений

**Frontend:**
- **React 18 + TypeScript** — типобезопасность на всех уровнях
- **Vite** — мгновенная горячая перезагрузка
- **Tailwind CSS + shadcn/ui** — красивейший UI без боли
- **Orval** — забудь про ручное написание API-клиентов (генерируется из OpenAPI!)

### 🏗️ Архитектура, которой можно гордиться

✅ **Модульный монолит** — каждый домен (`auth`, `tenant`, `user`) в отдельной папке  
✅ **Чистая структура** — `models.py`, `schemas.py`, `crud.py`, `router.py` в каждом модуле  
✅ **Разделение ответственности** — CRUD для работы с БД, Services для бизнес-логики  
✅ **Типобезопасность end-to-end** — от Pydantic-схем до TypeScript-интерфейсов  
✅ **Автоматическая генерация API** — Orval создаёт хуки React Query из OpenAPI  

## 📊 Кратко резюмируем, что у нас работает сейчас (07.10.2026):

## 🏗️ Backend (FastAPI + SQLAlchemy 2.0 + PostgreSQL)

### Домен `core` (Безопасность и RBAC)

**Модели БД:**
- ✅ `TenantModel` — организации (tenants)
- ✅ `UserModel` — пользователи с полями `role_ids`, `role_names`, `is_superadmin`
- ✅ `SectionModel` — разделы внутри тенанта
- ✅ `RoleModel` — роли с массивами `section_ids`, `section_names`
- ✅ `PermissionModel` — полномочия (doctype, full_access, editor, author, reader, can_delete, теги)
- ✅ `UserSession` — сессии для JWT-аутентификации

**CRUD-слой:**
- ✅ Полный CRUD для всех сущностей (`create`, `get`, `get_multi`, `update`, `delete`)
- ✅ Жесткая фильтрация по `tenant_id` на уровне CRUD (Правило №26)
- ✅ Метод `delete_by_role_id` для массового удаления полномочий

**Сервисный слой:**
- ✅ `RoleService.save_role()` — атомарное сохранение роли + полномочий + пользователей в одной транзакции
- ✅ Автоматическая синхронизация `role_names` в `UserModel` при изменении ролей

**Роутеры:**
- ✅ `POST /api/v1/auth/login`, `/logout`, `/me` — аутентификация
- ✅ `GET/POST/PUT/DELETE /api/v1/tenants/` — управление организациями
- ✅ `GET/POST/PUT/DELETE /api/v1/users/` — управление пользователями
- ✅ `GET/POST/PUT/DELETE /api/v1/sections/` — управление разделами
- ✅ `GET/POST/PUT/DELETE /api/v1/roles/` — управление ролями
- ✅ `GET/POST/PUT/DELETE /api/v1/permissions/` — управление полномочиями
- ✅ `POST /api/v1/roles/save` — агрегированное сохранение роли

**Схемы Pydantic:**
- ✅ `ApiResponse[T]`, `PaginatedResponse[T]` — универсальные обёртки
- ✅ Все схемы с суффиксом `Schema` (Правило №21)
- ✅ `RoleSaveSchema` для агрегированного сохранения

---

## 🎨 Frontend (React 19 + TypeScript + Vite + shadcn/ui)

### Инфраструктура
- ✅ Настроен **Orval** для автогенерации типобезопасных API-клиентов из OpenAPI
- ✅ Настроен **CORS** в `main.py` для связи с Vite (порт 5173)
- ✅ Создан переиспользуемый компонент **`ReferenceSelect`** с серверной пагинацией и поиском (Правило №27)

### Домен `core` (UI)

**Страницы:**
- ✅ `RolesPage.tsx` — список ролей с:
  - Компактными отступами (Правило №11)
  - Умным поиском по Enter (Правило №12)
  - Подсветкой строки после обновления (Правило №17)
  - Умными toast-уведомлениями с навигацией (Правило №18)
  - Пагинацией с номерами страниц (Правило №15)
  - Удалением через `AlertDialog` (Правило №16)

**Модальные окна:**
- ✅ `EditRoleModal.tsx` — расширенный экран редактирования роли с 4 вкладками:
  - **Основное**: название, описание
  - **Разделы**: таблица с чекбоксами для выбора разделов
  - **Полномочия**: матрица прав (full_access, editor, author, reader, can_delete) по типам документов
  - **Пользователи**: таблица с чекбоксами для назначения ролей
- ✅ Фиксированный размер модалки (800px) без "прыжков" при переключении вкладок
- ✅ Прокрутка внутри таблиц при большом количестве записей
- ✅ Строгое соблюдение порядка: `invalidateQueries` → `onOpenChange(false)` → `await onRoleSaved(...)` (Правило №24)

**Компоненты:**
- ✅ `ReferenceSelect.tsx` — универсальный справочник с серверным поиском, пагинацией, клавиатурной навигацией

---

## 📋 Правила проекта

- ✅ Сформулировано и актуализировано **35 правил** проекта (см. docs), позволяющие получать предсказуемые результаты при использовании AI

---

## 🚧 Что ещё предстоит сделать

### Backend
- [ ] Домены предметной области: `inventory`, `assets`, `cashflow`, `payable`
- [ ] Сервис проверки полномочий (`permission_checker.py`) для фильтрации документов по статусам (draft/active/deleted)
- [ ] Эндпоинт `GET /api/v1/doctypes` — справочник типов документов
- [ ] Миграции Alembic для всех таблиц

### Frontend
- [ ] Страницы для доменов предметной области (`InventoryPage`, `AssetsPage`, etc.)
- [ ] Интеграция `ReferenceSelect` во все формы справочников
- [ ] Реализация статусной модели документов (draft → active → deleted)
- [ ] UI для делегирования авторства и утверждения документов

### Инфраструктура
- [ ] Настройка CI/CD
- [ ] Тесты (pytest для backend, Vitest для frontend)
- [ ] Docker-compose для локального развёртывания

---

## 🎯 Текущий статус

Проект находится на этапе **завершения базовой инфраструктуры безопасности и RBAC**. Готов фундамент для разработки предметных доменов:
- ✅ Multi-tenancy с изоляцией данных на уровне БД
- ✅ Гибкая ролевая модель с матрицей полномочий
- ✅ Типобезопасный API-клиент через Orval
- ✅ Единый стиль кода и архитектуры
