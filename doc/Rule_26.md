# Правило №26: Обязательная фильтрация по tenant_id на уровне Backend (КРИТИЧЕСКИ ВАЖНО)

Каждый эндпоинт **ОБЯЗАТЕЛЬНО** должен фильтровать данные по `tenant_id` текущего авторизованного пользователя. Фронтенд **НИКОГДА** не решает, какие данные показывать или изменять. Бэкенд является единственным и абсолютным контролером изоляции данных (Multi-Tenancy).

---

### 1. Обоснование (Почему это критически важно)

В системе Cool ERP несколько организаций (тенантов) работают в одном экземпляре приложения. Если бэкенд не фильтрует данные по `tenant_id`, пользователь из Организации А сможет получить, изменить или удалить данные Организации Б, просто подставив чужой UUID в запросе (горизонтальное повышение привилегий). 

**Золотое правило:** Никогда не доверяйте `tenant_id`, пришедшему в теле запроса (payload) от фронтенда. Берите его **только** из проверенной сессии/JWT-токена.

---

### 2. Обязательные требования к реализации

#### 2.1. Извлечение контекста в Роутере
Роутер (Router) **ОБЯЗАТЕЛЬНО** должен извлекать `tenant_id` и флаг `is_superadmin` из зависимости `get_current_session` (или аналогичной, возвращающей данные текущего пользователя) и передавать их в сервис/CRUD.

#### 2.2. Сигнатура CRUD-методов
Все методы CRUD (чтение, создание, обновление, удаление) **ОБЯЗАТЕЛЬНО** принимают два дополнительных параметра:
* `current_tenant_id: uuid.UUID` — ID организации текущего пользователя.
* `is_superadmin: bool = False` — флаг, позволяющий суперадмину видеть/редактировать данные всех тенантов.

#### 2.3. Фильтрация при чтении (SELECT)
При выборке списка или одной записи **ОБЯЗАТЕЛЬНО** добавляется условие `WHERE tenant_id = :current_tenant_id`. Если `is_superadmin == True`, фильтр опускается.

#### 2.4. Проверка при записи (INSERT / UPDATE / DELETE)
* **При создании:** `tenant_id` для новой записи **ВСЕГДА** берется из `current_tenant_id`, а не из тела запроса.
* **При обновлении/удалении:** Перед изменением записи **ОБЯЗАТЕЛЬНО** проверяется, что она принадлежит `current_tenant_id` (иначе возвращается `403 Forbidden` или `404 Not Found`).

---

### 3. Примеры кода

#### ✅ ПРАВИЛЬНО: Роутер и CRUD (FastAPI + SQLAlchemy 2.0)

**Роутер (`router.py`):**
```python
@router.get("/roles/", response_model=ApiResponse[PaginatedResponse[RoleResponseSchema]])
async def get_roles(
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    # ✅ Извлекаем данные из сессии (JWT)
    current_session: UserSession = Depends(get_current_session), 
    db: AsyncSession = Depends(get_db),
):
    # ✅ Передаем контекст в CRUD
    items, total = await crud_role.get_multi(
        db,
        skip=skip,
        limit=limit,
        search=search,
        current_tenant_id=current_session.tenant_id, # ✅ Только из сессии!
        is_superadmin=current_session.is_superadmin,
    )
    # ... формирование ответа
```

**CRUD (`crud.py`):**
```python
async def get_multi(
    self,
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    current_tenant_id: uuid.UUID | None = None,
    is_superadmin: bool = False,
) -> tuple[list[RoleModel], int]:
    stmt = select(self.model)
    count_stmt = select(func.count()).select_from(self.model)

    # ✅ КРИТИЧЕСКИ ВАЖНО: Применяем фильтр только для обычных пользователей
    if not is_superadmin and current_tenant_id:
        stmt = stmt.where(self.model.tenant_id == current_tenant_id)
        count_stmt = count_stmt.where(self.model.tenant_id == current_tenant_id)

    if search:
        stmt = stmt.where(self.model.name.ilike(f"%{search}%"))
        count_stmt = count_stmt.where(self.model.name.ilike(f"%{search}%"))

    # ... выполнение запроса
```

