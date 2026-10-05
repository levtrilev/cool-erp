# Правило №8: Frontend — формы и состояния

Все формы и управляемые состояния на фронтенде **ОБЯЗАТЕЛЬНО** должны следовать единым стандартам:
* Для сложных полей в формах использовать `<Controller>` из `react-hook-form`.
* Разделять состояния ввода и запроса (`searchInput` vs `search`) — поиск выполняется по кнопке/Enter, а не на каждый символ.
* Toast-уведомления реализовывать через `useToast()` из `shadcn/ui`.

Использование «голых» `useState` для форм, поиск по каждому символу (`onChange`) и кастомные реализации уведомлений **КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНЫ**.

---

### 1. Обоснование (Почему это важно)

1. **Унификация управления формами:** В проекте используется единый стек (React Hook Form + Zod). Это позволяет использовать одинаковые паттерны валидации, обработки ошибок и отправки данных во всех формах приложения.
2. **Производительность:** Разделение состояний `searchInput` и `search` предотвращает лавину запросов к бэкенду при быстром вводе текста. Запрос отправляется только после явного подтверждения пользователем.
3. **Единообразие UX:** Все toast-уведомления в приложении выглядят одинаково, поддерживают темную тему и имеют единое поведение (время показа, расположение, анимация).
4. **Снижение объема кода:** Использование готовых хуков и компонентов вместо самописных решений сокращает количество boilerplate-кода в 2-3 раза.

---

### 2. Обязательные требования к реализации

#### 2.1. Управление формами через React Hook Form
Все формы (создание, редактирование, фильтры) **ОБЯЗАТЕЛЬНО** должны использовать:
* `useForm()` из `react-hook-form` для управления состоянием формы.
* `zodResolver` из `@hookform/resolvers/zod` для валидации по Zod-схемам.
* `<Controller>` для сложных полей (справочники, чекбоксы, радиокнопки, кастомные компоненты).

#### 2.2. Разделение состояний ввода и запроса
В списочных страницах **ОБЯЗАТЕЛЬНО** должны быть две отдельные переменные:
* `searchInput: string` — значение в поле ввода (обновляется на каждое нажатие клавиши).
* `search: string` — значение, отправляемое на бэкенд (обновляется только по Enter/кнопке).

#### 2.3. Toast-уведомления
Все уведомления **ОБЯЗАТЕЛЬНО** должны использовать `useToast()` из `shadcn/ui`. Нативные `alert()`, `console.log()` для пользователя или самописные компоненты уведомлений **ЗАПРЕЩЕНЫ**.

---

### 3. Примеры кода

#### ✅ ПРАВИЛЬНО: Форма создания с валидацией

```tsx
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { ReferenceSelect } from "@/lib/reusable/ReferenceSelect";

// Zod-схема валидации
const roleSchema = z.object({
  name: z.string().min(3, "Минимум 3 символа").max(100),
  description: z.string().optional(),
  tenant_id: z.string().uuid("Выберите организацию"),
});

type RoleFormData = z.infer<typeof roleSchema>;

export const CreateRoleModal = ({ open, onOpenChange, onRoleSaved }) => {
  const { toast } = useToast(); // ✅ Toast из shadcn/ui
  
  const { control, handleSubmit, formState: { errors, isSubmitting } } = useForm<RoleFormData>({
    resolver: zodResolver(roleSchema), // ✅ Валидация через Zod
    defaultValues: {
      name: "",
      description: "",
      tenant_id: "",
    },
  });

  const createMutation = useCreateRoleRolesPost();

  const onSubmit = async (data: RoleFormData) => {
    try {
      await createMutation.mutateAsync({ data });
      toast({ title: "Роль успешно создана" }); // ✅ Уведомление через useToast
      onOpenChange(false);
      onRoleSaved();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: "Не удалось создать роль",
      });
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {/* ✅ Обычное поле через register */}
      <div className="space-y-2">
        <label>Название</label>
        <Input {...control.register("name")} />
        {errors.name && (
          <p className="text-xs text-destructive">{errors.name.message}</p>
        )}
      </div>

      {/* ✅ Сложное поле через Controller (справочник) */}
      <div className="space-y-2">
        <label>Организация</label>
        <Controller
          name="tenant_id"
          control={control}
          render={({ field, fieldState }) => (
            <>
              <ReferenceSelect
                endpoint="/api/v1/tenants"
                value={field.value}
                onChange={field.onChange}
                placeholder="Выберите организацию..."
              />
              {fieldState.error && (
                <p className="text-xs text-destructive">{fieldState.error.message}</p>
              )}
            </>
          )}
        />
      </div>

      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Создание..." : "Создать"}
      </Button>
    </form>
  );
};
```

#### ✅ ПРАВИЛЬНО: Разделение состояний поиска

```tsx
export const RolesPage = () => {
  // ✅ РАЗДЕЛЕНИЕ СОСТОЯНИЙ
  const [searchInput, setSearchInput] = useState(""); // Для ввода
  const [search, setSearch] = useState("");           // Для запроса

  // Запрос использует search (не searchInput!)
  const { data } = useReadRolesRolesGet({
    skip: 0,
    limit: 10,
    search: search || undefined, // ✅ Отправляется только подтвержденное значение
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput); // ✅ Копируем только при подтверждении
    setPage(1);
  };

  return (
    <form onSubmit={handleSearch}>
      <Input
        value={searchInput} // ✅ Привязан к searchInput
        onChange={(e) => setSearchInput(e.target.value)} // ✅ Обновляется на каждый символ
        placeholder="Поиск по названию..."
      />
      <Button type="submit">Найти</Button>
    </form>
  );
};
```

#### ❌ НЕПРАВИЛЬНО: Использование useState для форм

