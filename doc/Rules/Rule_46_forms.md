# Урок: Архитектура сложных форм на примере `EditRoleModal`

## 1. Общая картина: три типа состояния

Любая сложная форма работает с **тремя типами состояния**, и ключевой навык — понимать, какое состояние где живёт и кто им управляет.

```
┌─────────────────────────────────────────────────────────┐
│                    СЛОИ СОСТОЯНИЯ                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. СЕРВЕРНОЕ СОСТОЯНИЕ (источник истины)               │
│     → Управляется: React Query (TanStack Query)         │
│     → Примеры: список разделов, список пользователей,    │
│       данные роли из БД                                 │
│     → Характеристики: асинхронное, кэшируемое,           │
│       может устаревать, перезапрашивается                │
│                                                         │
│  2. СОСТОЯНИЕ ФОРМЫ (черновик пользователя)             │
│     → Управляется: React Hook Form (RHF)                │
│     → Примеры: название роли, описание, section_ids     │
│     → Характеристики: синхронное, локальное,             │
│       сбрасывается при закрытии                         │
│                                                         │
│  3. ЛОКАЛЬНОЕ СОСТОЯНИЕ ЧЕРНОВИКОВ                      │
│     → Управляется: useState + логика синхронизации      │
│     → Примеры: permissions[], usersDraft[]              │
│     → Характеристики: массивы объектов с метаданными    │
│       (markedForDeletion, id: undefined для новых)      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Главный принцип:** эти три слоя **никогда не смешиваются**. Серверные данные не хранятся в `useState`, состояние формы не дублируется в отдельные `useState`, черновики не записываются в RHF, если они не являются простыми полями.

---

## 2. Библиотеки и их роли

### 2.1. React Hook Form (RHF) — управление формой

**Что делает:** управляет значениями полей формы, валидацией, состоянием отправки.

**Ключевые элементы:**

```typescript
// 1. Инициализация формы со схемой валидации
const { control, handleSubmit, reset } = useForm<RoleFormData>({
  resolver: zodResolver(roleSchema),   // Zod-схема для валидации
  defaultValues: CREATE_DEFAULTS,      // Начальные значения
});
```

**`useForm` возвращает:**

| Метод | Назначение | Когда использовать |
|-------|-----------|---------------------|
| `control` | Передаётся в `<Controller>` и `useWatch` | Связывание кастомных компонентов с формой |
| `handleSubmit` | Обёртка для `onSubmit`, запускает валидацию | В `<form onSubmit={...}>` |
| `reset` | Сбрасывает форму к заданным значениям | При открытии/закрытии модалки |
| `watch` | Читает значение поля (метод, не хук) | ⚠️ Только внутри `onSubmit`, не в рендере |
| `formState` | `errors`, `isSubmitting`, `isDirty` | Для отображения ошибок и блокировки кнопки |

**`<Controller>` — мост между RHF и кастомными компонентами:**

```tsx
<Controller
  name="section_ids"       // Имя поля в форме
  control={control}        // Ссылка на форму
  render={({ field }) => (
    <ReferenceMultiSelectChips
      value={field.value ?? []}       // Значение из формы
      onValueChange={field.onChange}  // Запись в форму
      // ... другие пропсы
    />
  )}
/>
```

`field` содержит: `value`, `onChange`, `onBlur`, `ref`, `name`. Мы передаём `value` и `onChange` в компонент, и он становится управляемым формой.

**`useWatch` — реактивное чтение значения поля:**

```typescript
// ✅ Хук: вызывает ререндер при изменении поля
const sectionIds = useWatch({
  control,
  name: "section_ids",
  defaultValue: [],   // Гарантия типа (не undefined)
});

