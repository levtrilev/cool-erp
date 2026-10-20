# Правило №41: Общие требования к формам и уведомлениям на фронтенде

**Суть:** Все формы и пользовательские уведомления на фронтенде обязаны следовать единому технологическому стандарту: управление формами через `react-hook-form`, валидация через `zodResolver` с Zod-схемами, сложные поля через `<Controller>`, уведомления через `useToast()` из `shadcn/ui`. Запрещены «голые» `useState` для форм, ручная валидация, нативные `alert()`/`confirm()`/`console.log()` для пользователя и самописные компоненты уведомлений.

Правило является обобщающим и устанавливает базовый стандарт, на который ссылаются специализированные правила (№12, №20, №22, №27, №34, №35, №36, №37, №38, №39).

---

## Строгие требования

### 1. Управление формами

1.1. Все формы (создание, редактирование, фильтры) обязаны использовать `useForm()` из `react-hook-form`.

1.2. Валидация обязательно выполняется через `zodResolver` из `@hookform/resolvers/zod` с Zod-схемой.

1.3. Схема валидации объявляется через `z.object({...})` и экспортируется как отдельная константа (`noteFormSchema`, `roleSchema` и т.д.).

1.4. Тип формы выводится из схемы: `type FormData = z.infer<typeof schema>`.

1.5. `defaultValues` формы объявляются как константа `CREATE_DEFAULTS` вне компонента или в самом его начале (детали — Правило №20).

### 2. Использование `<Controller>` и `register`

2.1. Для полей, которые **не являются** нативными HTML-элементами с поддержкой `onChange`/`value` (справочники `ReferenceSelect`, переключатели `Switch`, `Select`, `Textarea` с кастомной логикой, массивы тегов), обязателен `<Controller>` из `react-hook-form`.

2.2. В проекте устоялся паттерн использования `<Controller>` для **всех** полей формы, включая простые `<Input>`. Это обеспечивает единообразие кода и упрощает рефакторинг.

2.3. Запрещено смешивать подходы в одной форме (часть полей через `register`, часть через `Controller`), если это не обосновано спецификой поля.

### 3. Отображение ошибок валидации

3.1. Ошибки валидации обязаны отображаться **под соответствующим полем**.

3.2. Для отображения используется `<p className="text-xs text-destructive">` с текстом `errors.{fieldName}.message`.

3.3. Проверка наличия ошибки выполняется через `&&`: `{errors.name && <p>...</p>}`.

### 4. Состояние загрузки формы

4.1. Кнопка отправки формы обязана быть заблокирована во время отправки через `disabled={isSubmitting}` из `formState`.

4.2. При блокировке рекомендуется отображать иконку загрузки `<Loader2 className="animate-spin" />`.

4.3. Текст кнопки может меняться в зависимости от состояния (например, «Сохранение...» / «Сохранить»).

### 5. Уведомления пользователю

5.1. Все уведомления пользователю обязаны использовать `useToast()` из `@/components/ui/use-toast` (shadcn/ui).

5.2. Запрещены:
- Нативные `alert()`, `confirm()`, `prompt()`
- `console.log()` / `console.error()` для отображения информации пользователю
- Самописные компоненты уведомлений (кастомные `<div>` с анимацией)
- Сторонние библиотеки уведомлений (react-toastify, notistack и т.д.)

5.3. Для ошибок используется `variant: "destructive"`.

5.4. Для успешных операций используется стандартный вариант без `variant`.

5.5. Каждое уведомление обязано иметь `title` и (при необходимости) `description`.

5.6. При ошибке из блока `catch`/`onError` применяется безопасная обработка через `unknown` (Правило №36).

### 6. Сброс формы

6.1. После успешной отправки формы вызывается `reset(CREATE_DEFAULTS)` (детали — Правило №20).

6.2. При закрытии модалки вызывается `reset(CREATE_DEFAULTS)` (детали — Правило №20).

6.3. При открытии модалки в режиме редактирования вызывается `reset({...})` с данными из `initialData` (детали — Правило №37).

---

## ✅ ПРАВИЛЬНО

### Пример 1: Полная форма создания с валидацией

