## Правило №46: Архитектура сложных форм с множественными источниками данных

### Суть

Сложные формы (модальные окна с вкладками, таблицами, справочниками и черновиками) строятся на строгом разделении трёх типов состояния: **серверного** (React Query), **формы** (React Hook Form) и **локальных черновиков** (`useState` с метаданными). Реактивность обеспечивается через производные значения (`useMemo`, `useWatch`), а не через каскады `setState` в `useEffect`. Каждое пользовательское действие вызывает ровно один ререндер.

Правило является обобщением опыта разработки `EditRoleModal` и обязательно для всех форм, где присутствуют:
- Более одного типа связанных данных (например, роль + разделы + полномочия + пользователи)
- Вкладки с отдельными черновиками
- Индикаторы несохранённых изменений
- Режимы создания/редактирования/копирования

### Строгие требования

#### 1. Разделение состояния

**1.1.** Серверные данные загружаются только через Orval-хуки (`useGetXxx`, `useReadXxx`). Запрещено хранить их в `useState`.

**1.2.** Поля формы управляются только через RHF (`useForm`, `<Controller>`, `useWatch`). Запрещено дублировать значения полей в отдельные `useState`.

**1.3.** Черновики с метаданными (массивы объектов с `markedForDeletion`, `id: undefined` для новых) хранятся в `useState`, но инициализируются только после завершения загрузки данных.

**1.4.** Каждый тип данных имеет ровно один источник истины. Запрещено хранить одно и то же значение в двух местах (например, `section_ids` в форме и в отдельном `useState`).

#### 2. Производные значения

**2.1.** Все вычисляемые значения (индикаторы изменений, фильтрованные списки, подсчёты) реализуются через `useMemo`.

**2.2.** Запрещено использовать `useState` + `useEffect` для значений, которые можно вычислить из существующих данных.

**2.3.** Зависимости `useMemo` должны быть стабильными ссылками:
- Примитивы (`string`, `number`, `boolean`)
- Результаты других `useMemo`
- Значения из `useWatch` (с `defaultValue`)
- Запрещено: функции без `useCallback`, результаты `.filter()`/`.map()` без `useMemo`, `?? []` / `?? {}`

#### 3. Реактивный доступ к полям формы

**3.1.** Для чтения значений полей в рендере используется `useWatch` с `defaultValue`.

**3.2.** Запрещено использовать `watch()` (метод) в зависимостях `useMemo` или в рендере.

**3.3.** Для записи в форму используется `field.onChange` из `<Controller>`.

**3.4.** Запрещено создавать производные значения через `watch("field") ?? []` — это создаёт новый массив на каждом рендере и ломает стабильность зависимостей.

#### 4. Инициализация черновиков

**4.1.** `useState` черновика начинается с пустого массива.

**4.2.** Инициализация из данных происходит в `useEffect` с обязательной проверкой `!isLoading && data`.

**4.3.** Защита от повторной инициализации через `useRef` с идентификатором сущности.

**4.4.** Сброс черновика при закрытии: `setState([])` + `ref.current = null`.

**4.5.** Синхронизация черновика при открытии выполняется в обработчике события (`handleOpenChange`), а не в `useEffect`.

#### 5. Источник истины после сохранения

**5.1.** Ответ мутации сохраняется как `savedOverride` и имеет приоритет над пропом из родителя.

**5.2.** Все индикаторы изменений сравнивают с `effectiveEntity = savedOverride ?? prop ?? null`.

**5.3.** Черновики синхронизируются с ответом сервера после сохранения.

**5.4.** `savedOverride` сбрасывается при открытии новой сущности и при закрытии модалки.

#### 6. Гарантированный перемонт

**6.1.** При открытии модалки увеличивается `sessionKey`.

**6.2.** `key` на корневом элементе модалки включает `sessionKey`.

**6.3.** При закрытии сбрасываются: форма (`reset`), черновики, `savedOverride`, ref-флаги.

#### 7. Индикаторы изменений

**7.1.** Для простых полей (название, описание): сравнение `useWatch` значения с `effectiveEntity?.field`.

**7.2.** Для массивов (разделы): сравнение отсортированных массивов через `JSON.stringify`.