// Теперь можно использовать в зависимостях:
const hasSectionChanges = useMemo(() => {
  // ...сравнение с initialSectionIds
}, [effectiveRole?.section_ids, sectionIds]);  // ✅ Стабильная зависимость
```

**Почему `useWatch`, а не `watch`:**

| Аспект | `watch()` | `useWatch()` |
|--------|-----------|--------------|
| Что это | Метод объекта `useForm` | Отдельный хук |
| Реактивность | Не вызывает ререндер сам по себе | Вызывает ререндер при изменении |
| Использование в `useMemo` | ⚠️ Нестабильная ссылка | ✅ Стабильное значение |
| Использование в рендере | ⚠️ Читает при каждом рендере | ✅ Подписан на конкретное поле |

---

### 2.2. React Query (TanStack Query) — серверное состояние

**Что делает:** загружает данные с сервера, кэширует, перезапрашивает при инвалидации, управляет состоянием загрузки.

**Ключевые хуки в нашей форме:**

```typescript
// Загрузка данных (автоматический кэш, перезапрос при инвалидации)
const { data: sectionsData } = useGetSectionsSectionsGet({
  target_tenant_id: effectiveTenantId,
  limit: 1000,
  skip: 0,
});

const { data: usersData, isLoading: isUsersLoading } = useReadUsersUsersGet({
  tenant_id: effectiveTenantId,
  limit: 1000,
  skip: 0,
});

// Мутация (сохранение данных на сервер)
const saveMutation = useSaveRoleRolesSavePost();
```

**Жизненный цикл данных в RQ:**

```
Запрос → isLoading: true → data: undefined
       → isLoading: false → data: { items: [...], total: N }
       → (при инвалидации) → isFetching: true → data обновляется
```

**Инвалидация кэша после сохранения:**

```typescript
// После успешного сохранения говорим RQ: "эти данные устарели"
await queryClient.invalidateQueries({ queryKey: ["roles"] });
// RQ автоматически перезапрашивает все запросы с этим ключом
```

**Критический паттерн: ожидание загрузки перед инициализацией черновика**

```typescript
// ❌ НЕПРАВИЛЬНО: инициализация до загрузки
useEffect(() => {
  if (open) {
    setUsersDraft(initialUsersDraft); // initialUsersDraft = [] при загрузке!
  }
}, [open, initialUsersDraft]);

// ✅ ПРАВИЛЬНО: ждём завершения загрузки
useEffect(() => {
  if (open && roleId && !isUsersLoading && usersData) {
    if (lastInitializedRoleId.current !== roleId) {
      setUsersDraft(initialUsersDraft);  // Теперь данные гарантированно загружены
      lastInitializedRoleId.current = roleId;
    }
  }
}, [open, roleId, initialUsersDraft, isUsersLoading, usersData]);
```

Это **Правило №38** — асинхронная инициализация таблиц. Без него при перезагрузке страницы (F5) черновик инициализируется пустым массивом и не обновляется.

---

### 2.3. Zod — валидация формы

```typescript
const roleSchema = z.object({
  name: z.string().min(1, "Название обязательно"),
  description: z.string().optional(),
  section_ids: z.array(z.string()).optional(),
});

type RoleFormData = z.infer<typeof roleSchema>;  // Тип выводится из схемы
```

**Принцип:** схема валидации — единственный источник истины для типов формы. `z.infer` генерирует TypeScript-тип автоматически, что исключает рассинхронизацию между валидацией и типами.

---

### 2.4. Остальные библиотеки

| Библиотека | Роль в форме |
|-----------|--------------|
| **shadcn/ui** (`Dialog`, `Tabs`, `Button`, `Input`) | UI-компоненты |
| **lucide-react** (`Loader2`, `Check`, `Building2`) | Иконки |
| **useToast** (shadcn) | Уведомления пользователю |
| **Orval-сгенерированные хуки** | Типобезопасные обёртки над API |

---

## 3. Ключевые паттерны формы

### 3.1. Паттерн «Источник истины после сохранения» (`savedRoleOverride`)

**Проблема:** после сохранения роли проп `role` из родителя не обновляется автоматически. Если пользователь продолжит редактировать форму, индикаторы изменений будут сравнивать с устаревшими данными.

**Решение:** сохраняем ответ мутации как новый источник истины.

```typescript
// Состояние: сохранённая версия роли
const [savedRoleOverride, setSavedRoleOverride] =
  useState<RoleResponseSchema | null>(null);

