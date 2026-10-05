# Правило №21: Именование Pydantic-схем

Все классы Pydantic-схем (`Base`, `Create`, `Update`, `Response` и т.д.) **ОБЯЗАТЕЛЬНО** должны заканчиваться словом `Schema`.

✅ **Правильно:** `SectionBaseSchema`, `SectionCreateSchema`, `SectionResponseSchema`, `RoleSaveSchema`
❌ **Неправильно:** `SectionBase`, `TenantResponse`, `RoleCreate`, `UserUpdate`

---

### 1. Обоснование (Почему это важно)

1. **Разделение ответственности (DTO vs ORM):** В проекте одновременно используются SQLAlchemy ORM-модели (для работы с БД) и Pydantic-схемы (для валидации и сериализации API). Суффикс `Schema` создает четкую визуальную и смысловую границу между ними.
2. **Избежание коллизий импортов:** В Python нельзя импортировать два класса с одинаковым именем из разных модулей без использования алиасов. Если схема называется `RoleCreate`, а модель `RoleCreate` (гипотетически), возникнет конфликт. Суффиксы `Model` (для SQLAlchemy) и `Schema` (для Pydantic) полностью исключают эту проблему.
3. **Ясность автогенерации (Orval):** При генерации TypeScript-типов на фронтенде разработчик сразу видит, что `RoleResponseSchema` — это контракт API, а не внутренняя бизнес-сущность.
4. **Читаемость сигнатур:** В роутерах и сервисах типы аргументов читаются как естественный язык: `data: RoleCreateSchema`, `item: RoleModel`.

---

### 2. Обязательные требования к именованию

Каждая схема должна состоять из **Названия сущности** + **Назначения** + **Суффикса `Schema`**.

#### 2.1. Стандартный набор суффиксов
* **`BaseSchema`** — базовые поля, от которых наследуются другие схемы.
* **`CreateSchema`** — поля, обязательные/допустимые при создании записи.
* **`UpdateSchema`** — поля для частичного обновления (обычно все поля `Optional`).
* **`ResponseSchema`** — схема ответа от сервера (включает вычисляемые поля, `id`, `created_at` и т.д.).

#### 2.2. Специфичные схемы
Если схема используется для нестандартных операций (агрегация, аутентификация), используется описательный суффикс:
* **`SaveSchema`** — для агрегирующих эндпоинтов (например, `RoleSaveSchema` для сохранения роли вместе с полномочиями).
* **`LoginSchema`** / **`TokenSchema`** — для эндпоинтов аутентификации.

---

### 3. Примеры кода

#### ✅ ПРАВИЛЬНО: Объявление и использование схем

**Файл `backend/app/core/roles/schemas.py`:**
```python
from pydantic import BaseModel, ConfigDict
import uuid

# ✅ Базовая схема
class RoleBaseSchema(BaseModel):
    name: str
    description: str | None = None

# ✅ Схема создания
class RoleCreateSchema(RoleBaseSchema):
    tenant_id: uuid.UUID

# ✅ Схема обновления
class RoleUpdateSchema(BaseModel):
    name: str | None = None
    description: str | None = None

# ✅ Схема ответа
class RoleResponseSchema(RoleBaseSchema):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    tenant_name: str | None = None
```

**Файл `backend/app/core/roles/router.py` (Импорты и использование):**
```python
from app.core.roles.schemas import RoleCreateSchema, RoleResponseSchema, RoleUpdateSchema
from app.core.roles.models import RoleModel  # ✅ Модель имеет суффикс Model

@router.post("/", response_model=ApiResponse[RoleResponseSchema])
async def create_role(
    data: RoleCreateSchema,  # ✅ Явно видно, что это схема валидации
    db: AsyncSession = Depends(get_db)
):
    # Логика создания
    pass
```

#### ❌ НЕПРАВИЛЬНО: Нарушение правила

```python
#  ОШИБКА: Отсутствует суффикс Schema
class RoleCreate(BaseModel): 
    name: str

class RoleResponse(BaseModel):
    id: uuid.UUID
    name: str

# ❌ ОШИБКА: Конфликт имен при импорте, если в models.py тоже есть RoleCreate
from app.core.roles.models import RoleCreate 
from app.core.roles.schemas import RoleCreate # 💥 NameError / переопределение
```

---

### 4. Связь с SQLAlchemy моделями (Правило №1 и №28)

Чтобы избежать путаницы, в проекте принят строгий дуализм суффиксов:

| Слой | Назначение | Суффикс | Пример |
| :--- | :--- | :--- | :--- |
| **База данных (ORM)** | Маппинг на таблицы PostgreSQL | `Model` | `RoleModel`, `UserModel`, `TenantModel` |
| **API (DTO)** | Валидация и сериализация JSON | `Schema` | `RoleCreateSchema`, `UserResponseSchema` |

*Примечание: В редких случаях, если модель используется только внутренне и не имеет сложной логики, допускается называть её просто по имени сущности (например, `Doctype`), но для основных доменных сущностей суффикс `Model` обязателен.*

---

### 5. Чек-лист для разработчика

При создании нового домена или добавлении новых полей проверьте:

- [ ] Все классы, наследующиеся от `pydantic.BaseModel`, имеют суффикс `Schema`?
- [ ] Базовая схема названа `XxxBaseSchema`?
- [ ] Схема ответа названа `XxxResponseSchema` и имеет `model_config = ConfigDict(from_attributes=True)`?
- [ ] В роутерах и сервисах нет "голых" названий вроде `data: RoleCreate`?
- [ ] При импорте в одном файле моделей и схем не возникает конфликтов имен благодаря суффиксам?

Следование этому правилу делает код самодокументируемым. Любой разработчик, открывший файл `router.py` или `services.py`, с первого взгляда понимает, какие объекты идут извне (от клиента), а какие хранятся внутри системы.