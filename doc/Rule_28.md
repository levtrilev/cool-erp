# Правило №28: Обязательное указание схемы `public` в моделях SQLAlchemy

Все модели SQLAlchemy **ОБЯЗАТЕЛЬНО** должны явно указывать схему базы данных `public` в аргументах таблицы. Это критически важно для корректной работы `relationship`, `ForeignKey` и предотвращения ошибок метаданных ORM в PostgreSQL.

---

### 1. Объявление схемы в `__table_args__`

* Если у таблицы нет дополнительных SQL-ограничений (constraints), используется словарь:
  ```python
  __table_args__ = {"schema": "public"}
  ```

* Если есть constraints (например, `UniqueConstraint`), используется кортеж, где словарь со схемой идет последним:
  ```python
  __table_args__ = (
      UniqueConstraint("tenant_id", "name", name="sections_uc"),
      {"schema": "public"},
  )
  ```

---

### 2. Требования к `ForeignKey`

Все внешние ключи **ДОЛЖНЫ** включать префикс `public.` при указании целевой таблицы:

```python
# ✅ ПРАВИЛЬНО
tenant_id: Mapped[uuid.UUID] = mapped_column(
    ForeignKey("public.tenants.id", ondelete="NO ACTION"), 
    nullable=False
)

# ❌ НЕПРАВИЛЬНО (вызовет NoReferencedTableError при связывании)
tenant_id: Mapped[uuid.UUID] = mapped_column(
    ForeignKey("tenants.id"), 
    nullable=False
)
```

---

### 3. Зачем это нужно

1. **Предотвращение ошибок ORM:** Избежание `NoReferencedTableError` и `NoForeignKeysError`, когда SQLAlchemy не может найти таблицу для `relationship`, если часть моделей зарегистрирована с префиксом `public.`, а часть без него.
2. **Единый стандарт:** Абсолютная консистентность во всех доменах (`core`, `inventory`, `assets`, `cashflow`, `payable`).
3. **Безопасность миграций:** Явное указание схемы гарантирует, что Alembic всегда будет создавать таблицы и связи именно в схеме `public`.

---

###  Размещение в структуре правил
**ЧАСТЬ 6. МОДЕЛИРОВАНИЕ БАЗЫ ДАННЫХ (SQLAlchemy)**