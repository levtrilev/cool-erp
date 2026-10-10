# Правило №27: Использование компонента `ReferenceSelect` для справочников

## 1. Область применения

Компонент `ReferenceSelect` является **единственным разрешённым способом** выбора значений из справочников (домены, организации, типы документов, пользователи и т.д.) во всех формах проекта.

---

## 2. Базовые требования

### 2.1. Запрет на ручной ввод UUID
**Категорически запрещён** `<Input>` для ввода или отображения UUID справочных значений. Всегда используйте `ReferenceSelect`.

```tsx
// ❌ ЗАПРЕЩЕНО:
<Input {...register("domain_id")} placeholder="UUID домена" />

// ✅ ПРАВИЛЬНО:
<Controller
  name="domain_id"
  control={control}
  render={({ field }) => (
    <ReferenceSelect
      fetchFn={...}
      queryKey={["domains"]}
      value={field.value}
      onValueChange={field.onChange}
      // ... остальные пропы
    />
  )}
/>
```

### 2.2. Обязательный паттерн адаптера в `fetchFn`
Ответ от Orval-функции **всегда** должен быть преобразован в формат `{ items, total }`. Это связано с тем, что Orval оборачивает ответы в `ApiResponse`, а `ReferenceSelect` ожидает плоскую структуру.

```tsx
// ✅ ПРАВИЛЬНО: Адаптер распаковывает ответ
fetchFn={async (params) => {
  const response = await getDomainsDomainsGet(params);
  return {
    items: response?.data?.items ?? [],
    total: response?.data?.total ?? 0,
  };
}}
```

### 2.3. Подмена ID для строковых идентификаторов
Если справочник использует строковый идентификатор вместо UUID (например, `doctype` — это строка `"invoices"`, а не UUID), его необходимо явно подменить в адаптере. Также **обязательно** добавить поле `name`, если его нет в схеме.

```tsx
// ✅ ПРАВИЛЬНО: Для строковых ID (например, doctype)
fetchFn={async (params) => {
  const response = await getDoctypesDoctypesGet(params);
  const items = (response?.data?.items ?? []).map((item) => ({
    ...item,
    id: item.doctype, // ✅ Подмена UUID на строковый код
    name: item.doctype_name || item.doctype, // ✅ Гарантированное наличие поля name
  }));
  return { items, total: response?.data?.total ?? 0 };
}}
```

---

## 3. Формат дополнительных колонок

Для отображения дополнительных колонок в выпадающем списке использовать массив объектов с ключом **`column`** (не `key`!).

```tsx
// ✅ ПРАВИЛЬНО:
columns={[
  { column: "description", label: "Описание" },
  { column: "domain_name", label: "Домен" }
]}

// ❌ НЕПРАВИЛЬНО:
columns={[
  { key: "description", label: "Описание" } // Ключ должен быть "column"!
]}
```

---

## 4. ✅ КРИТИЧЕСКИ ВАЖНО: Использование пропа `selectedLabel`

Для **мгновенного отображения** имеющегося значения в режиме редактирования **обязательно** передавать проп `selectedLabel`. Это гарантирует, что текстовая метка отобразится сразу же при открытии модалки, не дожидаясь завершения асинхронного запроса `fetchFn` и поиска элемента в массиве `items`.

### 4.1. Почему это важно
Без `selectedLabel` компонент `ReferenceSelect` при первом рендере видит `value` (UUID), но массив `items` ещё пуст (запрос не завершился). Компонент не может найти элемент с нужным `id` и отобразить его `name`. В результате поле остаётся пустым до завершения запроса, что создаёт плохой UX.

### 4.2. Как это работает
Проп `selectedLabel` явно указывает компоненту, какой текст показать в качестве выбранного значения **до того**, как завершится асинхронный запрос. Как только `fetchFn` завершается, компонент корректно подхватывает реальный элемент из списка для дальнейшей работы.

### 4.3. Пример использования

```tsx
// ✅ ПРАВИЛЬНО: selectedLabel гарантирует мгновенное отображение
<Controller
  name="domain_id"
  control={control}
  render={({ field }) => (
    <ReferenceSelect
      fetchFn={async (params) => {
        const response = await getDomainsDomainsGet(params);
        return {
          items: response?.data?.items ?? [],
          total: response?.data?.total ?? 0,
        };
      }}
      queryKey={["domains"]}
      value={field.value}
      onValueChange={field.onChange}
      placeholder="Выберите домен..."
      // 👇 КЛЮЧЕВОЙ ПРОП для мгновенного отображения при редактировании
      selectedLabel={initialData?.domain_name ?? "Выберите домен..."}
      limit={50}
      heading="Домены"
      columns={[{ column: "description", label: "Описание" }]}
    />
  )}
/>
```

### 4.4. Пример из EditUserModal (эталон)

```tsx
<Controller
  name="tenant_id"
  control={control}
  render={({ field }) => (
    <ReferenceSelect
      fetchFn={async (params) => {
        const response = await readTenantsTenantsGet(params);
        return {
          items: response?.items ?? [],
          total: response?.total ?? 0,
        };
      }}
      queryKey={["tenants", "active"]}
      value={field.value || ""}
      onValueChange={field.onChange}
      placeholder="Выберите организацию"
      selectedLabel={user?.tenant_name ?? "Выберите организацию"} // ✅ ЭТАЛОН
      heading="Выберите организацию"
      columns={[{ column: "description", label: "Описание" }]}
    />
  )}
/>
```

---

## 5. 🚫 ЗАПРЕЩЕНО: Манипуляции с кэшем для отображения Label

