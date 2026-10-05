# Правило №10: Импорт типов и функций из Orval

При работе с API-клиентами, сгенерированными Orval, **ОБЯЗАТЕЛЬНО** соблюдать строгое разделение импортов:
* **Функции** (API-вызовы, хуки, мутации) — импортируются из `@/api/generated/<domain>/<domain>`
* **Типы** (Pydantic-схемы, DTO) — импортируются из `@/api/generated/fastAPI.schemas`

Смешивание импортов или использование альтернативных путей **КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО**.

---

### 1. Обоснование (Почему это важно)

1. **Структура Orval:** Orval генерирует два типа файлов:
   * **Файлы доменов** (`@/api/generated/roles/roles.ts`) — содержат React Query хуки (`useReadRolesRolesGet`), мутации (`useCreateRoleRolesPost`) и прямые функции (`readRolesRolesGet`).
   * **Единый файл схем** (`@/api/generated/fastAPI.schemas.ts`) — содержит все TypeScript-интерфейсы (`RoleResponseSchema`, `RoleCreateSchema` и т.д.), сгенерированные из Pydantic-схем бэкенда.
2. **Типобезопасность:** Если тип импортируется из неправильного места, TypeScript может не распознать его, что приведет к ошибкам компиляции или потере автодополнения в IDE.
3. **Единообразие кода:** Когда все разработчики импортируют одинаково, код становится предсказуемым. Не нужно гадать, откуда взят тип `RoleResponseSchema` — он всегда в `fastAPI.schemas`.
4. **Автоматизация:** Orval при перегенерации может изменить структуру файлов доменов (например, разбить один файл на несколько), но файл `fastAPI.schemas.ts` остается стабильным. Привязка к нему гарантирует, что импорты не сломаются при обновлении.

---

### 2. Обязательные требования к реализации

#### 2.1. Импорт функций (API-вызовы)
Все React Query хуки и прямые функции API **ОБЯЗАТЕЛЬНО** импортируются из файла соответствующего домена:
```typescript
import { 
  useReadRolesRolesGet,      // Хук для чтения списка
  useCreateRoleRolesPost,    // Хук для создания
  useDeleteRoleRolesRoleIdDelete, // Хук для удаления
  readRolesRolesGet          // Прямая функция (для колбэков)
} from "@/api/generated/roles/roles";
```

#### 2.2. Импорт типов (Схемы)
Все TypeScript-интерфейсы, соответствующие Pydantic-схемам бэкенда, **ОБЯЗАТЕЛЬНО** импортируются из единого файла схем:
```typescript
import type { 
  RoleResponseSchema,
  RoleCreateSchema,
  RoleUpdateSchema,
  RoleSaveSchema,
  PermissionResponseSchema
} from "@/api/generated/fastAPI.schemas";
```

#### 2.3. Использование `import type`
Для импорта **только типов** (без значений) **ОБЯЗАТЕЛЬНО** использовать конструкцию `import type`. Это позволяет TypeScript удалить эти импорты при компиляции, уменьшая размер бандла:
```typescript
import type { RoleResponseSchema } from "@/api/generated/fastAPI.schemas";
```

---

### 3. Примеры кода

#### ✅ ПРАВИЛЬНО: Разделение импортов

```tsx
// ✅ ПРАВИЛЬНО: Функции из домена, типы из схем
import { useReadRolesRolesGet, useCreateRoleRolesPost } from "@/api/generated/roles/roles";
import type { RoleResponseSchema, RoleCreateSchema } from "@/api/generated/fastAPI.schemas";

export const RolesPage = () => {
  // ✅ Используем хук из домена
  const { data, isLoading } = useReadRolesRolesGet({ skip: 0, limit: 10 });
  
  // ✅ Типизируем переменную схемой из fastAPI.schemas
  const roles: RoleResponseSchema[] = data?.data?.items || [];
  
  // ✅ Типизируем состояние формы
  const [formData, setFormData] = useState<RoleCreateSchema>({
    name: "",
    description: "",
    tenant_id: "",
  });

  return (
    <div>
      {/* ... */}
    </div>
  );
};
```

#### ✅ ПРАВИЛЬНО: Использование прямой функции в колбэке

```tsx
import { readRolesRolesGet } from "@/api/generated/roles/roles"; // ✅ Прямая функция
import type { RoleResponseSchema } from "@/api/generated/fastAPI.schemas";

const handleRoleSaved = async (id: string) => {
  // ✅ Используем прямую функцию для поиска в полном списке
  const fullListRes = await readRolesRolesGet({ limit: 1000, skip: 0 });
  const allItems: RoleResponseSchema[] = fullListRes.data?.items || [];
  
  const foundIndex = allItems.findIndex((item) => item.id === id);
  // ...
};
```

#### ❌ НЕПРАВИЛЬНО: Импорт типов из домена

```tsx
// ❌ ОШИБКА: Типы НЕ должны импортироваться из файла домена
import { 
  useReadRolesRolesGet,
  RoleResponseSchema // ❌ Это тип, он должен быть в fastAPI.schemas!
} from "@/api/generated/roles/roles";
```
*Почему это плохо:* Orval не экспортирует типы из файлов доменов. Этот импорт вызовет ошибку компиляции TypeScript: `Module has no exported member 'RoleResponseSchema'`.

#### ❌ НЕПРАВИЛЬНО: Импорт функций из схем