**Создание записи (`create` в `crud.py`):**
```python
async def create(
    self,
    db: AsyncSession,
    data: RoleCreateSchema,
    current_tenant_id: uuid.UUID, # ✅ Контекст из сессии
    is_superadmin: bool = False,
) -> RoleModel:
    # ✅ Игнорируем tenant_id из data, если он там есть, и подставляем свой
    db_obj = self.model(
        **data.model_dump(exclude={'tenant_id'}), 
        tenant_id=current_tenant_id # ✅ Жесткая привязка к тенанту
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj
```

#### ❌ НЕПРАВИЛЬНО: Опасные антипаттерны

**1. Доверие фронтенду (Дыра в безопасности):**
```python
# ❌ ГРУБОЕ НАРУШЕНИЕ ПРАВИЛА №26
@router.post("/roles/")
async def create_role(data: RoleCreateSchema, db: AsyncSession = Depends(get_db)):
    # ❌ Берем tenant_id из тела запроса! Злоумышленник может подставить чужой UUID.
    role = RoleModel(**data.model_dump()) 
    db.add(role)
```

**2. Отсутствие фильтра при чтении:**
```python
# ❌ ГРУБОЕ НАРУШЕНИЕ ПРАВИЛА №26
async def get_roles(db: AsyncSession):
    # ❌ Вернет ВСЕ роли из ВСЕХ организаций в системе!
    stmt = select(RoleModel) 
    result = await db.execute(stmt)
    return result.scalars().all()
```

**3. Отсутствие проверки при удалении/обновлении:**
```python
# ❌ ГРУБОЕ НАРУШЕНИЕ ПРАВИЛА №26
async def delete_role(db: AsyncSession, item_id: uuid.UUID):
    # ❌ Пользователь из Организации А сможет удалить роль Организации Б, 
    # просто узнав её UUID.
    stmt = delete(RoleModel).where(RoleModel.id == item_id)
    await db.execute(stmt)
```

---

### 4. Обработка Superadmin

Суперадмин (`is_superadmin == True`) имеет право видеть и управлять данными всех тенантов. Однако логика должна быть явной:

```python
# В методе update или delete
async def update(self, db: AsyncSession, item_id: uuid.UUID, data: RoleUpdateSchema, current_tenant_id: uuid.UUID, is_superadmin: bool):
    stmt = select(self.model).where(self.model.id == item_id)
    
    # ✅ Если не суперадмин — добавляем жесткий фильтр по tenant_id
    if not is_superadmin:
        stmt = stmt.where(self.model.tenant_id == current_tenant_id)
        
    result = await db.execute(stmt)
    db_obj = result.scalar_one_or_none()
    
    if not db_obj:
        # ✅ Возвращаем 404, даже если запись существует, но принадлежит другому тенанту.
        # Это предотвращает утечку информации о существовании записей в других организациях.
        raise HTTPException(status_code=404, detail="Запись не найдена")
        
    # ... логика обновления
```

---

### 5. Чек-лист для разработчика

При создании или рефакторинге любого эндпоинта проверьте:

- [ ] **Откуда берется `tenant_id`?** Только из `get_current_session` (или аналога), НИКОГДА из `request.body` / Pydantic схемы.
- [ ] **Передаются ли параметры в CRUD?** `current_tenant_id` и `is_superadmin` явно проброшены из роутера в сервис/CRUD.
- [ ] **Есть ли `WHERE tenant_id = ...`?** Во всех `SELECT` запросах (списки и получение по ID).
- [ ] **Проверяется ли владение при записи?** Перед `UPDATE` или `DELETE` запись ищется с фильтром по `tenant_id`.
- [ ] **Перезаписывается ли `tenant_id` при создании?** В методе `create` поле `tenant_id` жестко задается из контекста сессии.
- [ ] **Корректно ли обрабатывается Superadmin?** Суперадмин bypass'ит фильтр на чтение, но не ломает логику.

Следование этому правилу является **фундаментом безопасности** Cool ERP. Его нарушение приводит к критическим уязвимостям утечки данных между клиентами.