// Эффективная роль: сохранённая версия имеет приоритет
const effectiveRole: RoleResponseSchema | null =
  savedRoleOverride ?? sourceRole ?? null;

// В мутации:
onSuccess: async (res) => {
  setSavedRoleOverride(res.data);  // Обновляем источник истины
  // Теперь все индикаторы изменений сравнивают с актуальными данными
}
```

**Как это работает:**

```
До сохранения:
  effectiveRole = role из пропсов (данные из списка)
  Пользователь меняет название → hasBasicsChanges = true → индикатор "*"

После сохранения:
  savedRoleOverride = ответ сервера (актуальные данные)
  effectiveRole = savedRoleOverride (приоритет)
  Название в форме совпадает с effectiveRole.name → hasBasicsChanges = false → "*" исчезает
```

### 3.2. Паттерн «Гарантированный перемонт» (`sessionKey`)

**Проблема:** при закрытии и повторном открытии модалки компонент может не перемонтироваться (особенно если `key` не меняется), и старое состояние остаётся.

**Решение:** увеличиваем счётчик при каждом открытии.

```typescript
const [sessionKey, setSessionKey] = useState(0);

const handleOpenChange = (newOpen: boolean) => {
  if (newOpen && !open) {
    setSessionKey((prev) => prev + 1);  // Увеличиваем при каждом открытии
    // ... сброс состояния
  }
  // ...
};

// В JSX:
<DialogContent key={isEdit ? `edit-${role?.id}-${sessionKey}` : `create-${sessionKey}`}>
```

При изменении `sessionKey` React полностью размонтирует и заново монтирует `DialogContent`, что гарантирует чистое состояние.

### 3.3. Паттерн «Защита от повторной инициализации» (`lastInitializedRoleId`)

**Проблема:** `useEffect` синхронизации черновика может срабатывать многократно (при фоновых перезапросах данных, при изменении зависимостей). Без защиты каждый срабатывание перезаписывает черновик пользователя.

**Решение:** `useRef` хранит идентификатор сущности, для которой уже проведена инициализация.

```typescript
const lastInitializedRoleId = useRef<string | null>(null);

useEffect(() => {
  if (open && roleId && !isUsersLoading && usersData) {
    if (lastInitializedRoleId.current !== roleId) {  // ✅ Проверяем
      setUsersDraft(initialUsersDraft);
      lastInitializedRoleId.current = roleId;  // ✅ Запоминаем
    }
  }
}, [/* ... */]);
```

**Почему `useRef`, а не `useState`:**
- `useRef` не вызывает ререндер при изменении
- Нам не нужно отображать это значение в UI
- Нам нужно только запомнить факт инициализации

### 3.4. Паттерн «Производные значения через `useMemo`»

**Проблема:** нужно вычислить `hasSectionChanges`, `newSectionIds`, `deletedSectionIds`. Соблазн — хранить в `useState` и обновлять через `useEffect`.

**Почему это плохо:**

```typescript
// ❌ АНТИПАТТЕРН: параллельное состояние
const [hasSectionChanges, setHasSectionChanges] = useState(false);