```tsx
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/use-toast";

// ✅ Zod-схема валидации
const roleSchema = z.object({
  name: z.string().min(3, "Минимум 3 символа").max(100),
  description: z.string().optional(),
  tenant_id: z.string().min(1, "Выберите организацию"),
});

type RoleFormData = z.infer<typeof roleSchema>;

// ✅ Константа вне компонента
const CREATE_DEFAULTS: RoleFormData = {
  name: "",
  description: "",
  tenant_id: "",
};

export const CreateRoleModal = ({ open, onOpenChange, onRoleSaved }) => {
  const { toast } = useToast(); // ✅ Toast из shadcn/ui

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<RoleFormData>({
    resolver: zodResolver(roleSchema), // ✅ Валидация через Zod
    defaultValues: CREATE_DEFAULTS,
  });

  const createMutation = useCreateRoleRolesPost(); // ✅ Orval-хук (Правило №9)

  const onSubmit = async (formData: RoleFormData) => {
    try {
      await createMutation.mutateAsync({ data: formData });
      toast({ title: "Роль успешно создана" }); // ✅ Уведомление через useToast
      reset(CREATE_DEFAULTS); // ✅ Сброс формы
      onOpenChange(false);
      onRoleSaved();
    } catch (error: unknown) {
      // ✅ Безопасная обработка ошибок (Правило №36)
      const err = error as { response?: { data?: { detail?: string } } };
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: err?.response?.data?.detail || "Не удалось создать роль",
      });
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" id="role-form">
      {/* ✅ Поле через Controller (единый паттерн проекта) */}
      <div className="space-y-2">
        <Label htmlFor="name">
          Название <span className="text-destructive">*</span>
        </Label>
        <Controller
          name="name"
          control={control}
          render={({ field }) => (
            <Input
              id="name"
              {...field}
              placeholder="Введите название роли"
            />
          )}
        />
        {/* ✅ Ошибка валидации под полем */}
        {errors.name && <p className="text-xs text-destructive">{errors.name.message}</p>}
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Описание</Label>
        <Controller
          name="description"
          control={control}
          render={({ field }) => (
            <Input
              id="description"
              {...field}
              value={field.value ?? ""}
              placeholder="Введите описание"
            />
          )}
        />
        {errors.description && <p className="text-xs text-destructive">{errors.description.message}</p>}
      </div>

      <Button
        type="submit"
        form="role-form"
        disabled={isSubmitting}  // ✅ Блокировка во время отправки
      >
        {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {isSubmitting ? "Создание..." : "Создать"}
      </Button>
    </form>
  );
};
```

### Пример 2: Уведомления через `useToast()`

```tsx
const { toast } = useToast();

// ✅ Успешное уведомление
toast({ title: "Роль создана" });

// ✅ Уведомление с описанием
toast({
  title: "Роль создана",
  description: "Теперь назначьте её пользователям",
});

// ✅ Уведомление об ошибке
toast({
  variant: "destructive",
  title: "Ошибка",
  description: "Не удалось создать роль",
});

// ✅ Уведомление с действием (кнопкой) — Правило №18
toast({
  title: "Сохранено",
  description: "Запись находится на странице 5",
  action: (
    <Button variant="outline" size="sm" onClick={() => setPage(5)}>
      Перейти
    </Button>
  ),
});

// ✅ Безопасная обработка ошибок (Правило №36)
} catch (error: unknown) {
  const err = error as { response?: { data?: { detail?: string } } };
  toast({
    variant: "destructive",
    title: "Ошибка сохранения",
    description: err?.response?.data?.detail || "Не удалось выполнить действие",
  });
}
```

### Пример 3: Сложное поле через `<Controller>` (справочник)

```tsx
{/* ✅ Справочник через Controller с актуальной сигнатурой (Правило №27) */}
<Controller
  name="tenant_id"
  control={control}
  render={({ field }) => (
    <>
      <ReferenceSelect
        fetchFn={async (params) => {
          const response = await getTenantsTenantsGet(params);
          return {
            items: response?.data?.items ?? [],
            total: response?.data?.total ?? 0,
          };
        }}
        queryKey={["tenants", "active"]}
        value={field.value}
        onValueChange={field.onChange}
        placeholder="Выберите организацию..."
        selectedLabel={initialData?.tenant_name ?? "Выберите организацию..."}
        heading="Организации"
        limit={50}
        columns={[{ column: "description", label: "Описание" }]}
      />
      {errors.tenant_id && (
        <p className="text-xs text-destructive">{errors.tenant_id.message}</p>
      )}
    </>
  )}
/>
```