**Категорически запрещено** использовать `useEffect` с `queryClient.prefetchQuery` или `queryClient.setQueryData` исключительно для того, чтобы заставить `ReferenceSelect` показать название выбранного элемента при открытии модалки. Это антипаттерн, который решается корректно и декларативно **только через проп `selectedLabel`**.

### 5.1. Запрещённые антипаттерны

```tsx
// ❌ ЗАПРЕЩЕНО (Антипаттерн #1):
useEffect(() => {
  queryClient.prefetchQuery({
    queryKey: ["domains"],
    queryFn: async () => {
      const response = await getDomainsDomainsGet({ limit: 100, skip: 0 });
      return {
        items: response?.data?.items ?? [],
        total: response?.data?.total ?? 0,
      };
    },
  });
}, [queryClient]);

// ❌ ЗАПРЕЩЕНО (Антипаттерн #2):
const openEdit = (item: DoctypeResponseSchema) => {
  if (item.domain_id && item.domain_name) {
    queryClient.setQueryData(["domains"], {
      items: [{ id: item.domain_id, name: item.domain_name }],
      total: 1,
    });
  }
  setEditingDoctype(item);
  setIsModalOpen(true);
};
```

### 5.2. Почему это антипаттерн
- **Нарушение принципа единственной ответственности**: Страница списка не должна заботиться о том, как модальное окно отображает данные.
- **Скрытые зависимости**: Код становится хрупким и сложным для понимания.
- **Решение уже существует**: Проп `selectedLabel` решает проблему декларативно и элегантно.

---

## 6. Неизменяемость компонента

Проп `labelField` в компоненте **НЕ существует**. Прямое изменение исходного кода файла `ReferenceSelect.tsx` **запрещено**. Все адаптации данных (добавление поля `name`, маппинг `id`) должны происходить на уровне пропсов и функции `fetchFn` при вызове компонента.

```tsx
// ❌ ЗАПРЕЩЕНО: Пытаться использовать несуществующий проп
<ReferenceSelect
  labelField="domain_name" // Такого пропа нет!
  // ...
/>

// ✅ ПРАВИЛЬНО: Адаптировать данные в fetchFn
fetchFn={async (params) => {
  const response = await getDomainsDomainsGet(params);
  const items = (response?.data?.items ?? []).map((item) => ({
    ...item,
    name: item.domain_name, // ✅ Добавляем поле name
  }));
  return { items, total: response?.data?.total ?? 0 };
}}
```

---

## 7. Полный пример эталонного использования

```tsx
import { Controller } from "react-hook-form";
import { ReferenceSelect } from "@/lib/reusable/ReferenceSelect";
import { getDomainsDomainsGet } from "@/api/generated/domains/domains";

interface EditDoctypeModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData: DoctypeResponseSchema | null;
}

export const EditDoctypeModal = ({ open, onOpenChange, initialData }: EditDoctypeModalProps) => {
  const { control } = useForm<DoctypeFormData>({ /* ... */ });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <form>
          <Controller
            name="domain_id"
            control={control}
            render={({ field }) => (
              <ReferenceSelect
                // ✅ 1. Обязательный адаптер
                fetchFn={async (params) => {
                  const response = await getDomainsDomainsGet(params);
                  return {
                    items: response?.data?.items ?? [],
                    total: response?.data?.total ?? 0,
                  };
                }}
                // ✅ 2. Чистый ключ кэша
                queryKey={["domains"]}
                // ✅ 3. Значение из формы
                value={field.value}
                onValueChange={field.onChange}
                // ✅ 4. Placeholder для режима создания
                placeholder="Выберите домен..."
                // ✅ 5. КРИТИЧЕСКИ ВАЖНО: selectedLabel для режима редактирования
                selectedLabel={initialData?.domain_name ?? "Выберите домен..."}
                // ✅ 6. Дополнительные параметры
                limit={50}
                heading="Домены"
                // ✅ 7. Формат колонок с ключом "column"
                columns={[{ column: "description", label: "Описание" }]}
              />
            )}
          />
        </form>
      </DialogContent>
    </Dialog>
  );
};
```

---

## 8. Чек-лист для проверки

При использовании `ReferenceSelect` убедитесь, что:

- [ ] Используется `Controller` из `react-hook-form` (не прямой `register`)
- [ ] В `fetchFn` есть адаптер, возвращающий `{ items, total }`
- [ ] Для строковых ID выполнена подмена `id: item.code` в адаптере
- [ ] Поле `name` гарантированно присутствует в элементах (добавлено в адаптере, если нужно)
- [ ] В `columns` используется ключ `column`, а не `key`
- [ ] **Обязательно** передан проп `selectedLabel={initialData?.related_name ?? "Выберите..."}`
- [ ] **НЕ используются** `prefetchQuery` или `setQueryData` для решения проблемы отображения label
- [ ] Файл `ReferenceSelect.tsx` не модифицируется

---

## 9. Обоснование архитектурных решений

1. **Почему `selectedLabel`, а не prefetch?**
   - Декларативный подход: данные передаются явно через пропы
   - Нет скрытых зависимостей между компонентами
   - Нет лишних запросов к API
   - Мгновенное отображение без ожидания асинхронных операций

2. **Почему адаптер в `fetchFn`, а не изменение `ReferenceSelect`?**
   - Компонент остаётся универсальным и переиспользуемым
   - Логика адаптации данных остаётся в месте вызова, где есть контекст
   - Нет риска сломать другие места использования компонента

3. **Почему ключ `column`, а не `key`?**
   - `key` — это зарезервированное слово в React для списков
   - `column` более семантически точно описывает назначение поля

---

Это правило является **строгим стандартом** для всех справочников в проекте. Любые отклонения от него будут считаться нарушением архитектуры и должны быть исправлены.