useEffect(() => {
  const initial = effectiveRole?.section_ids || [];
  const current = sectionIds;
  setHasSectionChanges(JSON.stringify(initial) !== JSON.stringify(current));
}, [sectionIds, effectiveRole]);
// Проблема: лишний ререндер, рассинхронизация, каскадные обновления
```

**Правильно: `useMemo` — вычисление, а не состояние**

```typescript
// ✅ Производное значение вычисляется при каждом рендере
const hasSectionChanges = useMemo(() => {
  const initial = (effectiveRole?.section_ids || []).slice().sort();
  const current = (sectionIds || []).slice().sort();
  return JSON.stringify(initial) !== JSON.stringify(current);
}, [effectiveRole?.section_ids, sectionIds]);
```

**Принцип:** если значение можно **вычислить** из существующих данных — это `useMemo`, а не `useState`. `useState` — только для данных, которые **изменяются пользователем** или **приходят извне** и не могут быть вычислены.

### 3.5. Паттерн «Черновик с метаданными»

Для вкладок «Полномочия» и «Пользователи» недостаточно просто хранить массив значений. Нужно отслеживать:
- Какие записи новые (`id: undefined`)
- Какие помечены на удаление (`markedForDeletion: true`)
- Какие существующие (`id: "uuid"`)

```typescript
interface PermissionDraft {
  id?: string;              // undefined для новых записей
  doctype: string;
  // ... другие поля
  markedForDeletion?: boolean;  // true для помеченных на удаление
}

const [permissions, setPermissions] = useState<PermissionDraft[]>(initialPerms);
const [initialPermissionsSnapshot, setInitialPermissionsSnapshot] =
  useState<string>(JSON.stringify(initialPerms));

// Индикатор изменений: сравнение с снапшотом
const hasPermissionChanges = useMemo(() => {
  return JSON.stringify(permissions) !== initialPermissionsSnapshot;
}, [permissions, initialPermissionsSnapshot]);
```

**При сохранении:**
```typescript
permissions: permissions
  .filter((p) => !p.markedForDeletion)  // Исключаем помеченные на удаление
  .map((p) => ({
    // ... поля для бэкенда
    ...(p.id ? { id: p.id } : {}),  // id только для существующих
  })),
```

**После сохранения:** синхронизируем черновик с ответом сервера:
```typescript
setPermissions(freshPerms);
setInitialPermissionsSnapshot(JSON.stringify(freshPerms));
// Теперь все записи имеют id, нет помеченных на удаление → индикатор "*" исчезает
```

---

## 4. Реактивность и избегание каскадных ререндеров

### 4.1. Что вызывает ререндер компонента

Компонент ререндерится, когда:
1. Изменяется `useState` (вызван сеттер)
2. Изменяется проп от родителя
3. Изменяется значение из контекста
4. `useQuery` получает новые данные
5. `useWatch` фиксирует изменение поля формы
6. Родительский компонент ререндерится (и не мемоизирован)

### 4.2. Каскадный ререндер: как возникает

```
Сценарий: пользователь вводит символ в поле "Название"

1. Input onChange → field.onChange("Б")
2. RHF обновляет значение поля
3. useWatch фиксирует изменение → ререндер компонента
4. В рендере вычисляется:
   - hasBasicsChanges = useMemo(...) → пересчитывается (зависимость изменилась)
   - hasSectionChanges = useMemo(...) → НЕ пересчитывается (зависимости те же)
   - selectedUserIds = useMemo(...) → НЕ пересчитывается
5. Ререндер завершён

Итого: 1 ререндер, пересчитаны только зависимые значения
```

### 4.3. Антипаттерн: `setState` в `useEffect`

```typescript
// ❌ АНТИПАТТЕРН
const [hasChanges, setHasChanges] = useState(false);

useEffect(() => {
  setHasChanges(sectionIds.length !== initialSectionIds.length);
}, [sectionIds, initialSectionIds]);
```

**Что происходит:**

```
1. Изменяется sectionIds
2. Компонент ререндерится (1-й ререндер)
3. После рендера срабатывает useEffect
4. setHasChanges вызывает 2-й ререндер
5. После 2-го рендера снова проверяются зависимости
6. Если зависимости не изменились — цикл останавливается
   Если изменились (например, из-за нестабильной ссылки) — 3-й ререндер
```

**Итого:** 2+ ререндера вместо 1. В сложных формах с несколькими `useEffect` это превращается в каскад.

**Правило:** если значение можно вычислить из других значений — используй `useMemo`, а не `useState + useEffect`.

### 4.4. Антипаттерн: нестабильные зависимости

```typescript
// ❌ АНТИПАТТЕРН 1: новый объект на каждом рендере
const hasChanges = useMemo(() => {
  return sectionIds.length > 0;
}, [sectionIds.filter(id => id !== "")]);  // filter создаёт НОВЫЙ массив

