# 📋 Правило №34: Использование Switch (переключателей) с React Hook Form

Все переключатели (Switch/Toggle) в формах **ОБЯЗАТЕЛЬНО** должны реализовываться через компонент `Controller` из `react-hook-form` с прямой привязкой `field.value` и `field.onChange`, дополненной визуальной обратной связью через `Label`.

**КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО:**
* Использовать `useState` для управления состоянием переключателя внутри формы.
* Использовать сложные операторы (`??`, `!!`, `Boolean()`) внутри `checked`, если схема и `defaultValues` настроены корректно.
* Оставлять переключатель без текстовой/визуальной подписи, отражающей его текущее состояние.

---

### 1. Обоснование (Почему это важно)

1. **Надежность Radix UI:** Компонент `Switch` из `shadcn/ui` (построенный на Radix) требует строгого типа `boolean` для пропа `checked`. Прямая передача `field.value` (при корректных `defaultValues`) гарантирует отсутствие `undefined` или объектов событий, которые "замораживают" переключатель.
2. **Единообразие UX:** Пользователь должен мгновенно считывать состояние переключателя не только по положению ползунка, но и по цвету и иконке в подписи.
3. **Чистота кода:** Паттерн `checked={field.value}` + `onCheckedChange={field.onChange}` является каноническим для `react-hook-form` и не требует написания обёрток или кастомных обработчиков.
4. **Типобезопасность:** При правильной настройке Zod-схемы и `defaultValues` тип `field.value` выводится как `boolean`, что исключает ошибки TypeScript.

---

### 2. Обязательный шаблон реализации

```tsx
import { Controller } from "react-hook-form";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { CheckCircle2, PauseCircle } from "lucide-react";

// ... внутри компонента формы ...

<div className="mt-0">
  <Controller
    name="имя_поля" // Должно точно совпадать с ключом в defaultValues и схеме
    control={control}
    render={({ field }) => (
      <>
        <Switch
          id="имя_поля"
          checked={field.value}          // ✅ Прямая передача boolean
          onCheckedChange={field.onChange} // ✅ Прямая передача обработчика
        />
        <Label 
          htmlFor="имя_поля" 
          className={`flex items-center gap-2 cursor-pointer font-medium transition-colors ${
            field.value 
              ? "text-green-600 dark:text-green-400" // ✅ Цвет для true
              : "text-red-500 dark:text-red-400"     // ✅ Цвет для false
          }`}
        >
          {field.value ? (
            <>
              <CheckCircle2 className="h-4 w-4" />
              Текст активного состояния
            </>
          ) : (
            <>
              <PauseCircle className="h-4 w-4" />
              Текст неактивного состояния
            </>
          )}
        </Label>
      </>
    )}
  />
</div>
```

---

### 3. Требования к схеме и инициализации

Чтобы `field.value` гарантированно был `boolean`, необходимо:

#### 3.1. В Zod-схеме
Использовать `.optional()` (для совместимости с Orval), но **НЕ** использовать `.default()` внутри самой схемы, чтобы не ломать типизацию `Resolver`:
```typescript
is_active: z.boolean().optional(),
```

#### 3.2. В `useForm`
Явно задать `defaultValues`:
```typescript
defaultValues: {
  // ...
  is_active: true, // ✅ Гарантирует, что field.value изначально boolean
}
```

#### 3.3. При редактировании (`reset`)
Использовать оператор `??` для страховки от `null` с бэкенда:
```typescript
reset({
  // ...
  is_active: item.is_active ?? true,
})
```

---

### 4. Примеры кода

#### ✅ ПРАВИЛЬНО: Переключатель статуса организации

```tsx
<div className="mt-0">
  <Controller
    name="active"
    control={control}
    render={({ field }) => (
      <>
        <Switch
          id="active"
          checked={field.value}
          onCheckedChange={field.onChange}
        />
        <Label 
          htmlFor="active" 
          className={`flex items-center gap-2 cursor-pointer font-medium transition-colors ${
            field.value 
              ? "text-green-600 dark:text-green-400" 
              : "text-red-500 dark:text-red-400"
          }`}
        >
          {field.value ? (
            <>
              <CheckCircle2 className="h-4 w-4" />
              Организация активна
            </>
          ) : (
            <>
              <PauseCircle className="h-4 w-4" />
              Организация приостановлена
            </>
          )}
        </Label>
      </>
    )}
  />
</div>
```

#### ✅ ПРАВИЛЬНО: Переключатель активности типа документа

```tsx
<div className="mt-0">
  <Controller
    name="is_active"
    control={control}
    render={({ field }) => (
      <>
        <Switch
          id="is_active"
          checked={field.value}
          onCheckedChange={field.onChange}
        />
        <Label 
          htmlFor="is_active" 
          className={`flex items-center gap-2 cursor-pointer font-medium transition-colors ${
            field.value 
              ? "text-green-600 dark:text-green-400" 
              : "text-red-500 dark:text-red-400"
          }`}
        >
          {field.value ? (
            <>
              <CheckCircle2 className="h-4 w-4" />
              Активен
            </>
          ) : (
            <>
              <PauseCircle className="h-4 w-4" />
              Неактивен
            </>
          )}
        </Label>
      </>
    )}
  />
</div>
```

#### ❌ НЕПРАВИЛЬНО: Использование `useState`