---

## ❌ НЕПРАВИЛЬНО

```tsx
{/* ❌ ОШИБКА 1: Использование "голых" useState для формы */}
export const CreateRoleModal = () => {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [tenantId, setTenantId] = useState("");
  const [error, setError] = useState("");

  const handleSubmit = () => {
    if (name.length < 3) {
      setError("Минимум 3 символа"); // ❌ Ручная валидация
      return;
    }
    // ... отправка
  };

  return (
    <div>
      <Input value={name} onChange={(e) => setName(e.target.value)} />
      {error && <p>{error}</p>}
    </div>
  );
};
// Почему плохо: нет типобезопасности, ручная валидация, дублирование кода,
// невозможно переиспользовать логику.

{/* ❌ ОШИБКА 2: Использование alert() для пользователя */}
const handleSave = async () => {
  await createMutation.mutateAsync({ data });
  alert("Роль создана!"); // ❌ Нативное уведомление
};
// Почему плохо: блокирует UI, выглядит чужеродно, не поддерживает тёмную тему.

{/* ❌ ОШИБКА 3: Самописный компонент уведомлений */}
const [showToast, setShowToast] = useState(false);
// ... кастомный <div> с анимацией
// Почему плохо: дублирует функциональность, не поддерживает тёмную тему,
// требует самостоятельного управления жизненным циклом.

{/* ❌ ОШИБКА 4: Использование console для пользователя */}
const handleSave = async () => {
  try {
    await createMutation.mutateAsync({ data });
    console.log("Успешно сохранено"); // ❌ Пользователь этого не увидит
  } catch (error) {
    console.error("Ошибка сохранения", error); // ❌ Пользователь этого не увидит
  }
};

{/* ❌ ОШИБКА 5: Использование any в обработке ошибок */}
} catch (error: any) {
  toast({ description: error.response?.data?.detail }); // ❌ Нарушение Правила №36
}

{/* ❌ ОШИБКА 6: Отсутствие блокировки кнопки во время отправки */}
<Button type="submit">Сохранить</Button>
// ❌ Пользователь может кликнуть дважды → дублирующийся запрос

{/* ❌ ОШИБКА 7: Ошибки валидации не отображаются под полями */}
<Controller
  name="name"
  control={control}
  render={({ field }) => <Input {...field} />}
/>
// ❌ Пользователь не видит, почему форма не отправляется

{/* ❌ ОШИБКА 8: Смешение register и Controller без обоснования */}
<Input {...register("name")} />                    {/* ❌ Через register */}
<Controller name="tenant_id" control={control} />  {/* Через Controller */}
{/* Нарушение единообразия: в проекте устоялся паттерн использования <Controller> для всех полей */}

{/* ❌ ОШИБКА 9: Устаревшая сигнатура ReferenceSelect */}
<ReferenceSelect
  endpoint="/api/v1/tenants"       {/* ❌ Такого пропа нет */}
  value={field.value}
  onChange={field.onChange}         {/* ❌ Правильно: onValueChange */}
  placeholder="Выберите..."
  {/* ❌ Отсутствует обязательный selectedLabel (Правило №27) */}
/>
```

---

## Обоснование

### Почему `react-hook-form` + Zod?

| Аспект | `useState` + ручная валидация | `react-hook-form` + Zod |
|--------|-------------------------------|--------------------------|
| Типобезопасность | Нет (все значения — `string`) | ✅ Типы выводятся из схемы |
| Валидация | Ручная, дублируется | ✅ Декларативная, в одном месте |
| Производительность | Перерендер на каждое изменение | ✅ Перерендер только при отправке |
| Переиспользование | Невозможно | ✅ Схемы и хуки переиспользуются |
| Синхронизация с бэкендом | Нет | ✅ Zod ↔ Pydantic (похожий синтаксис) |

### Почему `useToast()` из `shadcn/ui`?

