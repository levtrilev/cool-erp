# 📋 Правило №31: Приоритетное использование базового CRUD-класса

Все CRUD-операции **ОБЯЗАТЕЛЬНО** должны реализовываться с применением базового класса `CRUDBase`. Переопределение методов допускается **только** при наличии специфичной бизнес-логики, которую невозможно реализовать через базовый класс.

---

### 1. Обоснование (Почему это важно)

1. **Единообразие кода:** Все CRUD-классы имеют одинаковую структуру, что упрощает навигацию по проекту.
2. **Снижение дублирования:** Базовые операции (get, create, update, remove, get_multi_paginated) реализованы один раз и переиспользуются.
3. **Типобезопасность:** Generic-параметры `CRUDBase[Model, CreateSchema, UpdateSchema]` гарантируют корректность типов на всех уровнях.
4. **Встроенная безопасность:** `get_multi_paginated` автоматически фильтрует по `tenant_id` (Правило №26) и поддерживает поиск.
5. **Обработка ошибок:** Базовый класс централизованно обрабатывает `SQLAlchemyError` с откатом транзакции.

---

### 2. Обязательные требования

#### 2.1. Наследование от `CRUDBase`
Каждый CRUD-класс **ОБЯЗАТЕЛЬНО** должен наследоваться от `CRUDBase` с указанием трёх типов:
```python
class CRUDXxx(CRUDBase[XxxModel, XxxCreateSchema, XxxUpdateSchema]):
```

#### 2.2. Использование базовых методов без переопределения
Если метод базового класса полностью покрывает требования — **НЕ ПЕРЕОПРЕДЕЛЯЙТЕ** его:
- `get(db, id)` — получение по ID
- `create(db, obj_in)` — создание (если нет M2M связей)
- `update(db, db_obj, obj_in)` — обновление (если нет M2M связей)
- `remove(db, id)` — удаление (если нет проверки связанных записей)
- `get_multi_paginated(db, tenant_id, ...)` — список с пагинацией

#### 2.3. Допустимые причины для переопределения
Переопределение метода **ДОПУСКАЕТСЯ** только в следующих случаях:
1. **M2M связи** — требуется синхронизация связанных таблиц (как `tenant_ids` в `DoctypeModel`)
2. **Специфичная фильтрация** — нужна фильтрация через JOIN (например, по M2M таблице)
3. **Поиск по нескольким полям** — базовый метод поддерживает только одно поле
4. **Защита от удаления** — нужно проверить наличие связанных записей перед удалением
5. **Дополнительные проверки** — уникальность, бизнес-правила и т.д.

#### 2.4. Совместимость сигнатур
При переопределении метода **ОБЯЗАТЕЛЬНО** сохранять имена параметров базового класса:
- `obj_in` (не `data`)
- `db_obj` (не `item` или `obj`)
- `user_is_superadmin` (не `is_superadmin`)

---

### 3. Примеры

#### ✅ ПРАВИЛЬНО: Использование базовых методов

```python
class CRUDRole(CRUDBase[RoleModel, RoleCreateSchema, RoleUpdateSchema]):
    """Роли — стандартный CRUD без M2M связей."""
    # ✅ НЕ переопределяем get, create, update, remove, get_multi_paginated
    # Базовый класс полностью покрывает требования
    pass

crud_role = CRUDRole(RoleModel)
```

#### ✅ ПРАВИЛЬНО: Переопределение только при необходимости

```python
class CRUDDoctype(CRUDBase[DoctypeModel, DoctypeCreateSchema, DoctypeUpdateSchema]):
    """Типы документов — требуют синхронизации M2M tenant_ids."""
    
    # ✅ Переопределяем create — нужна синхронизация tenant_ids
    async def create(self, db, obj_in, **kwargs):
        # Специфичная логика для M2M
        ...
    
    # ✅ Переопределяем update — нужна синхронизация tenant_ids
    async def update(self, db, db_obj, obj_in, **kwargs):
        # Специфичная логика для M2M
        ...
    
    # ✅ Переопределяем get_multi_paginated — нужен поиск по двум полям + M2M фильтрация
    async def get_multi_paginated(self, db, tenant_id, **kwargs):
        # Специфичная логика
        ...
    
    # ✅ НЕ переопределяем get и remove — базовая реализация подходит
```

#### ❌ НЕПРАВИЛЬНО: Полное переопределение без необходимости

