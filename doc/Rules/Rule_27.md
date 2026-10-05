# Правило №27: Обязательное использование компонента `ReferenceSelect` для справочников

Все выпадающие списки, предназначенные для выбора значения из справочника (тенанты, пользователи, разделы, типы документов, контрагенты и т.д.), **ОБЯЗАТЕЛЬНО** должны реализовываться через кастомный компонент `ReferenceSelect`.

Использование стандартного компонента `<Select>` из `shadcn/ui` для справочников **КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО**.

---

### 1. Обоснование правила (Почему это важно)

Стандартный `<Select>` из `shadcn/ui` рендерит **все** доступные опции в DOM одновременно. Если в справочнике 10 000 записей, браузер зависнет, а сетевой запрос загрузит мегабайты данных. 
`ReferenceSelect` решает эту проблему, загружая данные **по требованию** (при открытии или вводе текста) с сервера, используя пагинацию и поиск.

---

### 2. Обязательные требования к реализации

#### 2.1. Серверная пагинация и поиск
* Компонент должен отправлять запросы на бэкенд с параметрами `search` и `skip/limit`.
* Фильтрация списка должна происходить **на стороне сервера**, а не в памяти браузера.

#### 2.2. Интеграция с React Hook Form
* Компонент **ОБЯЗАТЕЛЬНО** должен оборачиваться в `<Controller>` из `react-hook-form`.
* Запрещено ручное управление состоянием (`useState`) для значения справочника, если форма управляется через `react-hook-form`.

#### 2.3. Отображение метки в режиме редактирования (`selectedLabel`)
При открытии модалки редактирования бэкенд часто возвращает только ID связанной сущности (например, `tenant_id: "uuid-..."`). Чтобы пользователь сразу видел название, а не пустое поле или ID, **ОБЯЗАТЕЛЬНО** передавать проп `selectedLabel`.

#### 2.4. Исключение: Статические списки
Стандартный `<Select>` из `shadcn/ui` **разрешен** только для статических, жестко закодированных (hardcoded) списков, которые никогда не меняются и содержат не более 10-15 элементов (например, выбор статуса: "Черновик", "Активен", "Удален" или выбор булевых значений).

---

### 3. Примеры кода

#### ✅ ПРАВИЛЬНО: Создание новой записии (Create)
```tsx
import { Controller } from "react-hook-form";
import { ReferenceSelect } from "@/lib/reusable/ReferenceSelect";

// ... внутри формы создания ...
<div className="space-y-2">
  <label className="text-sm font-medium">Организация</label>
  <Controller
    name="tenant_id"
    control={control}
    rules={{ required: "Организация обязательна" }}
    render={({ field, fieldState }) => (
      <>
        <ReferenceSelect
          endpoint="/api/v1/tenants" // Эндпоинт справочника
          value={field.value}
          onChange={field.onChange}
          placeholder="Выберите организацию..."
          searchPlaceholder="Поиск по названию..."
        />
        {fieldState.error && (
          <p className="text-xs text-destructive">{fieldState.error.message}</p>
        )}
      </>
    )}
  />
</div>
```

#### ✅ ПРАВИЛЬНО: Редактирование существующей записии (Edit)
```tsx
// ... внутри модалки редактирования, где editingItem содержит данные ...
<div className="space-y-2">
  <label className="text-sm font-medium">Организация</label>
  <Controller
    name="tenant_id"
    control={control}
    render={({ field }) => (
      <ReferenceSelect
        endpoint="/api/v1/tenants"
        value={field.value}
        onChange={field.onChange}
        // ✅ КРИТИЧЕСКИ ВАЖНО: Передаем текущее название, чтобы оно отобразилось сразу
        selectedLabel={editingItem.tenant_name} 
        placeholder="Выберите организацию..."
      />
    )}
  />
</div>
```

#### ❌ НЕПРАВИЛЬНО: Использование стандартного Select для справочника
```tsx
// ❌ ГРУБОЕ НАРУШЕНИЕ ПРАВИЛА №27
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

// ... внутри формы ...
<Select onValueChange={(val) => setValue("tenant_id", val)} value={watch("tenant_id")}>
  <SelectTrigger>
    <SelectValue placeholder="Выберите организацию" />
  </SelectTrigger>
  <SelectContent>
    {/* ❌ Загружает все 10,000 организаций в DOM, вызывает лаги */}
    {allTenants.map((t) => (
      <SelectItem key={t.id} value={t.id}>{t.name}</SelectItem>
    ))}
  </SelectContent>
</Select>
```

#### ✅ ДОПУСТИМО: Использование стандартного Select для СТАТИЧЕСКОГО списка
```tsx
// ✅ РАЗРЕШЕНО: Статусы не меняются, их всего 3 штуки
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

<Select onValueChange={(val) => setValue("status", val)} value={watch("status")}>
  <SelectTrigger>
    <SelectValue placeholder="Выберите статус" />
  </SelectTrigger>
  <SelectContent>
    <SelectItem value="draft">Черновик</SelectItem>
    <SelectItem value="active">Активен</SelectItem>
    <SelectItem value="deleted">Удален</SelectItem>
  </SelectContent>
</Select>
```

---

### 4. Чек-лист для разработчика

При добавлении выпадающего списка в форму проверьте:
- [ ] Это справочник, данные которого хранятся в БД?
- [ ] Используется компонент `ReferenceSelect`?
- [ ] Компонент обернут в `<Controller>` (если форма на RHF)?
- [ ] Если это форма редактирования, передан ли проп `selectedLabel`?
- [ ] Отсутствует ли импорт `Select` из `@/components/ui/select` для этого конкретного поля?

Следование этому правилу гарантирует высокую производительность фронтенда даже при работе с огромными справочниками и обеспечивает единый UX поиска и выбора записей во всем приложении.