```tsx
// ❌ ГРУБОЕ НАРУШЕНИЕ ПРАВИЛА №34
const [isActive, setIsActive] = useState(true);

<Switch
  checked={isActive}
  onCheckedChange={setIsActive}
/>
// 💥 Состояние не связано с формой! При отправке в payload уйдёт undefined.
```

#### ❌ НЕПРАВИЛЬНО: Использование операторов преобразования

```tsx
// ❌ ОШИБКА: Избыточные операторы преобразования
<Switch
  checked={Boolean(field.value)}      // ❌ Избыточно
  onCheckedChange={(v) => field.onChange(Boolean(v))}  // ❌ Избыточно
/>
```

#### ❌ НЕПРАВИЛЬНО: Отсутствие визуальной подписи

```tsx
// ❌ ОШИБКА: Переключатель без понятной подписи
<Switch
  id="is_active"
  checked={field.value}
  onCheckedChange={field.onChange}
/>
// 💥 Пользователь не понимает, что именно он переключает
```

---

### 5. Нюансы и лучшие практики

#### 5.1. Именование полей
* Используйте snake_case для полей формы: `is_active`, `is_published`, `is_visible`.
* Имя поля должно точно совпадать с именем поля в Pydantic-схеме бэкенда.

#### 5.2. Иконки и цвета
* **Зелёный + `CheckCircle2`** — для активного/включённого состояния.
* **Красный + `PauseCircle`** (или `XCircle`) — для неактивного/выключенного состояния.
* Используйте классы `dark:text-green-400` и `dark:text-red-400` для поддержки тёмной темы.

#### 5.3. Доступность (a11y)
* **Обязательно** используйте `htmlFor` в `Label`, совпадающий с `id` в `Switch`.
* Это позволяет кликать по тексту для переключения состояния.
* Это также необходимо для скринридеров.

#### 5.4. Множественные переключатели
Если в форме несколько переключателей, каждый должен иметь **уникальный `id`**:
```tsx
<Switch id="is_active" ... />
<Switch id="is_featured" ... />
<Switch id="is_archived" ... />
```

---

### 6. Связь с другими правилами

* **Правило №1 (Чистая архитектура):** Состояние формы хранится в `react-hook-form`, а не в локальных `useState`.
* **Правило №4 (Orval-совместимость):** Имена полей формы совпадают с именами полей в Pydantic-схемах бэкенда.
* **Правило №21 (Суффикс Schema):** Поля формы соответствуют полям `CreateSchema` и `UpdateSchema`.
* **Правило №22 (Структура состояний):** Переключатели — часть единой структуры состояний формы.

---

### 7. Чек-лист для разработчика

При добавлении любого переключателя в форму проверьте:

**Структура:**
- [ ] Используется ли `Controller` из `react-hook-form`?
- [ ] Имя поля (`name`) точно совпадает с ключом в `defaultValues` и Zod-схеме?
- [ ] Проп `checked` равен в точности `field.value` (без `!!`, `??` или `Boolean()`)?
- [ ] Проп `onCheckedChange` равен в точности `field.onChange`?

**Визуализация:**
- [ ] Рядом с `Switch` есть `Label` с `htmlFor`, совпадающим с `id` переключателя?
- [ ] `Label` меняет цвет в зависимости от `field.value`?
- [ ] `Label` содержит иконку (`CheckCircle2` / `PauseCircle`), отражающую состояние?
- [ ] Поддержка тёмной темы (`dark:text-*`) реализована?

**Типизация:**
- [ ] В Zod-схеме поле объявлено как `z.boolean().optional()`?
- [ ] В `defaultValues` формы задано начальное булево значение для этого поля?
- [ ] При редактировании используется `item.field ?? defaultValue` для страховки?
- [ ] TypeScript не выдаёт ошибок типизации?

**Доступность:**
- [ ] `id` в `Switch` уникален в пределах формы?
- [ ] По переключателю можно кликать с клавиатуры (Tab + Space)?

---

### 8. Типичные ошибки и их исправление

| Ошибка | Исправление |
| :--- | :--- |
| Переключатель "зависает" и не кликается | Убрать `!!`, `??`, `Boolean()` из `checked`. Использовать `field.value` напрямую |
| В payload уходит `undefined` | Добавить `defaultValues: { field_name: true }` в `useForm` |
| Ошибка TypeScript `Type 'undefined' is not assignable to type 'boolean'` | Использовать `.optional()` в Zod-схеме, а не `.default()` |
| Клик по тексту не переключает | Добавить `htmlFor` в `Label`, совпадающий с `id` в `Switch` |
| Состояние не сохраняется при отправке | Убедиться, что `name` в `Controller` совпадает с ключом в схеме |
| Переключатель работает, но без визуальной обратной связи | Добавить `Label` с иконками и цветами |

---

### 9. Размещение в структуре правил

Правило №34 добавляется в **ЧАСТЬ 2. FRONTEND**, после Правила №33.

---

Следование этому правилу гарантирует, что:
✅ Все переключатели во всём проекте работают предсказуемо и единообразно
✅ Пользователь мгновенно считывает состояние переключателя по цвету и иконке
✅ Код остаётся чистым и типобезопасным
✅ Доступность (a11y) соблюдается на уровне стандарта
✅ Отсутствуют "зависающие" переключатели из-за некорректной типизации

Это правило работает в связке с Правилами №1 (Чистая архитектура), №4 (Orval-совместимость), №21 (Схемы) и №22 (Структура состояний), формируя единый стандарт работы с формами в проекте Cool ERP.