```python
class CRUDUser(CRUDBase[UserModel, UserCreateSchema, UserUpdateSchema]):
    # ❌ ОШИБКА: Переопределили все методы, хотя базовые подходят
    async def get(self, db, id):
        result = await db.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()  # Точно такой же код, как в базовом классе!
```

---

### 4. Чек-лист для разработчика

При создании нового CRUD-класса проверьте:

- [ ] Класс наследуется от `CRUDBase[Model, CreateSchema, UpdateSchema]`?
- [ ] Использованы ли базовые методы (`get`, `create`, `update`, `remove`, `get_multi_paginated`) без переопределения там, где это возможно?
- [ ] Переопределены ли только те методы, которые требуют специфичной бизнес-логики?
- [ ] Сохранены ли имена параметров базового класса (`obj_in`, `db_obj`, `user_is_superadmin`)?
- [ ] Вызывается ли `super()` в переопределённых методах, если это уместно?
- [ ] Добавлены ли комментарии, объясняющие причину переопределения?

---

## 📄 Полный файл `backend/app/core/doctypes/crud.py`

```python
import uuid
from typing import Optional, Tuple, List

from sqlalchemy import select, delete, insert, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.core.base_crud import CRUDBase
from app.core.doctypes.models import DoctypeModel, doctype_tenants
from app.core.doctypes.schemas import (
    DoctypeCreateSchema,
    DoctypeUpdateSchema,
)


class CRUDDoctype(CRUDBase[DoctypeModel, DoctypeCreateSchema, DoctypeUpdateSchema]):
    """
    CRUD для типов документов.
    
    Специфика (причины переопределения):
    1. create — синхронизация M2M связи tenant_ids (Правило №30)
    2. update — синхронизация M2M связи tenant_ids + проверка уникальности doctype
    3. get_multi_paginated — поиск по двум полям (doctype И doctype_name) + 
       фильтрация через M2M таблицу для обычных пользователей (Правило №26)
    
    НЕ переопределяем:
    - get — базовая реализация подходит
    - remove — базовая реализация подходит (каскадное удаление M2M настроено в модели)
    """

    async def create(
        self,
        db: AsyncSession,
        obj_in: DoctypeCreateSchema,
        tenant_id: Optional[uuid.UUID] = None,
        user_is_superadmin: bool = False,
    ) -> DoctypeModel:
        """
        Создание типа документа с синхронизацией тенантов.
        
        Переопределено, т.к. нужна синхронизация M2M связи tenant_ids.
        """
        if not user_is_superadmin:
            raise HTTPException(status_code=403, detail="Только для суперадмина")

        # Проверка уникальности doctype
        stmt = select(self.model).where(self.model.doctype == obj_in.doctype)
        if (await db.execute(stmt)).scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Тип документа '{obj_in.doctype}' уже существует"
            )

        # Создаём объект без tenant_ids (это не колонка, а M2M связь)
        db_obj = self.model(**obj_in.model_dump(exclude={'tenant_ids'}))
        db.add(db_obj)
        await db.flush()  # Получаем db_obj.id

        # ✅ Синхронизация M2M связи с тенантами
        if obj_in.tenant_ids:
            await db.execute(
                insert(doctype_tenants),
                [{"doctype_id": db_obj.id, "tenant_id": tid} for tid in obj_in.tenant_ids]
            )

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        db_obj: DoctypeModel,
        obj_in: DoctypeUpdateSchema,
        tenant_id: Optional[uuid.UUID] = None,
        user_is_superadmin: bool = False,
    ) -> DoctypeModel:
        """
        Обновление типа документа с синхронизацией тенантов.
        
        Переопределено, т.к. нужна синхронизация M2M связи tenant_ids + 
        проверка уникальности doctype.
        """
        if not user_is_superadmin:
            raise HTTPException(status_code=403, detail="Только для суперадмина")

        item_id = db_obj.id

        # Проверка уникальности при изменении doctype
        update_data = obj_in.model_dump(exclude_unset=True, exclude={'tenant_ids'})
        if "doctype" in update_data and update_data["doctype"] != db_obj.doctype:
            stmt_check = select(self.model).where(
                self.model.doctype == update_data["doctype"]
            )
            if (await db.execute(stmt_check)).scalar_one_or_none():
                raise HTTPException(
                    status_code=400,
                    detail=f"Тип документа '{update_data['doctype']}' уже существует"
                )

        # Обновляем обычные поля
        for key, value in update_data.items():
            setattr(db_obj, key, value)

        # ✅ Полная перезапись M2M связи с тенантами (если передана)
        if obj_in.tenant_ids is not None:
            await db.execute(
                delete(doctype_tenants).where(doctype_tenants.c.doctype_id == item_id)
            )
            if obj_in.tenant_ids:
                await db.execute(
                    insert(doctype_tenants),
                    [{"doctype_id": item_id, "tenant_id": tid} for tid in obj_in.tenant_ids]
                )

        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_multi_paginated(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        search_field: str = "doctype_name",  # Не используется, но сохраняем для совместимости
        user_is_superadmin: bool = False,
    ) -> Tuple[List[DoctypeModel], int]:
        """
        Получение списка типов документов с пагинацией и фильтрацией.
        
        Переопределено, т.к.:
        1. Нужен поиск по двум полям: doctype И doctype_name
        2. Фильтрация по tenant_id идёт через M2M таблицу doctype_tenants
        """
        stmt = select(self.model)
        count_stmt = select(func.count()).select_from(self.model)

        # ✅ Правило №26: Обычные пользователи видят только свои тенанты
        # Фильтрация через M2M таблицу
        if not user_is_superadmin:
            stmt = stmt.join(doctype_tenants).where(
                doctype_tenants.c.tenant_id == tenant_id
            )
            count_stmt = count_stmt.join(doctype_tenants).where(
                doctype_tenants.c.tenant_id == tenant_id
            )

        # ✅ Поиск по двум полям: doctype и doctype_name
        if search:
            search_filter = (
                self.model.doctype.ilike(f"%{search}%")
                | self.model.doctype_name.ilike(f"%{search}%")
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        # Получаем общее количество
        total: int = (await db.execute(count_stmt)).scalar_one()

        # Получаем данные с пагинацией
        stmt = stmt.offset(skip).limit(limit).order_by(self.model.doctype_name)
        items = list((await db.execute(stmt)).scalars().all())

        return items, total


# ✅ Экземпляр CRUD
crud_doctype = CRUDDoctype(DoctypeModel)
```