// ✅ ПРАВИЛЬНО: сначала вычисли стабильное значение
const activeSectionIds = useMemo(
  () => sectionIds.filter(id => id !== ""),
  [sectionIds]
);
const hasChanges = useMemo(() => {
  return activeSectionIds.length > 0;
}, [activeSectionIds]);
```

```typescript
// ❌ АНТИПАТТЕРН 2: функция в зависимостях
const hasChanges = useMemo(() => {
  return computeChanges(sectionIds);
}, [computeChanges]);  // Функция создаётся заново на каждом рендере

// ✅ ПРАВИЛЬНО: оберни функцию в useCallback или вынеси из компонента
const computeChanges = useCallback((ids: string[]) => {
  // ...
}, []);  // Стабильная ссылка
```

```typescript
// ❌ АНТИПАТТЕРН 3: ?? [] в зависимостях
const hasChanges = useMemo(() => {
  // ...
}, [(sectionIds ?? [])]);  // Новый [] на каждом рендере при undefined

// ✅ ПРАВИЛЬНО: используй useWatch с defaultValue
const sectionIds = useWatch({ control, name: "section_ids", defaultValue: [] });
const hasChanges = useMemo(() => {
  // ...
}, [sectionIds]);  // Стабильный массив
```

### 4.5. Антипаттерн: параллельное состояние для данных формы

```typescript
// ❌ АНТИПАТТЕРН: дублирование данных формы в отдельном состоянии
const [sectionIds, setSectionIds] = useState<string[]>(role?.section_ids || []);

useEffect(() => {
  if (open && role) {
    setSectionIds(role.section_ids || []);  // setState в useEffect!
  }
}, [open, role]);

// Теперь есть ДВА источника: форма (RHF) и sectionIds (useState)
// Они могут рассинхронизироваться
```

**✅ Правильно:** данные формы живут только в RHF. Для чтения используем `useWatch`, для записи — `field.onChange`.

```typescript
// Данные в форме
<Controller
  name="section_ids"
  control={control}
  render={({ field }) => (
    <ReferenceMultiSelectChips
      value={field.value ?? []}
      onValueChange={field.onChange}
    />
  )}
/>

