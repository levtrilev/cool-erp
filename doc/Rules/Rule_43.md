
## Правило №43: `tenant_id` Permission всегда берётся из связанной роли

**Суть:** Поле `tenant_id` у `PermissionModel` **всегда** устанавливается из `role.tenant_id`, а не из `current_tenant_id` сессии пользователя. Это гарантирует, что permission всегда принадлежит той же организации, что и его роль, независимо от того, кто выполняет операцию (суперадмин или админ организации).

**Область применения:** все операции создания и обновления Permission — через CRUD-методы и через `role_service.save_role`.

---

### Строгие требования

#### 1. В `permissions/crud.py` метод `create_permission`

```python
async def create_permission(self, db, obj_in, current_tenant_id, is_superadmin=False):
    # ✅ ШАГ 1: Загружаем роль для получения её tenant_id
    role = await db.execute(select(RoleModel).where(RoleModel.id == obj_in.role_id))
    role = role.scalar_one_or_none()
    
    # ✅ ШАГ 2: Проверка прав доступа к роли (не к permission!)
    if not is_superadmin and role.tenant_id != current_tenant_id:
        raise HTTPException(status_code=403, detail="Нет доступа к роли другой организации")
    
    # ✅ ШАГ 3: tenant_id берётся ИЗ РОЛИ, а не из current_tenant_id
    target_tenant_id: uuid.UUID = role.tenant_id
    
    # ✅ ШАГ 4: Исключаем tenant_id из входящих данных, чтобы не было конфликта
    data_dict = obj_in.model_dump(exclude={"tenant_id"})
    db_obj = PermissionModel(**data_dict, tenant_id=target_tenant_id)
    
    db.add(db_obj)
    await db.flush()
    return db_obj
```

#### 2. В `role_service.save_role` при синхронизации permissions

```python
# ✅ КРИТИЧНО: tenant_id берётся из РОЛИ, а не из сессии
target_tenant_id: uuid.UUID = role.tenant_id

for perm_data in data.permissions:
    perm_dict = perm_data.model_dump(exclude={"id", "tenant_id"})
    perm_dict["role_id"] = role.id
    perm_dict["role_name"] = role.name
    # ❌ НЕ добавлять: perm_dict["tenant_id"] = current_tenant_id
    # ✅ Вместо этого: tenant_id добавляется внутри create_permission из role.tenant_id
    
    safe_perm_data = PermissionCreateSchema(
        **perm_dict, 
        tenant_id=target_tenant_id,  # ← tenant_id роли
    )
    
    new_perm = await crud_permission.create_permission(
        db,
        obj_in=safe_perm_data,
        current_tenant_id=target_tenant_id,  # ← tenant_id роли
        is_superadmin=is_superadmin,
    )
```

---

### ✅ ПРАВИЛЬНО

```python
# При создании permission суперадмином для роли организации A:
# - user.tenant_id = UUID_суперадмина
# - role.tenant_id = UUID_организации_A  ← используем это
# - permission.tenant_id = UUID_организации_A  ✅

role = await crud_role.get(db, item_id=role_id, ...)
target_tenant_id = role.tenant_id  # ✅ Берём из роли

permission = await crud_permission.create_permission(
    db,
    obj_in=PermissionCreateSchema(..., tenant_id=target_tenant_id),
    current_tenant_id=target_tenant_id,
    is_superadmin=is_superadmin,
)
```

### ❌ НЕПРАВИЛЬНО

```python
# ❌ ОШИБКА: tenant_id берётся из сессии пользователя
permission = await crud_permission.create_permission(
    db,
    obj_in=PermissionCreateSchema(..., tenant_id=current_tenant_id),
    current_tenant_id=current_tenant_id,  # ❌ Сессия суперадмина
    is_superadmin=is_superadmin,
)
# Результат: permission создан с tenant_id суперадмина,
# но пользователь организации A его не увидит,
# потому что в AccessService проверка perm.tenant_id == user.tenant_id не пройдёт
```

---

### Обоснование

#### Почему tenant_id из роли, а не из сессии?

| Аспект | tenant_id из сессии | tenant_id из роли |
|--------|---------------------|-------------------|
| **Суперадмин создаёт permission** | `tenant_id = tenant_id_суперадмина` → permission не виден целевой организации | `tenant_id = tenant_id_роли` → permission работает для целевой организации ✅ |
| **Админ создаёт permission** | Работает (совпадает с tenant_id роли) | Работает (совпадает с tenant_id роли) ✅ |
| **Семантическая корректность** | ❌ Permission "принадлежит" пользователю | ✅ Permission "принадлежит" роли и её организации |
| **В AccessService** | Проверка `perm.tenant_id == user.tenant_id` не проходит для целевой организации | ✅ Проверка проходит ✅ |

#### Почему это архитектурный принцип

`PermissionModel` — это **атрибут роли**, а не самостоятельная сущность. Он логически принадлежит роли и должен наследовать её организацию. Попытка присвоить permission'у tenant_id, отличный от tenant_id роли, создаёт семантическую ошибку — permission оказывается "оторванным" от своей роли.

---

### Чек-лист применения

- [ ] В `create_permission` загружается роль для получения `tenant_id`
- [ ] `tenant_id` permission устанавливается из `role.tenant_id`
- [ ] `tenant_id` из входящих данных исключается (`exclude={"tenant_id"}`)
- [ ] Проверка прав выполняется по tenant_id **роли**, а не permission
- [ ] В `role_service.save_role` используется `target_tenant_id = role.tenant_id`
- [ ] Параметр `current_tenant_id` в вызовах CRUD = `role.tenant_id`, а не `session.tenant_id`

---

### Связь с другими правилами

| Правило | Связь |
|---------|-------|
| Backend №26 (Multi-tenancy) | Фильтрация permission по tenant_id роли, а не сессии |
| Backend №31 (Приоритет CRUDBase) | Метод `create_permission` — уникальное имя, не переопределяет базовый |
| Backend №40 (Блокировки) | Аналогичный принцип: проверки прав используют tenant_id документа |
| AccessService (ШАГ 3) | Проверка `perm.tenant_id == user.tenant_id` корректно работает |

---