**7.3.** Для черновиков (полномочия, пользователи): сравнение с снапшотом через `JSON.stringify`.

**7.4.** Агрегированный индикатор `hasAnyChanges` объединяет все индикаторы через `||`.

**7.5.** Индикаторы отображаются на вкладках в виде `*` (жёлтый символ в правом верхнем углу триггера).

#### 8. Строгий порядок действий при сохранении

**8.1.** Инвалидация кэшей (`invalidateQueries`) — обновить данные.

**8.2.** Синхронизация черновиков с ответом сервера.

**8.3.** Обновление `savedOverride`.

**8.4.** Закрытие модалки (`onOpenChange(false)`) — только если это режим копирования или создания.

**8.5.** Сброс формы (`reset(CREATE_DEFAULTS)`) — выполняется в `handleOpenChange` при закрытии.

**8.6.** Вызов `onSaved(id, name)` для подсветки в родительском списке.

### ✅ ПРАВИЛЬНО

#### Пример 1: Разделение состояния и реактивные значения

```tsx
import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import { useForm, Controller, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

const roleSchema = z.object({
  name: z.string().min(1, "Название обязательно"),
  description: z.string().optional(),
  section_ids: z.array(z.string()).optional(),
});

type RoleFormData = z.infer<typeof roleSchema>;

const CREATE_DEFAULTS: RoleFormData = {
  name: "",
  description: "",
  section_ids: [],
};

export function EditRoleModal({ open, onOpenChange, role, onRoleSaved }) {
  const { control, handleSubmit, reset } = useForm<RoleFormData>({
    resolver: zodResolver(roleSchema),
    defaultValues: CREATE_DEFAULTS,
  });

  // ✅ Паттерн: ключ для гарантированного перемонта
  const [sessionKey, setSessionKey] = useState(0);

  // ✅ Паттерн: источник истины после сохранения
  const [savedRoleOverride, setSavedRoleOverride] = useState(null);
  const effectiveRole = savedRoleOverride ?? role ?? null;

  // ✅ Реактивное чтение через useWatch (не watch!)
  const sectionIds = useWatch({
    control,
    name: "section_ids",
    defaultValue: [],  // ✅ Гарантия типа (не undefined)
  });

  // ✅ Реактивное чтение названия для индикатора изменений
  const watchedName = useWatch({
    control,
    name: "name",
    defaultValue: "",
  });

  // ✅ Индикатор изменений через useMemo со стабильными зависимостями
  const hasSectionChanges = useMemo(() => {
    const initial = (effectiveRole?.section_ids || []).slice().sort();
    const current = sectionIds.slice().sort();
    return JSON.stringify(initial) !== JSON.stringify(current);
  }, [effectiveRole?.section_ids, sectionIds]);

  // ✅ Индикатор для простых полей
  const hasNameChanges = useMemo(() => {
    return (watchedName || "") !== (effectiveRole?.name || "");
  }, [watchedName, effectiveRole?.name]);

  // ✅ Агрегированный индикатор
  const hasAnyChanges = hasSectionChanges || hasNameChanges;

  // ...
}
```

#### Пример 2: Инициализация черновика с защитой от повторной инициализации

```tsx
// ✅ Загрузка данных с флагом загрузки
const { data: usersData, isLoading: isUsersLoading } = useReadUsersUsersGet({
  tenant_id: effectiveTenantId,
  limit: 1000,
  skip: 0,
});

// ✅ Вычисление начального черновика (мемоизировано)
const initialUsersDraft = useMemo(() => {
  return allUsers
    .filter((u) => initialUserIds.includes(u.id))
    .map((u) => ({
      id: u.id,
      name: u.name,
      email: u.email || undefined,
      markedForDeletion: false,  // ✅ Метаданные для черновика
    }));
}, [allUsers, initialUserIds]);

// ✅ Черновик начинается ПУСТЫМ (не из initialData!)
const [usersDraft, setUsersDraft] = useState([]);
const lastInitializedRoleId = useRef(null);

// ✅ Синхронизация только после загрузки
useEffect(() => {
  if (open && roleId && !isUsersLoading && usersData) {
    if (lastInitializedRoleId.current !== roleId) {
      setUsersDraft(initialUsersDraft);
      lastInitializedRoleId.current = roleId;
    }
  }
}, [open, roleId, initialUsersDraft, isUsersLoading, usersData]);

// ✅ Сброс в обработчике события (не в useEffect)
const handleOpenChange = useCallback((newOpen: boolean) => {
  if (newOpen && !open) {
    setSessionKey((prev) => prev + 1);
    setSavedRoleOverride(null);
    setUsersDraft([]);  // ✅ Сброс черновика при открытии
    lastInitializedRoleId.current = null;  // ✅ Сброс флага
  }
  if (!newOpen) {
    reset(CREATE_DEFAULTS);
    setSavedRoleOverride(null);
    setUsersDraft([]);
    lastInitializedRoleId.current = null;
  }
  onOpenChange(newOpen);
}, [open, onOpenChange, reset]);
```