// Реактивное чтение для индикаторов
const sectionIds = useWatch({ control, name: "section_ids", defaultValue: [] });
```

### 4.6. Правило «Один рендер — одно изменение»

Каждое пользовательское действие должно вызывать **ровно один ререндер**. Если после действия происходит 2+ ререндера — есть антипаттерн.

| Действие | Ожидаемый ререндер | Антипаттерн |
|----------|-------------------|-------------|
| Ввод в поле | 1 (RHF + useWatch) | `setState` в `useEffect` → 2+ |
| Выбор элемента в справочнике | 1 (field.onChange → RHF) | `setState` + `reset` → 2+ |
| Открытие модалки | 1 (сброс формы + инициализация) | `setState` в `useEffect` → 3+ |
| Сохранение | 1 (ответ мутации → обновление) | `setState` + `invalidateQueries` без ожидания → 3+ |

---

## 5. Обобщённое правило для сложных форм

Формулирую как **Правило №46** для проекта:

---

# Правило №46: Архитектура сложных форм с множественными источниками данных

## Суть

Сложные формы (модальные окна с вкладками, таблицами, справочниками и черновиками) строятся на строгом разделении трёх типов состояния: серверного (React Query), формы (React Hook Form) и локальных черновиков (`useState` с метаданными). Реактивность обеспечивается через производные значения (`useMemo`, `useWatch`), а не через каскады `setState` в `useEffect`. Каждый пользовательское действие вызывает ровно один ререндер.

## Строгие требования

### 1. Разделение состояния

1.1. **Серверные данные** загружаются только через Orval-хуки (`useGetXxx`, `useReadXxx`). Запрещено хранить их в `useState`.

1.2. **Поля формы** управляются только через RHF (`useForm`, `<Controller>`, `useWatch`). Запрещено дублировать значения полей в отдельные `useState`.

1.3. **Черновики с метаданными** (массивы объектов с `markedForDeletion`, `id: undefined` для новых) хранятся в `useState`, но инициализируются только после завершения загрузки данных.

### 2. Производные значения

2.1. Все вычисляемые значения (индикаторы изменений, фильтрованные списки, подсчёты) реализуются через `useMemo`.

2.2. Запрещено использовать `useState` + `useEffect` для значений, которые можно вычислить из существующих данных.

2.3. Зависимости `useMemo` должны быть стабильными ссылками:
- Примитивы (`string`, `number`, `boolean`)
- Результаты других `useMemo`
- Значения из `useWatch` (с `defaultValue`)
- Запрещено: функции без `useCallback`, результаты `.filter()`/`.map()` без `useMemo`, `?? []` / `?? {}`

### 3. Реактивный доступ к полям формы

3.1. Для чтения значений полей в рендере используется `useWatch` с `defaultValue`.

3.2. Запрещено использовать `watch()` (метод) в зависимостях `useMemo` или в рендере.

3.3. Для записи в форму используется `field.onChange` из `<Controller>`.

### 4. Инициализация черновиков

4.1. `useState` черновика начинается с пустого массива.

4.2. Инициализация из данных происходит в `useEffect` с обязательной проверкой `!isLoading && data`.

4.3. Защита от повторной инициализации через `useRef` с идентификатором сущности.

4.4. Сброс черновика при закрытии: `setState([])` + `ref.current = null`.

### 5. Источник истины после сохранения

5.1. Ответ мутации сохраняется как `savedOverride` и имеет приоритет над пропом из родителя.

5.2. Все индикаторы изменений сравнивают с `effectiveEntity = savedOverride ?? prop ?? null`.

5.3. Черновики синхронизируются с ответом сервера после сохранения.

### 6. Гарантированный перемонт

6.1. При открытии модалки увеличивается `sessionKey`.

6.2. `key` на корневом элементе модалки включает `sessionKey`.

6.3. При закрытии сбрасываются: форма (`reset`), черновики, `savedOverride`, ref-флаги.

### 7. Индикаторы изменений

7.1. Для простых полей (название, описание): сравнение `useWatch` значения с `effectiveEntity?.field`.

7.2. Для массивов (разделы): сравнение отсортированных массивов через `JSON.stringify`.

7.3. Для черновиков (полномочия, пользователи): сравнение с снапшотом через `JSON.stringify`.

7.4. Агрегированный индикатор `hasAnyChanges` объединяет все индикаторы через `||`.

## Проверка на каскадные ререндеры

Перед коммитом формы откройте компонент в браузере и выполните:
1. Введите символ в поле → в консоли должен быть **1** ререндер (проверить через `console.log` в рендере или через React DevTools)
2. Выберите элемент в справочнике → **1** ререндер
3. Откройте модалку → **1** ререндер (после загрузки данных)
4. Сохраните → **1** ререндер после ответа сервера

Если ререндеров больше — ищите `setState` в `useEffect`, нестабильные зависимости или дублирование состояния.

---

## 6. Критика и предложения по улучшению

### 6.1. Что можно улучшить в текущей форме

**Проблема 1: `useEffect` синхронизации полномочий с `eslint-disable`**

```typescript
// Текущий код:
useEffect(() => {
  if (!open) return;
  // ...
  // eslint-disable-next-line react-hooks/set-state-in-effect
  setPermissions(perms);
  setInitialPermissionsSnapshot(JSON.stringify(perms));
}, [open, sourceRole, isCopy]);
```

`eslint-disable` — признак того, что паттерн не идеален. Этот `useEffect` нужен, потому что `permissions` — это черновик с метаданными, который не помещается в RHF. Но его можно изолировать в кастомный хук:

```typescript
// Предложение: вынести в хук
const { permissions, setPermissions, initialPermissionsSnapshot, hasPermissionChanges } =
  usePermissionsDraft({
    open,
    sourceRole,
    isCopy,
  });
