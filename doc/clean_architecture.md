## ✅ Правило : "Чистая архитектура в приоритете"

### 🎯 Принципы чистой архитектуры:

1. **ORM-модели с relationship** — связи между сущностями через SQLAlchemy relationship, а не через ручные запросы
2. **@property для вычисляемых полей** — когда нужно извлечь данные из связанной модели (например, `user.tenant_name` из `user.tenant.name`)
3. **Pydantic's `from_attributes=True`** — автоматическая конвертация ORM → Pydantic без ручных словарей
4. **CRUD-паттерн** — вся работа с БД через CRUD-классы, а не прямые запросы в роутерах
5. **Service-слой** — сложная бизнес-логика выносится в сервисы, а не смешивается с роутерами

### 📋 Что это означает на практике:

**❌ Плохо (ручные словари):**
```python
user_dict = {
    "id": user.id,
    "name": user.name,
    "tenant_name": user.tenant.name if user.tenant else None,
    # ... 20 полей вручную
}
return UserResponseSchema.model_validate(user_dict)
```

**✅ Хорошо (чистая архитектура):**
```python
# В модели:
@property
def tenant_name(self) -> str | None:
    return self.tenant.name if self.tenant else None

# В схеме:
class UserResponseSchema(BaseModel):
    tenant_name: Optional[str] = None
    model_config = {"from_attributes": True}

# В роутере:
return UserResponseSchema.model_validate(user)
```

### 🚀 Преимущества:

- **Масштабируемость** — при добавлении новых сущностей не нужно переписывать десятки словарей
- **Поддерживаемость** — логика извлечения данных в одном месте (в модели)
- **Типобезопасность** — IDE подсказывает поля, компилятор ловит ошибки
- **Тестируемость** — легко писать юнит-тесты для моделей и сервисов