| Аспект | Нативные `alert()` | Самописные компоненты | `useToast()` |
|--------|---------------------|------------------------|---------------|
| Единообразие стиля | ❌ Чужеродно | ⚠️ Зависит от реализации | ✅ Единый стиль |
| Тёмная тема | ❌ Нет | ⚠️ Нужно реализовать | ✅ Из коробки |
| Неблокирующий | ❌ Блокирует | ✅ | ✅ |
| Поддержка `action` (кнопка) | ❌ Нет | ⚠️ Нужно реализовать | ✅ Из коробки |
| Варианты (`destructive`) | ❌ Нет | ⚠️ Нужно реализовать | ✅ Из коробки |
| Интеграция с React | ❌ Нет | ⚠️ Нужно реализовать | ✅ Из коробки |

### Почему `<Controller>` для всех полей?

В проекте устоялся паттерн использования `<Controller>` для **всех** полей формы, а не только для сложных. Это обеспечивает:
- **Единообразие кода** — все поля оформлены одинаково, легко читать и рефакторить
- **Лёгкость замены** — если `<Input>` нужно заменить на кастомный компонент, не нужно менять обвязку
- **Доступ к `fieldState`** — можно получить `fieldState.error` для каждого поля
- **Совместимость с Правилом №27** (`ReferenceSelect`) и **Правилом №34** (`Switch`)

---

## Чек-лист применения

При создании любой формы проверьте:

**Управление формой:**
- [ ] Используется ли `useForm()` из `react-hook-form`?
- [ ] Подключен ли `zodResolver` с Zod-схемой?
- [ ] Схема валидации объявлена через `z.object({...})`?
- [ ] Тип формы выведен через `z.infer<typeof schema>`?
- [ ] `defaultValues` объявлены как константа `CREATE_DEFAULTS`?

**Поля формы:**
- [ ] Все поля обёрнуты в `<Controller>` (единый паттерн проекта)?
- [ ] Справочники используют `ReferenceSelect` с актуальной сигнатурой (Правило №27)?
- [ ] Переключатели используют `Switch` с актуальной сигнатурой (Правило №34)?

**Ошибки валидации:**
- [ ] Ошибки отображаются под соответствующими полями?
- [ ] Для отображения используется `<p className="text-xs text-destructive">`?
- [ ] Проверка ошибки выполняется через `&&`?

**Состояние загрузки:**
- [ ] Кнопка отправки заблокирована через `disabled={isSubmitting}`?
- [ ] При блокировке отображается иконка загрузки?

**Уведомления:**
- [ ] Используется ли `useToast()` из `@/components/ui/use-toast`?
- [ ] Отсутствуют ли вызовы `alert()`, `confirm()`, `prompt()`?
- [ ] Отсутствуют ли вызовы `console.log()`/`console.error()` для пользователя?
- [ ] Отсутствуют ли самописные компоненты уведомлений?
- [ ] Для ошибок используется `variant: "destructive"`?
- [ ] Обработка ошибок в `catch`/`onError` использует `unknown` (Правило №36)?

**Сброс формы:**
- [ ] При закрытии модалки вызывается `reset(CREATE_DEFAULTS)` (Правило №20)?
- [ ] При открытии в режиме редактирования вызывается `reset({...})` (Правило №37)?

---

## Связь с другими правилами

| Правило | Связь |
|---------|-------|
| №9 (Orval-хуки) | Мутации формы выполняются через Orval-хуки |
| №12 (Поиск через form) | Частный случай формы для поиска |
| №20 (Сброс формы) | Детализация требования №6 |
| №22 (Разделение состояний поиска) | Разделение `searchInput` и `search` — регулируется Правилом №22, не дублируется здесь |
| №27 (ReferenceSelect) | Справочники через `<Controller>` — детализация требования №2 |
| №34 (Switch) | Переключатели через `<Controller>` — детализация требования №2 |
| №35 (Вынесение модалок) | Формы в модалках выносятся в отдельный компонент |
| №36 (Безопасная обработка ошибок) | Обработка ошибок в `catch`/`onError` |
| №37 (Синхронизация формы) | Синхронизация `initialData` через `useEffect` |
| №38 (Асинхронная инициализация таблиц) | Таблицы с отдельной загрузкой в формах |
| №39 (Название-ссылка) | Документные модалки с блокировкой используют тот же стандарт форм |
| ТЗ §6.2 | Валидация формата тегов через Zod |

---

Это правило является **обязательным** для всех форм в проекте. Любое отклонение (ручная валидация, нативные `alert()`, самописные уведомления) будет считаться нарушением архитектуры и подлежит немедленному исправлению при код-ревью.