```

**Проблема 2: `handleTenantChange` проверяет сохранённые связи**

```typescript
const hasSections = (sourceRole?.section_ids?.length ?? 0) > 0;
const hasPermissions = (sourceRole?.permissions?.length ?? 0) > 0;
```

Это проверяет **сохранённые** данные, а не текущее состояние формы. Если пользователь добавил разделы в форме, но не сохранил, и пытается сменить организацию — проверка пропустит, хотя логичнее было бы предупредить.

**Предложение:** проверять текущее состояние формы:

```typescript
const hasSections = sectionIds.length > 0;
const hasPermissions = permissions.filter((p) => !p.markedForDeletion).length > 0;
const hasUsers = selectedUserIds.length > 0;
```

Но тогда нужно будет синхронизировать это поведение с бэкенд-проверкой в `services.py`, которая проверяет сохранённые данные. Это вопрос дизайна: что мы защищаем — от смены организации с **сохранёнными** связями или с **любыми** связями (включая несохранённые)?

**Проблема 3: дублирование `initialPerms`**

`initialPerms` вычисляется при каждом рендере, но `useState(initialPerms)` использует только первое значение. Можно убрать `initialPerms` и сразу инициализировать пустым массивом, а инициализацию делать в `useEffect`:

```typescript
const [permissions, setPermissions] = useState<PermissionDraft[]>([]);
// Инициализация в useEffect синхронизации
```

Это уже фактически есть (через `useEffect` синхронизации полномочий), но `initialPerms` всё ещё вычисляется. Это не ошибка, но лишний код.

### 6.2. Архитектурные улучшения для будущих форм

**Предложение 1: Кастомный хук `useFormDirtyTracking`**

Индикаторы изменений повторяются во всех формах. Можно вынести:

```typescript
function useFormDirtyTracking<T>({
  effectiveEntity,
  watchedFields,
  drafts,
}: {
  effectiveEntity: T | null;
  watchedFields: Record<string, { current: unknown; initial: unknown }>;
  drafts: Record<string, { current: string; snapshot: string }>;
}) {
  const fieldChanges = useMemo(() => {
    // ... сравнение полей
  }, [/* ... */]);

  const draftChanges = useMemo(() => {
    // ... сравнение черновиков
  }, [/* ... */]);

  const hasAnyChanges = Object.values(fieldChanges).some(Boolean)
    || Object.values(draftChanges).some(Boolean);

  return { hasAnyChanges, fieldChanges, draftChanges };
}
```

**Предложение 2: Кастомный хук `useDraftSync`**

Логика синхронизации черновиков (защита от повторной инициализации, ожидание загрузки, сброс при закрытии) повторяется для `usersDraft` и `permissions`. Можно вынести:

```typescript
function useDraftSync<T>({
  open,
  entityId,
  initialDraft,
  isLoading,
  data,
  sessionKey,
}: {
  open: boolean;
  entityId: string | undefined;
  initialDraft: T[];
  isLoading: boolean;
  data: unknown;
  sessionKey: number;
}) {
  const [draft, setDraft] = useState<T[]>([]);
  const lastInitializedRef = useRef<string | null>(null);

  useEffect(() => {
    if (!open) {
      setDraft([]);
      lastInitializedRef.current = null;
      return;
    }
    if (entityId && !isLoading && data) {
      const currentKey = `${entityId}-${sessionKey}`;
      if (lastInitializedRef.current !== currentKey) {
        setDraft(initialDraft);
        lastInitializedRef.current = currentKey;
      }
    }
  }, [open, entityId, initialDraft, isLoading, data, sessionKey]);

  return [draft, setDraft] as const;
}
```

**Предложение 3: Типизация `PermissionDraft` с дискриминированным союзом**

Сейчас `id?: string` — опциональный. Для новых записей `id` не просто отсутствует — его **не должно быть**. Для помеченных на удаление `markedForDeletion: true`. Можно использовать дискриминированный союз:

```typescript
type PermissionDraft =
  | { status: "existing"; id: string; /* ... */ }
  | { status: "new"; /* ... без id */ }
  | { status: "deleted"; id: string; /* ... */ };
