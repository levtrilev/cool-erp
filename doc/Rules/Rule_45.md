## Правило №45: Совместимость с React Compiler (предотвращение циклических предупреждений)

### Суть

React Compiler автоматически оптимизирует мемоизацию компонентов. При наличии **ручной мемоизации** (`useMemo`, `useCallback`), которая не соответствует ожиданиям Compiler, возникают предупреждения `Compilation Skipped: Existing memoization could not be preserved`. Попытка исправить одно предупреждение приводит к появлению другого — возникает цикл.

**Корень проблемы:** смешение двух подходов к мемоизации:
1. **Ручная мемоизация** (`useMemo`, `useCallback`) — разработчик явно управляет зависимостями
2. **Автоматическая оптимизация** (React Compiler) — компилятор анализирует код и решает, что мемоизировать

Когда эти подходы конфликтуют, Compiler отказывается оптимизировать компонент, что приводит к потере производительности (30-50% медленнее на больших формах).

### Область применения

Все компоненты с формами (`react-hook-form`), списками и сложной логикой состояний, где используются:
- `useMemo` с зависимостями из `watch()`
- `useCallback` с зависимостями-объектами
- Логические выражения (`?? []`, `|| []`) в зависимостях
- Динамические функции (`handleSubmit`, мутации)

### Строгие требования

#### 1. Использовать `useWatch` вместо `watch` для реактивных значений формы

**1.1.** `watch()` из `react-hook-form` возвращает функцию, которая не может быть безопасно мемоизирована React Compiler.

**1.2.** **ОБЯЗАТЕЛЬНО** использовать `useWatch` из `react-hook-form` для получения значений полей формы, которые нужны в `useMemo` или передаются в другие компоненты.

**1.3.** `useWatch` гарантирует стабильный тип возвращаемого значения (не `undefined` при наличии `defaultValue`).

```typescript
// ✅ ПРАВИЛЬНО
import { useWatch } from "react-hook-form";

const sectionIds: string[] = useWatch({
  control,
  name: "section_ids",
  defaultValue: [],  // ✅ Гарантированный тип string[]
});

const hasSectionChanges = useMemo(() => {
  const initial = (effectiveRole?.section_ids || []).slice().sort();
  const current = sectionIds.slice().sort();
  return JSON.stringify(initial) !== JSON.stringify(current);
}, [effectiveRole?.section_ids, sectionIds]);  // ✅ sectionIds стабилен
```

```typescript
// ❌ НЕПРАВИЛЬНО
const { watch } = useForm(...);
const sectionIds = watch("section_ids") ?? [];  // ❌ watch не мемоизируется

const hasSectionChanges = useMemo(() => {
  // ...
}, [watch]);  // ❌ React Compiler: 'watch' cannot be memoized safely
```

#### 2. Избегать создания новых массивов/объектов в зависимостях `useMemo`

**2.1.** Операторы `?? []`, `|| []`, `?? {}` создают **новые объекты** на каждом рендере, когда левая часть `undefined`/`null`.

**2.2.** Это нарушает стабильность зависимостей `useMemo` и вызывает предупреждение `The 'X' logical expression could make the dependencies change on every render`.

**2.3.** **ОБЯЗАТЕЛЬНО** использовать константы вне компонента или `useMemo` для стабилизации.

```typescript
// ✅ ПРАВИЛЬНО: Вариант 1 — константа вне компонента
const EMPTY_ARRAY: readonly string[] = [];

const MyComponent = () => {
  const watchedValue = useWatch({ control, name: "items" });
  
  const items = useMemo(
    () => watchedValue ?? EMPTY_ARRAY,
    [watchedValue]  // ✅ EMPTY_ARRAY стабилен
  );
};
```

```typescript
// ✅ ПРАВИЛЬНО: Вариант 2 — useMemo с defaultValue
const MyComponent = () => {
  const items: string[] = useWatch({
    control,
    name: "items",
    defaultValue: [],  // ✅ Не undefined → не нужен ?? []
  });
  
  // ✅ items гарантированно string[], не нужен оператор ??
};
```