#### Пример 3: Синхронизация после сохранения

```tsx
saveMutation.mutate(payload, {
  onSuccess: async (res) => {
    const savedRole = res.data;

    // ✅ 1. Инвалидация кэшей
    await queryClient.invalidateQueries({ queryKey: ["roles"] });

    // ✅ 2. Обновление источника истины
    setSavedRoleOverride(savedRole);

    // ✅ 3. Синхронизация черновика полномочий с ответом сервера
    const freshPerms = (savedRole.permissions ?? []).map((p) => ({
      id: p.id,
      doctype: p.doctype,
      // ... все поля
    }));
    setPermissions(freshPerms);
    setInitialPermissionsSnapshot(JSON.stringify(freshPerms));

    // ✅ 4. Триггер пересинхронизации пользователей
    lastInitializedRoleId.current = null;
    setUsersResyncKey((prev) => prev + 1);

    // ✅ 5. Закрытие модалки только для режима копирования
    await onRoleSaved(savedRole.id, savedRole.name);
    if (isCopy) {
      onOpenChange(false);
    }

    toast({ title: "Роль сохранена" });
  },
});
```

#### Пример 4: Индикаторы изменений на вкладках

```tsx
<TabsList className="grid w-full grid-cols-4">
  <TabsTrigger value="main" className="relative">
    Основное
    {/* ✅ Индикатор "*" при изменениях */}
    {hasBasicsChanges && (
      <span className="absolute -top-1 -right-1 text-amber-500 text-xl font-bold leading-none">
        *
      </span>
    )}
  </TabsTrigger>

  <TabsTrigger value="sections" className="relative">
    Разделы({(sectionIds || []).length})
    {hasSectionChanges && (
      <span className="absolute -top-1 -right-1 text-amber-500 text-xl font-bold leading-none">
        *
      </span>
    )}
  </TabsTrigger>

  <TabsTrigger value="permissions" className="relative">
    Полномочия({activePermissionsCount})
    {hasPermissionChanges && (
      <span className="absolute -top-1 -right-1 text-amber-500 text-xl font-bold leading-none">
        *
      </span>
    )}
  </TabsTrigger>

  <TabsTrigger value="users" className="relative">
    Пользователи({selectedUserIds.length})
    {hasUserChanges && (
      <span className="absolute -top-1 -right-1 text-amber-500 text-xl font-bold leading-none">
        *
      </span>
    )}
  </TabsTrigger>
</TabsList>
```

#### Пример 5: Режим копирования с предзаполнением формы

```tsx
// ✅ Определение режима копирования
const isEdit = !!role;
const isCopy = !!copyFromRole && !isEdit;
const sourceRole = copyFromRole ?? role ?? null;

// ✅ При копировании используем организацию исходной роли
const [selectedTenantId, setSelectedTenantId] = useState(
  sourceRole?.tenant_id ?? "",
);

// ✅ Синхронизация формы с суффиксом "(копия)"
useEffect(() => {
  if (open && sourceRole) {
    reset({
      name: isCopy ? `${sourceRole.name} (копия)` : sourceRole.name || "",
      description: sourceRole.description || "",
      section_ids: sourceRole.section_ids || [],
    });
  } else if (open && !sourceRole) {
    reset(CREATE_DEFAULTS);
  }
}, [open, isCopy, sourceRole, reset]);

// ✅ При копировании НЕ копируем id полномочий (новые записи)
useEffect(() => {
  if (!open) return;
  const sourcePerms = sourceRole?.permissions ?? [];
  const perms = sourcePerms.map((p) => ({
    id: isCopy ? undefined : p.id,  // ✅ undefined для новых
    doctype: p.doctype,
    // ... остальные поля
  }));
  setPermissions(perms);
  setInitialPermissionsSnapshot(JSON.stringify(perms));
}, [open, sourceRole, isCopy]);

// ✅ При копировании закрываем модалку после сохранения
onSuccess: async (res) => {
  // ... синхронизация
  if (isCopy) {
    onOpenChange(false);
  }
}
```

