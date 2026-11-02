Версионирование API — это то, о чём легко забыть в начале и больно переделывать потом. 

---

## 🎯 Ответ на главный вопрос: нужны ли версии сейчас?

**Нет, вам не нужна сложная система версионирования прямо сейчас.** Но вам нужно **заложить один простой принцип** в структуру, чтобы потом не переделывать всё.

Этот принцип: **версия живёт в префиксе URL, а не в структуре папок.**

---

## 📐 Как это работает на практике

### Текущее состояние (v1)

Сейчас у вас в `main.py`:

```python
app.include_router(auth_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(tenant_router, prefix="/api/v1")
```

Это **уже правильно**. Версия — это просто строка в префиксе. Структура папок доменов (`core/user/`, `inventory/product/`) **не знает** о версиях и **не должна знать**.

### Когда появится v2

Допустим, через год вам нужно изменить `PUT /users/{id}` — добавить обязательное поле `department_id`. Но старые мобильные клиенты ещё используют v1.

**Ключевое правило: дублируйте только то, что изменилось.**

```
backend/app/
├── core/
│   ├── user/
│   │   ├── models.py          # Модель ОДНА для всех версий
│   │   ├── schemas.py         # Схемы v1 И v2 живут тут
│   │   ├── crud.py            # CRUD ОДИН для всех версий
│   │   ├── services.py        # Сервисы ОДНИ для всех версий
│   │   ├── router.py          # Роутер v1 (текущий)
│   │   └── router_v2.py       # 🆕 Роутер v2 (только изменившиеся эндпоинты)
│   │
│   ├── tenant/
│   │   ├── ...
│   │   └── router.py          # v1 — без изменений, v2 его переиспользует
```

### В `main.py`:

```python
# backend/app/main.py

# v1 — все роутеры как есть
from app.core.user.router import router as user_router_v1
from app.core.tenant.router import router as tenant_router_v1

app.include_router(user_router_v1, prefix="/api/v1")
app.include_router(tenant_router_v1, prefix="/api/v1")

# v2 — только изменившиеся роутеры
from app.core.user.router_v2 import router as user_router_v2
# tenant не изменился — переиспользуем v1!
app.include_router(user_router_v2, prefix="/api/v2")
app.include_router(tenant_router_v1, prefix="/api/v2")  # Тот же роутер!
```

Итоговые URL:
- `GET /api/v1/users/` → `user_router_v1`
- `GET /api/v2/users/` → `user_router_v2` (новая логика)
- `GET /api/v1/tenants/` → `tenant_router_v1`
- `GET /api/v2/tenants/` → `tenant_router_v1` (тот же код!)

---

## 📋 Жизненный цикл версий API

### Фаза 1: Разработка (вы сейчас здесь)

```
/api/v1/ — единственная версия
```

- Все роутеры имеют префикс `/api/v1` в `main.py`
- Никаких `router_v2.py` файлов нет
- Вы свободно меняете API, потому что клиентов ещё нет (или они ваши)

**Что заложить сейчас:** просто продолжайте использовать `prefix="/api/v1"` в `main.py`. Больше ничего не нужно.

### Фаза 2: Стабилизация (появились внешние клиенты)

```
/api/v1/ — заморожена, только багфиксы
```

- Вы объявляете v1 "стабильной"
- В v1 добавляете ТОЛЬКО новые эндпоинты, но НЕ меняете существующие
- Не удаляете поля из ответов, не меняете типы данных

### Фаза 3: Эволюция (нужны breaking changes)

```
/api/v1/ — заморожена (deprecated)
/api/v2/ — активная разработка
```

- Создаёте `router_v2.py` ТОЛЬКО для изменившихся эндпоинтов
- Неизменившиеся эндпоинты переиспользуете из v1
- Модели, схемы, CRUD, сервисы — общие для всех версий

### Фаза 4: Устаревание

```
/api/v1/ — deprecated, возвращает заголовок Sunset
/api/v2/ — стабильная
/api/v3/ — активная разработка
```

- В v1 добавляете middleware, который возвращает заголовок:
  ```
  Deprecation: true
  Sunset: Sat, 01 Jan 2027 00:00:00 GMT
  Link: <https://api.coolerp.com/api/v2>; rel="successor-version"
  ```
- Клиенты видят предупреждение и мигрируют на v2

### Фаза 5: Удаление

```
/api/v1/ — удалена
/api/v2/ — стабильная
```

- Удаляете `router.py` (v1) и все специфичные для v1 схемы
- В `main.py` убираете регистрацию v1

---

## 🏗️ Альтернативный подход: версия как отдельный слой

Если вы ожидаете, что версии будут сильно отличаться (например, v2 полностью перерабатывает структуру ответов), можно создать отдельный слой:

```
backend/app/
├── api/
│   ├── v1/
│   │   ├── __init__.py
│   │   ├── router.py          # Агрегатор всех доменов для v1
│   │   ├── user_router.py     # Тонкая обёртка над user/router.py
│   │   └── tenant_router.py
│   └── v2/
│       ├── __init__.py
│       ├── router.py
│       ├── user_router.py     # Новая логика
│       └── tenant_router.py   # Переиспользует v1
│
├── core/                      # Домены НЕ знают о версиях
│   ├── user/
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   └── services.py
│   └── tenant/
│       ├── ...
```

```python
# backend/app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1.user_router import router as user_router
from app.api.v1.tenant_router import router as tenant_router

router = APIRouter()
router.include_router(user_router, prefix="/users", tags=["Users"])
router.include_router(tenant_router, prefix="/tenants", tags=["Tenants"])
```

```python
# backend/app/main.py
from app.api.v1.router import router as api_v1
from app.api.v2.router import router as api_v2

app.include_router(api_v1, prefix="/api/v1")
app.include_router(api_v2, prefix="/api/v2")
```

**Плюсы:** Чёткое разделение, легко увидеть "что изменилось в v2".
**Минусы:** Больше файлов, больше boilerplate.

---

## ✅ Моя рекомендация для вашего проекта

**Сейчас:** Ничего не меняйте. Ваш текущий подход (`prefix="/api/v1"` в `main.py`) — правильный.

**Когда понадобится v2:** Используйте **первый подход** (добавление `router_v2.py` рядом с `router.py` в домене). Он проще и не требует перестройки структуры.

**Никогда не делайте:**
- ❌ Не создавайте папки `v1/`, `v2/` внутри каждого домена — это взорвёт структуру
- ❌ Не дублируйте модели и CRUD между версиями — они общие
- ❌ Не версионируйте через query-параметры (`/users?version=2`) — это антипаттерн
- ❌ Не версионируйте через заголовки (`Accept: application/vnd.v2`) — это усложняет отладку и кэширование

---

## 📝 Единственное, что стоит сделать прямо сейчас

Добавьте в `main.py` комментарий-напоминание для будущего себя:

```python
# backend/app/main.py

# ==========================================
# РЕГИСТРАЦИЯ РОУТЕРОВ
# Версия API задаётся ТОЛЬКО здесь через prefix.
# Домены (core/user, inventory/product и т.д.) 
# НЕ знают о версиях.
# При создании v2: добавить router_v2.py в домене,
# неизменившиеся роутеры переиспользовать из v1.
# ==========================================

app.include_router(auth_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(tenant_router, prefix="/api/v1")
# ... остальные домены
```

Этого достаточно. Когда через год понадобится v2, вы откроете `main.py`, прочитаете комментарий и будете точно знать, что делать. 🎯