```

Это даст компилятору больше информации и исключит ошибки вроде «передали `id` для новой записи».

---

## 7. Итоговая схема работы формы

```
┌──────────────────────────────────────────────────────────────────┐
│                    EditRoleModal                                  │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ПРОПСЫ: open, role, copyFromRole, onOpenChange,         │    │
│  │         onRoleSaved                                     │    │
│  └─────────────────────────────────────────────────────────┘    │
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ВЫЧИСЛЕНИЯ:                                             │    │
│  │   isEdit = !!role                                       │    │
│  │   isCopy = !!copyFromRole && !isEdit                    │    │
│  │   sourceRole = copyFromRole ?? role                     │    │
│  │   effectiveRole = savedRoleOverride ?? sourceRole       │    │
│  │   effectiveTenantId = selectedTenantId || currentTenantId│    │
│  └─────────────────────────────────────────────────────────┘    │
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ RQ-ХУКИ (серверное состояние):                          │    │
│  │   useGetUserAuthUserGet()     → текущий пользователь    │    │
│  │   useReadTenantsTenantsGet()  → справочник организаций  │    │
│  │   useReadUsersUsersGet()      → пользователи для вкладки│    │
│  │   useGetSectionsSectionsGet() → разделы для вкладки     │    │
│  │   useSaveRoleRolesSavePost()  → мутация сохранения      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ RHF (состояние формы):                                  │    │
│  │   useForm({ resolver: zodResolver(roleSchema) })        │    │
│  │   control, handleSubmit, reset                          │    │
│  │                                                         │    │
│  │   useWatch("section_ids") → sectionIds                  │    │
│  │   useWatch("name")        → watchedName                 │    │
│  │   useWatch("description") → watchedDescription          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ЛОКАЛЬНЫЕ ЧЕРНОВИКИ:                                    │    │
│  │   permissions: PermissionDraft[]                        │    │
│  │   initialPermissionsSnapshot: string                    │    │
│  │   usersDraft: UserDraft[]                               │    │
│  │   lastInitializedRoleId: useRef                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ПРОИЗВОДНЫЕ ЗНАЧЕНИЯ (useMemo):                         │    │
│  │   hasBasicsChanges     ← watchedName vs effectiveRole   │    │
│  │   hasTenantChanges     ← effectiveTenantId vs effective │    │
│  │   hasSectionChanges    ← sectionIds vs effectiveRole    │    │
│  │   hasPermissionChanges ← permissions vs snapshot        │    │
│  │   hasUserChanges       ← selectedUserIds vs initial     │    │
│  │   hasAnyChanges        ← все выше через ||              │    │
│  │   newSectionIds        ← sectionIds - initialSectionIds │    │
│  │   deletedSectionIds    ← initialSectionIds - sectionIds │    │
│  └─────────────────────────────────────────────────────────┘    │
│                          ↓                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ JSX:                                                    │    │
│  │   <Dialog> → <form> → <Tabs>                            │    │
│  │     <TabsTrigger> × 4 (с индикаторами *)                │    │
│  │     <TabsContent> × 4 (Основное, Разделы, Полномочия,  │    │
│  │                        Пользователи)                    │    │
│  │   <DialogFooter> → кнопки Отмена/Закрыть, Сохранить     │    │
│  └─────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────┘
```

---

Это обобщённое правило можно сохранить в `frontend_rules` как **Правило №46** и применять при создании всех будущих сложных форм. Если нужно, могу оформить его в формате существующих правил с примерами правильного и неправильного кода.