### ❌ НЕПРАВИЛЬНО

#### Ошибка 1: Дублирование данных формы в отдельном `useState`

```tsx
// ❌ НЕПРАВИЛЬНО: параллельное состояние для данных формы
const [selectedSectionIds, setSelectedSectionIds] = useState(role?.section_ids || []);

// Форма уже управляет section_ids через useWatch!
// Теперь есть два источника истины → рассинхронизация при сохранении
```

**Правильно:** использовать `useWatch` для чтения и `field.onChange` для записи.

#### Ошибка 2: Использование `watch()` в зависимостях `useMemo`

```tsx
// ❌ НЕПРАВИЛЬНО: ссылка на функцию в зависимостях
const hasSectionChanges = useMemo(() => {
  const initial = (effectiveRole?.section_ids || []).slice().sort();
  // ❌ watch — это функция, а не значение!
  const current = (watch("section_ids") ?? []).slice().sort();
  return JSON.stringify(initial) !== JSON.stringify(current);
}, [effectiveRole?.section_ids, watch]);
// ⚠️ useMemo не пересчитается при изменении поля,
// потому что ссылка на функцию `watch` стабильна
```

**Правильно:** использовать `useWatch` и зависимость от значения.

#### Ошибка 3: `?? []` в зависимостях `useMemo`

```tsx
// ❌ НЕПРАВИЛЬНО: новый массив на каждом рендере
const sectionIds = watch("section_ids") ?? [];
// Каждый рендер создаёт НОВЫЙ [] при значении undefined

const hasChanges = useMemo(() => {
  // ...
}, [sectionIds]);  // ❌ sectionIds — новая ссылка каждый рендер!
```

**Правильно:** `useWatch` с `defaultValue: []` гарантирует стабильную ссылку.

#### Ошибка 4: `useState` + `useEffect` для вычисляемых значений

```tsx
// ❌ НЕПРАВИЛЬНО: каскадные ререндеры
const [hasChanges, setHasChanges] = useState(false);

useEffect(() => {
  setHasChanges(sectionIds.length !== initialSectionIds.length);
}, [sectionIds, initialSectionIds]);
// ⚠️ Каждый рендер → проверка зависимостей → возможный ререндер
```

**Правильно:** `useMemo` вычисляет значение синхронно без лишних ререндеров.

#### Ошибка 5: Инициализация черновика из данных до загрузки

```tsx
// ❌ НЕПРАВИЛЬНО: инициализация из ещё не загруженных данных
const initialDraft = useMemo(() => {
  return (usersData?.items ?? []).map((item) => ({...}));
}, [usersData]);

// ❌ useState зафиксирует пустой массив при первом рендере
const [draft, setDraft] = useState(initialDraft);
// При загрузке данных через 200мс черновик НЕ обновится!
```

**Правильно:** `useState([])` + `useEffect` с проверкой `!isLoading && data`.

#### Ошибка 6: Синхронизация формы в `useEffect` с `setState`

```tsx
// ❌ НЕПРАВИЛЬНО: сброс состояния в эффекте
useEffect(() => {
  if (!open) {
    setUsersDraft([]);  // ❌ Каскадный ререндер
    lastInitializedRoleId.current = null;
  }
}, [open]);
```

**Правильно:** сброс в обработчике события `handleOpenChange`.

#### Ошибка 7: Отсутствие `savedOverride` после сохранения