---

## 📄 Пример использования в роутере

Обратите внимание: для `update` нужно **сначала загрузить объект через `get`**, затем передать его в `update`:

```python
@router.put("/{doctype_id}", response_model=ApiResponse[DoctypeResponseSchema])
async def update_doctype(
    doctype_id: uuid.UUID,
    obj_in: DoctypeUpdateSchema,
    current_session: SuperAdminUser,
    db: DBSession,
):
    # ✅ СНАЧАЛА загружаем объект через базовый метод get
    db_obj = await crud_doctype.get(db, id=doctype_id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Тип документа не найден")
    
    # ✅ ЗАТЕМ передаём его в update
    updated_obj = await crud_doctype.update(
        db,
        db_obj=db_obj,  # ✅ Передаём объект, а не ID
        obj_in=obj_in,
        user_is_superadmin=True,
    )
    
    return ApiResponse(
        success=True,
        message="Обновлен",
        data=DoctypeResponseSchema.model_validate(updated_obj),
    )


@router.delete("/{doctype_id}", response_model=ApiResponse[DoctypeResponseSchema])
async def delete_doctype(
    doctype_id: uuid.UUID,
    current_session: SuperAdminUser,
    db: DBSession,
):
    # ✅ Используем базовый метод remove
    deleted_obj = await crud_doctype.remove(db, id=doctype_id)
    if not deleted_obj:
        raise HTTPException(status_code=404, detail="Тип документа не найден")
    
    return ApiResponse(
        success=True,
        message="Удален",
        data=DoctypeResponseSchema.model_validate(deleted_obj),
    )
```

---

## 📋 Итоговый чек-лист

- [x] Сформулировано Правило №31 о приоритетном использовании `CRUDBase`
- [x] `CRUDDoctype` наследуется от `CRUDBase[DoctypeModel, DoctypeCreateSchema, DoctypeUpdateSchema]`
- [x] Переопределены только методы, требующие специфичной логики: `create`, `update`, `get_multi_paginated`
- [x] НЕ переопределены методы `get` и `remove` — используются из базового класса
- [x] Имена параметров совпадают с базовым классом: `obj_in`, `db_obj`, `user_is_superadmin`
- [x] В роутере `update` сначала загружается объект через `get`, затем передаётся в `update`
- [x] В роутере `delete` используется базовый метод `remove`