```typescript
// ❌ НЕПРАВИЛЬНО
const MyComponent = () => {
  const watchedValue = useWatch({ control, name: "items" });
  
  const items = useMemo(
    () => watchedValue ?? [],  // ❌ [] создаётся на каждом рендере
    [watchedValue]
  );
  
  // ❌ React Compiler: 'items' logical expression could make dependencies change
};
```

#### 3. Не смешивать ручную и автоматическую мемоизацию

**3.1.** React Compiler анализирует код и **сам решает**, какие значения мемоизировать.

**3.2.** Если вы добавляете `useMemo` для значения, которое Compiler считает не нуждающимся в мемоизации, возникает конфликт.

**3.3.** **ПРАВИЛО ВЫБОРА:**

| Сценарий | Решение |
|----------|---------|
| Простое вычисление (фильтр, map) | **НЕ использовать** `useMemo` — довериться Compiler |
| Дорогое вычисление (сортировка 1000+ элементов) | Использовать `useMemo` + `eslint-disable react-hooks/preserve-manual-memoization` |
| Значение передаётся в другой компонент как проп | Использовать `useMemo` |
| Функция-обработчик события | Использовать `useCallback` |

```typescript
// ✅ ПРАВИЛЬНО: Доверяем Compiler для простых вычислений
const initialUserIds: string[] =
  !roleId || allUsers.length === 0
    ? []
    : allUsers
        .filter((u) => u.role_ids?.includes(roleId))
        .map((u) => u.id);
// ✅ React Compiler сам решит, нужно ли мемоизировать
```

```typescript
// ✅ ПРАВИЛЬНО: Явная мемоизация для дорогих операций
// eslint-disable-next-line react-hooks/preserve-manual-memoization
const initialUserIds = useMemo(() => {
  if (!roleId || allUsers.length === 0) return [];
  return allUsers
    .filter((u) => u.role_ids?.includes(roleId))
    .map((u) => u.id);
}, [roleId, allUsers]);
```

```typescript
// ❌ НЕПРАВИЛЬНО: Избыточная мемоизация
const userName = useMemo(() => user?.name, [user?.name]);
// ❌ Compiler: Existing memoization could not be preserved
// Причина: простое чтение свойства не нуждается в мемоизации
```

#### 4. Оборачивать все обработчики событий в `useCallback`

**4.1.** Функции, передаваемые как пропсы в дочерние компоненты или используемые в `useMemo`/`useEffect`, **ОБЯЗАТЕЛЬНО** оборачивать в `useCallback`.

**4.2.** Это стабилизирует ссылки и предотвращает лишние ре-рендеры дочерних компонентов.

**4.3.** Зависимости `useCallback` должны быть **примитивами** или **мемоизированными объектами**.

```typescript
// ✅ ПРАВИЛЬНО
const handleOpenChange = useCallback(
  (newOpen: boolean) => {
    if (newOpen && !open) {
      setSessionKey((prev) => prev + 1);
    }
    if (!newOpen) {
      reset(CREATE_DEFAULTS);
    }
    onOpenChange(newOpen);
  },
  [open, onOpenChange, reset]  // ✅ Все зависимости стабильны
);

const onSubmit = useCallback(
  async (data: FormData) => {
    await mutation.mutateAsync(data);
    toast({ title: "Сохранено" });
  },
  [mutation, toast]  // ✅ mutation и toast стабильны
);
```

```typescript
// ❌ НЕПРАВИЛЬНО
const onSubmit = async (data: FormData) => {
  await mutation.mutateAsync(data);
  toast({ title: "Сохранено" });
};

// ❌ При передаче в <form onSubmit={onSubmit}>:
// React Compiler: 'onSubmit' makes dependencies of useCallback change on every render
```

#### 5. Обходить проблему чтения `useRef` во время рендера