```tsx
// ❌ НЕПРАВИЛЬНО: сравнение с устаревшим пропом
onSuccess: async (res) => {
  // Нет обновления источника истины!
  await onRoleSaved(res.data.id, res.data.name);
}

// Индикаторы изменений сравнивают с `role` из родителя,
// который не обновился → ложные срабатывания
```

**Правильно:** `setSavedRoleOverride(res.data)` + `effectiveRole = savedRoleOverride ?? role`.

#### Ошибка 8: Отсутствие защиты от повторной инициализации

```tsx
// ❌ НЕПРАВИЛЬНО: повторная инициализация на каждый refetch
useEffect(() => {
  if (open && usersData) {
    setUsersDraft(initialUsersDraft);  // ❌ Затрёт изменения пользователя!
  }
}, [open, usersData]);
// Каждый фоновый refetch перезапишет черновик
```

**Правильно:** `useRef` с идентификатором сущности + проверка `lastInitializedId.current !== entityId`.

#### Ошибка 9: Неправильный порядок при сохранении

```tsx
// ❌ НЕПРАВИЛЬНО: закрытие модалки до инвалидации кэша
onSuccess: async () => {
  onOpenChange(false);  // ❌ Модалка закрыта, но кэш не обновлён
  await queryClient.invalidateQueries({ queryKey: ["roles"] });
}
// Пользователь видит модалку закрытой, но список не обновился
```

**Правильно:** сначала инвалидация, затем закрытие.

#### Ошибка 10: Индикатор изменений без `useMemo`

```tsx
// ❌ НЕПРАВИЛЬНО: пересчёт на каждом рендере
const hasChanges = JSON.stringify(sectionIds) !== JSON.stringify(initialSectionIds);
// ⚠️ JSON.stringify вызывается на каждом рендере, даже если значения не изменились
```

**Правильно:** обернуть в `useMemo` со стабильными зависимостями.

### Обоснование

#### Почему три типа состояния, а не одно?

| Тип состояния | Источник истины | Кто управляет | Пример |
|---------------|-----------------|---------------|--------|
| **Серверное** | БД | React Query | Список разделов, список пользователей, роль из БД |
| **Форма** | `react-hook-form` | RHF | Название роли, описание, `section_ids` |
| **Локальный черновик** | Компонент | `useState` + `useEffect` | Полномочия с флагом `markedForDeletion`, пользователи с `markedForDeletion` |

**Почему нельзя всё хранить в форме?**
- Форма не подходит для сложных структур с метаданными (`markedForDeletion`, `id: undefined` для новых)
- Форма не умеет "помечать на удаление" — это бизнес-логика, не валидация
- Черновики требуют сравнения с снапшотом для определения изменений

**Почему нельзя всё хранить в `useState`?**
- Нарушается Правило №37 (синхронизация формы при открытии)
- Дублирование данных между формой и `useState` → рассинхронизация
- Потеря преимуществ RHF (валидация, `reset`, `watch`)

#### Почему `useWatch`, а не `watch`?

| Аспект | `watch()` | `useWatch()` |
|--------|-----------|--------------|
| **Тип** | Метод объекта `useForm` | Отдельный хук |
| **Реактивность** | Не вызывает ререндер сам по себе | Вызывает ререндер при изменении |
| **Стабильность** | Ссылка на функцию стабильна, значение — нет | Значение стабильно между рендерами |
| **Использование в `useMemo`** | ⚠️ Функция в зависимостях не отслеживает значение | ✅ Значение в зависимостях корректно |
| **`defaultValue`** | Нет (нужен `?? []` → новый массив каждый рендер) | ✅ Есть (стабильная ссылка) |

#### Почему индикаторы через `JSON.stringify`, а не поэлементное сравнение?

| Аспект | `JSON.stringify` | Поэлементное сравнение |
|--------|------------------|------------------------|
| **Простота** | ✅ Одна строка | ⚠️ Цикл + логика сравнения |
| **Производительность** | ⚠️ Сериализация на каждый вызов | ✅ Ранний выход при несовпадении |
| **Порядок элементов** | ⚠️ Зависит от порядка → нужна предварительная сортировка | ⚠️ Тоже нужна сортировка |
| **Когда использовать** | ✅ Массивы до 100 элементов | ⚠️ Массивы > 1000 элементов |