```tsx
// ❌ ГРУБОЕ НАРУШЕНИЕ ПРАВИЛА №8
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
```
*Почему это плохо:* Нет типобезопасности, ручная валидация, дублирование кода, невозможно переиспользовать логику.

#### ❌ НЕПРАВИЛЬНО: Поиск по каждому символу

```tsx
// ❌ ГРУБОЕ НАРУШЕНИЕ ПРАВИЛА №8
<Input
  value={search}
  onChange={(e) => {
    setSearch(e.target.value); // ❌ Запрос на каждый символ!
    setPage(1);
  }}
/>
```
*Почему это плохо:* При вводе слова из 10 символов будет 10 запросов к бэкенду. Это создает лишнюю нагрузку и вызывает «мигание» таблицы.

#### ❌ НЕПРАВИЛЬНО: Использование alert() или самописных уведомлений

```tsx
// ❌ ГРУБОЕ НАРУШЕНИЕ ПРАВИЛА №8
const handleSave = async () => {
  await createMutation.mutateAsync({ data });
  alert("Роль создана!"); // ❌ Нативное уведомление
};

// ❌ ИЛИ самописный компонент
const [showToast, setShowToast] = useState(false);
// ... кастомный <div> с анимацией
```
*Почему это плохо:* `alert()` блокирует UI и выглядит чужеродно. Самописные компоненты дублируют функциональность и не поддерживают темную тему.

---

### 4. Нюансы и лучшие практики

#### 4.1. Когда использовать `register`, а когда `Controller`
* **`register`** — для простых полей (`<Input>`, `<Textarea>`), которые нативно поддерживают `onChange` и `value`.
* **`<Controller>`** — для сложных компонентов (справочники, чекбоксы, кастомные виджеты), которые не передают `value`/`onChange` напрямую или требуют дополнительной логики.

#### 4.2. Валидация через Zod
Все схемы валидации **ОБЯЗАТЕЛЬНО** должны быть описаны через Zod:
```tsx
const schema = z.object({
  name: z.string().min(3).max(100),
  email: z.string().email(),
  age: z.number().min(18).max(100),
});
```
Это обеспечивает типобезопасность и единообразие валидации на фронтенде и бэкенде (Pydantic на бэкенде тоже использует похожий синтаксис).

#### 4.3. Обработка ошибок формы
Ошибки валидации **ОБЯЗАТЕЛЬНО** должны отображаться под соответствующими полями:
```tsx
{errors.name && (
  <p className="text-xs text-destructive mt-1">{errors.name.message}</p>
)}
```

#### 4.4. Состояние загрузки
Для кнопок отправки **ОБЯЗАТЕЛЬНО** использовать `isSubmitting` из `formState`:
```tsx
<Button type="submit" disabled={isSubmitting}>
  {isSubmitting ? "Сохранение..." : "Сохранить"}
</Button>
```

#### 4.5. Сброс формы после отправки
После успешной отправки форму **ОБЯЗАТЕЛЬНО** нужно сбросить:
```tsx
const onSubmit = async (data) => {
  await mutation.mutateAsync({ data });
  reset(); // ✅ Сброс формы
  toast({ title: "Успешно" });
};
```

#### 4.6. Toast-уведомления: варианты
```tsx
// ✅ Успешное уведомление
toast({ title: "Роль создана" });

// ✅ Уведомление с описанием
toast({ 
  title: "Роль создана",
  description: "Можете назначить её пользователям"
});

// ✅ Уведомление об ошибке
toast({
  variant: "destructive",
  title: "Ошибка",
  description: "Не удалось создать роль"
});

// ✅ Уведомление с действием (кнопкой)
toast({
  title: "Роль создана",
  description: "На странице 5",
  action: <Button onClick={() => setPage(5)}>Перейти</Button>
});
```

#### 4.7. Связь с другими правилами
* **Правило №12:** Разделение `searchInput` и `search` + обёртка в `<form>`.
* **Правило №22:** Обязательная структура состояний списочной страницы.
* **Правило №27:** Использование `ReferenceSelect` через `<Controller>` для справочников.

---

### 5. Чек-лист для разработчика

При создании любой формы или списочной страницы проверьте:

**Формы:**
- [ ] Используется ли `useForm()` из `react-hook-form`?
- [ ] Подключен ли `zodResolver` с Zod-схемой?
- [ ] Для сложных полей используется `<Controller>`?
- [ ] Отображаются ли ошибки валидации под полями?
- [ ] Используется ли `isSubmitting` для блокировки кнопки отправки?
- [ ] Сбрасывается ли форма после успешной отправки (`reset()`)?

**Поиск:**
- [ ] Объявлены ли две переменные: `searchInput` и `search`?
- [ ] Поле ввода привязано к `searchInput`?
- [ ] Запрос к бэкенду использует `search` (не `searchInput`)?
- [ ] Поиск обёрнут в `<form>` с `onSubmit` (Правило №12)?
- [ ] Значение `search` обновляется только при подтверждении (Enter/кнопка)?

**Уведомления:**
- [ ] Используется ли `useToast()` из `shadcn/ui`?
- [ ] Отсутствуют ли вызовы `alert()`, `console.log()` для пользователя?
- [ ] Отсутствуют ли самописные компоненты уведомлений?
- [ ] Для ошибок используется `variant: "destructive"`?

Следование этому правилу гарантирует, что все формы в Cool ERP будут типобезопасными, валидируемыми и единообразными. Пользователь получит предсказуемый UX: мгновенная валидация, понятные ошибки, профессиональные уведомления. Разработчик — быстрый онбординг, переиспользуемый код и автоматическую синхронизацию с бэкендом через Zod/Pydantic.