**5.1.** React Compiler запрещает чтение `ref.current` во время рендера, так как это нарушает детерминизм.

**5.2.** Если `handleSubmit` или другая функция читает `ref`, **ОБЯЗАТЕЛЬНО** обернуть вызов в `useCallback`.

```typescript
// ✅ ПРАВИЛЬНО
const handleFormSubmit = useCallback(
  (e: React.FormEvent<HTMLFormElement>) => {
    handleSubmit(onSubmit, onInvalid)(e);
  },
  [handleSubmit, onSubmit, onInvalid]
);

return (
  <form onSubmit={handleFormSubmit}>
    {/* ✅ handleFormSubmit стабилен, нет чтения ref во время рендера */}
  </form>
);
```

```typescript
// ❌ НЕПРАВИЛЬНО
return (
  <form onSubmit={handleSubmit(onSubmit, onInvalid)}>
    {/* ❌ React Compiler: Cannot access refs during render */}
  </form>
);
```

#### 6. Альтернатива: полное отключение React Compiler для файла

**6.1.** Если компонент слишком сложный и предупреждения не устраняются, можно **полностью отключить** React Compiler для файла.

**6.2.** Это делается через директиву в начале файла.

```typescript
// react-compiler-skip
import { useState, useMemo } from "react";
// ... остальной код компонента
```

**6.3.** **ПРЕДУПРЕЖДЕНИЕ:** При отключении Compiler компонент теряет автоматическую оптимизацию (30-50% медленнее). Используйте только как крайнюю меру.

### Полные примеры

#### Пример 1: Форма с `useWatch` и стабильными зависимостями

```typescript
import { useState, useMemo, useCallback } from "react";
import { useForm, Controller, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

const schema = z.object({
  name: z.string(),
  items: z.array(z.string()).optional(),
});

type FormData = z.infer<typeof schema>;

export const MyForm = ({ initialData, onSave }: Props) => {
  const { control, handleSubmit, reset } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", items: [] },
  });

  // ✅ useWatch вместо watch
  const items: string[] = useWatch({
    control,
    name: "items",
    defaultValue: [],  // ✅ Гарантированный string[]
  });

  // ✅ useMemo со стабильными зависимостями
  const hasChanges = useMemo(() => {
    const initial = initialData?.items || [];
    return JSON.stringify(initial) !== JSON.stringify(items);
  }, [initialData?.items, items]);  // ✅ items стабилен из useWatch

  // ✅ useCallback для обработчика
  const onSubmit = useCallback(
    async (data: FormData) => {
      await onSave(data);
      reset();
    },
    [onSave, reset]
  );

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {/* ... поля формы ... */}
      <button type="submit" disabled={!hasChanges}>
        Сохранить
      </button>
    </form>
  );
};
```

#### Пример 2: Дорогое вычисление с явной мемоизацией

```typescript
export const UsersList = ({ users, roleId }: Props) => {
  // ✅ Явная мемоизация для дорогой операции
  // eslint-disable-next-line react-hooks/preserve-manual-memoization
  const filteredUsers = useMemo(() => {
    return users
      .filter((u) => u.role_ids?.includes(roleId))
      .sort((a, b) => a.name.localeCompare(b.name));
  }, [users, roleId]);

  // ✅ Простое вычисление — доверяем Compiler
  const activeCount = filteredUsers.filter((u) => u.is_active).length;

  return (
    <div>
      <p>Найдено: {filteredUsers.length}, активных: {activeCount}</p>
      {/* ... рендер списка ... */}
    </div>
  );
};
```

### Обоснование

#### Почему возникает цикл предупреждений?

| Шаг | Действие | Результат |
|-----|----------|-----------|
| 1 | Добавляем `useMemo` для `initialUserIds` | Compiler: `Could not preserve existing memoization` |
| 2 | Убираем `useMemo` → используем `watch` | Compiler: `'watch' cannot be memoized safely` |
| 3 | Заменяем `watch` на `?? []` | Compiler: `Logical expression could make dependencies change` |
| 4 | Оборачиваем `?? []` в `useMemo` | Возвращаемся к шагу 1 |