Для ролей с десятками разделов и полномочий `JSON.stringify` с предварительной сортировкой — оптимальный выбор.

#### Почему `savedOverride`, а не обновление пропа из родителя?

| Аспект | Обновление пропа из родителя | `savedOverride` внутри модалки |
|--------|------------------------------|--------------------------------|
| **Скорость** | ⚠️ Требует инвалидации + перезапроса списка | ✅ Мгновенно (ответ мутации уже есть) |
| **Рассинхронизация** | ⚠️ Если родитель не обновился — индикаторы врут | ✅ Источник истины локальный |
| **Сложность** | ⚠️ Нужно передать `onSaved` с полным объектом | ✅ Модалка сама управляет |
| **Сброс** | ⚠️ Сложно определить, когда сбросить | ✅ При открытии новой сущности |

### Чек-лист применения

При создании сложной формы проверьте:

**Архитектура состояния:**
- [ ] Серверные данные загружаются через Orval-хуки
- [ ] Поля формы управляются через RHF
- [ ] Черновики с метаданными в `useState`
- [ ] Нет дублирования одного значения в двух местах

**Реактивность:**
- [ ] Реактивное чтение через `useWatch` с `defaultValue`
- [ ] Нет `watch()` в зависимостях `useMemo`
- [ ] Нет `?? []` в зависимостях `useMemo`
- [ ] Вычисляемые значения через `useMemo` со стабильными зависимостями

**Инициализация черновиков:**
- [ ] `useState` начинается с пустого массива
- [ ] `useEffect` проверяет `!isLoading && data` перед инициализацией
- [ ] `useRef` защищает от повторной инициализации
- [ ] Сброс черновика в `handleOpenChange`, а не в `useEffect`

**Синхронизация:**
- [ ] `savedOverride` имеет приоритет над пропом
- [ ] Черновики синхронизируются с ответом сервера после сохранения
- [ ] `savedOverride` сбрасывается при открытии новой сущности

**Индикаторы изменений:**
- [ ] Индикаторы вычисляются через `useMemo`
- [ ] Агрегированный `hasAnyChanges` через `||`
- [ ] Индикаторы отображаются на вкладках (`*`)

**Порядок при сохранении:**
- [ ] Инвалидация кэшей
- [ ] Синхронизация черновиков
- [ ] Обновление `savedOverride`
- [ ] Закрытие модалки (для копирования/создания)
- [ ] Вызов `onSaved`

### Связь с другими правилами

| Правило | Связь |
|---------|-------|
| №9 (Orval-хуки) | Серверные данные через Orval-хуки |
| №20 (Сброс формы) | `reset(CREATE_DEFAULTS)` при закрытии |
| №24 (Порядок при сохранении) | Инвалидация → закрытие → сброс → `onSaved` |
| №34 (Switch) | Переключатели через `<Controller>` |
| №35 (Модалки в отдельном компоненте) | Форма вынесена в `EditRoleModal` |
| №36 (Безопасная обработка ошибок) | `unknown` в `catch` |
| №37 (Синхронизация при открытии) | `useEffect` для `reset`, `useWatch` для реактивности |
| №38 (Асинхронная инициализация таблиц) | Инициализация черновиков после загрузки |
| №41 (Общие требования к формам) | `react-hook-form` + Zod + `useToast` |
| №45 (Совместимость с React Compiler) | `useWatch` вместо `watch`, стабильные зависимости |

### Примеры из проекта

| Компонент | Что демонстрирует |
|-----------|-------------------|
| `EditRoleModal` | Полная реализация: вкладки, черновики, индикаторы, режим копирования |
| `EditUserModal` | Синхронизация формы через `reset` в `useEffect` (Правило №37) |
| `AdminRolesPage` | Кнопка «Копировать» + передача `copyFromRole` |
| `PermissionsTab` | Черновик с `markedForDeletion` и снапшотом |
| `UsersTab` | Черновик пользователей с защитой от повторной инициализации |

---

**Это правило обязательно для всех сложных форм проекта.** Любое отклонение (дублирование данных формы в `useState`, использование `watch()` в зависимостях, отсутствие `savedOverride`) будет считаться нарушением архитектуры и подлежит исправлению при код-ревью.