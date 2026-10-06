# 📋 Правило №27: Использование компонента `ReferenceSelect` для справочников

Все поля выбора из справочников (один объект) **ОБЯЗАТЕЛЬНО** должны реализовываться через компонент `<ReferenceSelect>`. Использование `<Input>` для ручного ввода UUID или стандартных HTML `<select>` **КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО**.

Для согласования типов ответа бэкенда (`ApiResponse<PaginatedResponse<T>>`) и ожиданий компонента (`{ items: T[], total: number }`) **ОБЯЗАТЕЛЬНО** используется функция-адаптер внутри пропса `fetchFn`. Изменение кода самого компонента `ReferenceSelect.tsx` для обхода этой проблемы **ЗАПРЕЩЕНО**.

---

### 1. Обоснование (Почему это важно)

1. **Защита от ошибок ввода:** Пользователь физически не может ввести несуществующий или невалидный UUID.
2. **Изоляция преобразований:** Адаптер в `fetchFn` чётко разделяет ответственность: бэкенд возвращает свой контракт (Правило №4), компонент получает свой, а мостик между ними находится в месте вызова.
3. **Неприкосновенность базовых компонентов:** Отлаженный `ReferenceSelect.tsx` остаётся стабильным и не обрастает специфичной логикой под конкретные ответы API.
4. **Единый UX:** Поиск, пагинация и отображение дополнительных колонок работают одинаково предсказуемо во всём приложении.

---

### 2. Обязательная сигнатура компонента

```typescript
interface ReferenceItem {
  id: string;
  [key: string]: any;
}

interface ReferenceSelectProps<T extends ReferenceItem> {
  fetchFn: (params: { skip?: number; limit?: number; search?: string }) => Promise<{ items: T[]; total: number }>;
  queryKey: string[];
  value: string;
  onValueChange: (value: string) => void;
  placeholder?: string;
  disabled?: boolean;
  limit?: number;
  heading?: string;
  // ✅ ВАЖНО: используется ключ 'column', а не 'key' или 'labelField'
  columns?: Array<{ column: keyof T; label: string }>; 
}
```

---

### 3. Обязательный шаблон вызова (Золотой стандарт)

```tsx
import { Controller } from "react-hook-form";
import { ReferenceSelect } from "@/lib/reusable/ReferenceSelect";
import { getDomainsDomainsGet } from "@/api/generated/domains/domains"; // Импортируем функцию, а не хук

// ... внутри формы ...

<div className="space-y-2">
  <label className="text-sm font-medium">Домен</label>
  <Controller
    name="domain_id"
    control={control}
    render={({ field }) => (
      <ReferenceSelect
        // ✅ АДАПТЕР: Преобразуем ApiResponse в формат, ожидаемый ReferenceSelect
        fetchFn={async (params) => {
          const response = await getDomainsDomainsGet(params);
          // Распаковываем ApiResponse -> { items, total }
          return {
            items: response?.data?.items ?? [],
            total: response?.data?.total ?? 0,
          };
        }}
        queryKey={["domains"]}
        value={field.value}
        onValueChange={field.onChange}
        placeholder="Выберите домен..."
        limit={50}
        heading="Домены"
        columns={[
          { column: "description", label: "Описание" }, // ✅ Используем 'column', а не 'key'
        ]}
      />
    )}
  />
  {errors.domain_id && (
    <p className="text-xs text-destructive">{errors.domain_id.message}</p>
  )}
</div>
```

---

### 4. Примеры для разных справочников

#### Пример А: Справочник с дополнительными колонками (Domain)
```tsx
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
      limit={50}
      heading="Домены"
      columns={[
        { column: "description", label: "Описание" },
      ]}
    />
  )}
/>
```

#### Пример Б: Простой справочник (Tenant)
```tsx
<Controller
  name="tenant_id"
  control={control}
  render={({ field }) => (
    <ReferenceSelect
      fetchFn={async (params) => {
        const response = await getTenantsTenantsGet(params);
        return {
          items: response?.data?.items ?? [],
          total: response?.data?.total ?? 0,
        };
      }}
      queryKey={["tenants"]}
      value={field.value}
      onValueChange={field.onChange}
      placeholder="Выберите организацию..."
      heading="Организации"
      // columns можно не указывать, если достаточно основного поля (обычно name)
    />
  )}
/>
```

---

### 5. Требования к справочным API

Чтобы `ReferenceSelect` работал корректно, эндпоинт справочника **ОБЯЗАТЕЛЬНО** должен:
1. Возвращать `ApiResponse<PaginatedResponse<T>>` (Правило №4).
2. Поддерживать параметры `skip`, `limit`, `search`.
3. Иметь поле `id` в схеме ответа (для `value`).
4. Иметь хотя бы одно текстовое поле (например, `name`), которое компонент использует как основной заголовок элемента списка.

---

### 6. Чек-лист для разработчика

При добавлении поля выбора из справочника проверьте:

**Структура:**
- [ ] Используется ли `<Controller>` из `react-hook-form`?
- [ ] Импортирована ли **функция** запроса из Orval (например, `getDomainsDomainsGet`), а не хук?
- [ ] Используется ли **функция-адаптер** внутри `fetchFn` для возврата `{ items, total }`?
- [ ] В адаптере корректно используется цепочка `response?.data?.items`?

**Пропсы компонента:**
- [ ] Указан ли уникальный `queryKey` для кэша React Query?
- [ ] `value` привязан к `field.value`, а `onValueChange` к `field.onChange`?
- [ ] Указан ли осмысленный `placeholder` и `heading`?
- [ ] Если используются доп. колонки, указан ли массив `columns` с ключом **`column`** (а не `key` или `field`)?
- [ ] **ОТСУТСТВУЕТ** ли несуществующий проп `labelField`?

**Запреты:**
- [ ] Отсутствуют ли ручные `<Input>` для ввода UUID?
- [ ] Отсутствуют ли попытки изменить код файла `ReferenceSelect.tsx`?

---

### 7. Типичные ошибки и их исправление

| Ошибка | Исправление |
| :--- | :--- |
| Использование `labelField="name"` | **Удалить.** Компонент автоматически использует поле `name` (или аналогичное) как основное. Для доп. полей используйте `columns`. |
| Использование `key: "description"` в `columns` | **Исправить на** `column: "description"`. Это строгое требование интерфейса компонента. |
| `fetchFn={(params) => getDomainsGet(params)}` напрямую | **Обернуть в адаптер:** `async (params) => { const r = await getDomainsGet(params); return { items: r?.data?.items ?? [], total: r?.data?.total ?? 0 }; }` |
| Импорт хука `useGetDomainsGet` вместо функции | Импортировать именно функцию запроса: `import { getDomainsGet } from "..."` |

---

### 8. Связь с другими правилами

- **Правило №4 (Orval-совместимость):** Адаптер в `fetchFn` преобразует стандартный `ApiResponse` в формат, ожидаемый компонентом.
- **Правило №1 (Чистая архитектура):** Компонент не знает о деталях API — вся логика преобразования находится в месте вызова.
- **Правило №21 (Суффикс Schema):** Имена полей формы (`domain_id`) совпадают с именами полей в Pydantic-схемах бэкенда.

---

Следование этому правилу гарантирует, что все справочники во всём проекте выглядят и работают единообразно, код вызова самодокументируем, а TypeScript не выдаёт ошибок типизации.