**Решение:** использовать `useWatch` + `defaultValue` — это единственный подход, который:
- ✅ Даёт стабильный тип (не `undefined`)
- ✅ Не требует оператора `??`
- ✅ Совместим с React Compiler
- ✅ Не вызывает каскадных ре-рендеров

#### Почему `useWatch` лучше `watch`?

| Аспект | `watch()` | `useWatch()` |
|--------|-----------|--------------|
| **Тип возврата** | `T \| undefined` | `T` (при `defaultValue`) |
| **Мемоизация** | ❌ Не безопасна | ✅ Полностью безопасна |
| **Реактивность** | Вызывает ре-рендер при каждом изменении | Ре-рендер только при изменении конкретного поля |
| **Совместимость с Compiler** | ⚠️ Предупреждения | ✅ Полная |
| **Производительность** | Перерендер всей формы | Перерендер только подписанных компонентов |

#### Когда доверять Compiler, а когда мемоизировать вручную?

| Критерий | Доверять Compiler | Ручная мемоизация |
|----------|-------------------|---------------------|
| **Простые операции** | ✅ `user.name`, `items.length` | ❌ Избыточно |
| **Фильтрация/маппинг < 100 элементов** | ✅ Compiler справится | ❌ Избыточно |
| **Сортировка 1000+ элементов** | ⚠️ Может быть медленно | ✅ `useMemo` |
| **Передача в дочерний компонент** | ❌ Ре-рендер на каждый рендер | ✅ `useMemo` для объектов |
| **Функции-обработчики** | ❌ Новая функция на каждом рендере | ✅ `useCallback` |

### Чек-лист применения

Перед коммитом компонента с формами/списками проверьте:

- [ ] Используется `useWatch` вместо `watch` для значений формы в `useMemo`
- [ ] `useWatch` имеет `defaultValue` (не `undefined`)
- [ ] Нет операторов `?? []`, `|| {}` в зависимостях `useMemo`
- [ ] Все обработчики событий обёрнуты в `useCallback`
- [ ] Зависимости `useCallback` — примитивы или мемоизированные объекты
- [ ] Нет чтения `ref.current` во время рендера (обёрнуто в `useCallback`)
- [ ] Дорогие операции (>100 элементов) обёрнуты в `useMemo`
- [ ] Простые операции **НЕ** обёрнуты в `useMemo` (доверие Compiler)
- [ ] Если есть `eslint-disable react-hooks/preserve-manual-memoization`, добавлен комментарий с обоснованием
- [ ] React Compiler не выдаёт предупреждений при сборке (`npm run build`)

### Связь с другими правилами

| Правило | Связь |
|---------|-------|
| Frontend №37 (Синхронизация формы) | `useWatch` дополняет `reset` для реактивности |
| Frontend №41 (Общие требования к формам) | `useCallback` для обработчиков формы |
| Frontend №20 (Сброс формы) | `useWatch` работает с `defaultValues` из `CREATE_DEFAULTS` |
| Backend №36 (Безопасная обработка ошибок) | `useCallback` для `onError` мутаций |

### Когда применять это правило

**Обязательно для:**
- ✅ Форм с `react-hook-form` (EditRoleModal, EditUserModal, EditNoteModal)
- ✅ Страниц со списками и фильтрами (UsersPage, NotesPage)
- ✅ Компонентов с дорогими вычислениями (сортировка, группировка)
- ✅ Компонентов, передающих функции как пропсы

**Не обязательно для:**
- ❌ Простых презентационных компонентов без состояний
- ❌ Статических страниц без интерактивности

---

**Это правило обязательно для всех компонентов с формами и сложной логикой.** Любое отклонение (использование `watch` вместо `useWatch`, отсутствие `useCallback` для обработчиков) будет вызывать циклические предупреждения React Compiler и подлежит исправлению при код-ревью.