```tsx
// ❌ ОШИБКА: Функции НЕ должны импортироваться из файла схем
import { 
  useReadRolesRolesGet, // ❌ Это функция, она должна быть в roles/roles!
  RoleResponseSchema
} from "@/api/generated/fastAPI.schemas";
```
*Почему это плохо:* Файл `fastAPI.schemas.ts` содержит только интерфейсы типов. Попытка импортировать оттуда функцию вызовет ошибку: `Module has no exported member 'useReadRolesRolesGet'`.

#### ❌ НЕПРАВИЛЬНО: Использование обычного `import` для типов

```tsx
// ❌ ОШИБКА: Отсутствие `type` в импорте
import { RoleResponseSchema } from "@/api/generated/fastAPI.schemas";
```
*Почему это плохо:* Хотя TypeScript всё равно поймет, что это тип, использование `import type` явно указывает намерение и позволяет сборщику (Vite/Webpack) удалить этот импорт из финального бандла, так как типы не существуют в runtime.

#### ❌ НЕПРАВИЛЬНО: Ручное описание типов

```tsx
// ❌ ОШИБКА: Дублирование типов, которые уже есть в Orval
interface RoleResponseSchema {
  id: string;
  name: string;
  description: string | null;
}
```
*Почему это плохо:* При изменении схемы на бэкенде (например, добавлении поля `tenant_name`) придется вручную обновлять этот интерфейс в каждом файле, где он используется. Orval-схемы обновляются автоматически при перегенерации.

---

### 4. Нюансы и лучшие практики

#### 4.1. Перегенерация Orval
После любого изменения Pydantic-схем на бэкенде **ОБЯЗАТЕЛЬНО** перегенерировать клиенты:
```bash
cd frontend
npm run orval
```
Это обновит файл `fastAPI.schemas.ts` и файлы доменов, синхронизируя их с актуальным состоянием бэкенда.

#### 4.2. Именование файлов доменов
Orval генерирует файлы доменов по имени роутера в `main.py`. Если роутер зарегистрирован как:
```python
app.include_router(roles_router, prefix="/api/v1/roles", tags=["Roles"])
```
То файл будет называться `roles/roles.ts`. Важно сохранять консистентность между именем домена на бэкенде и на фронтенде.

#### 4.3. Группировка импортов
Для улучшения читаемости **рекомендуется** группировать импорты по источникам:
```tsx
// 1. React и сторонние библиотеки
import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

// 2. Orval: функции из доменов
import { useReadRolesRolesGet, useCreateRoleRolesPost } from "@/api/generated/roles/roles";

// 3. Orval: типы из схем
import type { RoleResponseSchema, RoleCreateSchema } from "@/api/generated/fastAPI.schemas";

// 4. Компоненты UI
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table";

// 5. Локальные компоненты и утилиты
import { EditRoleModal } from "./EditRoleModal";
```

#### 4.4. Автоимпорт в IDE
VS Code и другие IDE могут предлагать автоимпорт из неправильных мест (например, из `node_modules` или старых файлов). **Всегда проверяйте**, что путь импорта соответствует Правилу №10. Если IDE предлагает импорт из `@/api/generated/roles/roles` для типа — это ошибка автодополнения.

#### 4.5. Связь с Правилом №21 (Именование Pydantic-схем)
На бэкенде все схемы заканчиваются на `Schema` (например, `RoleResponseSchema`). Orval сохраняет это имя при генерации TypeScript-интерфейсов. Поэтому на фронтенде типы тоже будут называться `RoleResponseSchema`, `RoleCreateSchema` и т.д. Это обеспечивает полную консистентность между бэкендом и фронтендом.

#### 4.6. Обработка вложенных типов
Если схема содержит вложенные объекты (например, `RoleResponseSchema` содержит массив `PermissionResponseSchema`), Orval сгенерирует оба типа в `fastAPI.schemas.ts`. Импортировать нужно оба:
```tsx
import type { 
  RoleResponseSchema,
  PermissionResponseSchema // ✅ Вложенный тип тоже из fastAPI.schemas
} from "@/api/generated/fastAPI.schemas";
```

---

### 5. Чек-лист для разработчика

При добавлении импортов Orval в любой компонент проверьте:

- [ ] Все React Query хуки (`useRead...`, `useCreate...`, `useUpdate...`, `useDelete...`) импортируются из `@/api/generated/<domain>/<domain>`?
- [ ] Все прямые функции API (`read...`, `create...`) импортируются из `@/api/generated/<domain>/<domain>`?
- [ ] Все TypeScript-интерфейсы (`...ResponseSchema`, `...CreateSchema`) импортируются из `@/api/generated/fastAPI.schemas`?
- [ ] Используется ли `import type` для импорта только типов?
- [ ] Отсутствуют ли ручные дубликаты типов, которые уже есть в Orval?
- [ ] Перегенерирован ли Orval после изменений на бэкенде (`npm run orval`)?
- [ ] Сгруппированы ли импорты по источникам (React, Orval-функции, Orval-типы, UI, локальные)?

Следование этому правилу гарантирует, что фронтенд Cool ERP будет полностью типобезопасным, синхронизированным с бэкендом и легко поддерживаемым. Любой разработчик, открывший файл, мгновенно поймет, откуда взяты функции и типы, что ускоряет онбординг и рефакторинг.