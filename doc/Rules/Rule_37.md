# Правило №37: Синхронизация формы при открытии модалки

## 1. Область применения

Правило применяется во всех модальных окнах создания/редактирования сущностей (`EditDoctypeModal`, `EditRoleModal`, `EditUserModal` и т.д.), где необходимо синхронизировать данные из `initialData` с формой `react-hook-form` при открытии модалки.

---

## 2. Базовые требования

### 2.1. Синхронизация через `useEffect`
При открытии модалки данные из `initialData` должны синхронизироваться с формой через `useEffect` с зависимостями `[open, initialData, reset]`.

```tsx
// ✅ ПРАВИЛЬНО: Синхронизация формы через useEffect
useEffect(() => {
  if (open) {
    if (initialData) {
      // Режим редактирования: заполняем форму данными из БД
      reset({
        name: initialData.name || "",
        description: initialData.description || "",
        is_active: initialData.is_active ?? true,
        domain_id: initialData.domain_id || "",
      });
    } else {
      // Режим создания: сбрасываем к дефолтным значениям
      reset(CREATE_DEFAULTS);
    }
  }
}, [open, initialData, reset]);
```

### 2.2. Категорический запрет на `setState` внутри `useEffect`
**Запрещено** вызывать `setState` (например, `setSelectedSectionIds`, `setSelectedUserIds`) внутри `useEffect`, который синхронизирует форму. Это вызывает каскадные рендеры и предупреждение React:

```
Error: Calling setState synchronously within an effect can trigger cascading renders
```

```tsx
// ❌ ЗАПРЕЩЕНО: Вызов setState внутри useEffect
useEffect(() => {
  if (initialData) {
    reset({ name: initialData.name });
    setSelectedSectionIds(initialData.section_ids || []); // ❌ Каскадные рендеры!
    setSelectedUserIds(initialData.user_ids || []);       // ❌ Каскадные рендеры!
  }
}, [initialData, reset]);
```

---

## 3. Альтернативные решения для производных состояний

Если вам нужно управлять состояниями, которые зависят от `initialData` (например, массивы выбранных ID секций или пользователей), используйте один из двух подходов:

### 3.1. Подход №1: Интеграция в форму через `watch()`

Если состояние логически связано с формой, добавьте его в Zod-схему и используйте `watch()` из `react-hook-form`:

```tsx
// ✅ ПРАВИЛЬНО: Производное состояние как часть формы
const doctypeSchema = z.object({
  name: z.string().min(1),
  description: z.string().optional(),
  section_ids: z.array(z.string().uuid()).optional(), // ✅ Добавляем в схему
});

type DoctypeFormData = z.infer<typeof doctypeSchema>;

const CREATE_DEFAULTS: DoctypeFormData = {
  name: "",
  description: "",
  section_ids: [], // ✅ В дефолтных значениях
};

// В компоненте:
const { control, reset, watch } = useForm<DoctypeFormData>({
  resolver: zodResolver(doctypeSchema),
  defaultValues: CREATE_DEFAULTS,
});

// ✅ Получаем значение реактивно из формы
const selectedSectionIds = watch("section_ids") || [];

// ✅ Синхронизация при открытии модалки
useEffect(() => {
  if (open) {
    if (initialData) {
      reset({
        name: initialData.name,
        description: initialData.description,
        section_ids: initialData.section_ids || [], // ✅ Форма сама это запомнит
      });
    } else {
      reset(CREATE_DEFAULTS);
    }
  }
}, [open, initialData, reset]);

// В JSX:
<Controller
  name="section_ids"
  control={control}
  render={({ field }) => (
    <TenantMultiSelect
      value={field.value ?? []}
      onChange={field.onChange}
    />
  )}
/>
```

**Преимущества:**
- Единый источник истины (Single Source of Truth)
- Нет каскадных рендеров
- Данные автоматически валидируются Zod-схемой
- Отправляются вместе с остальными данными формы

### 3.2. Подход №2: Паттерн с `key` на контейнере

Если состояние управляет сложным отдельным компонентом со своей внутренней логикой, используйте паттерн с `key`, который заставляет React пересоздать компонент при изменении `initialData`:

```tsx
// ✅ ПРАВИЛЬНО: Паттерн с key для принудительного пересоздания
const [selectedSectionIds, setSelectedSectionIds] = useState<string[]>([]);

// ✅ useEffect ТОЛЬКО для сброса формы, без setState
useEffect(() => {
  if (open) {
    if (initialData) {
      reset({
        name: initialData.name,
        description: initialData.description,
      });
    } else {
      reset(CREATE_DEFAULTS);
    }
  }
}, [open, initialData, reset]);

// ✅ Стейт инициализируется один раз при монтировании
// (не синхронизируется через useEffect)

// В JSX:
<TabsContent 
  value="sections" 
  key={initialData?.id || "new"} // ✅ Ключ меняется при смене initialData
>
  <SectionSelector
    selectedIds={selectedSectionIds}
    onChange={setSelectedSectionIds}
  />
</TabsContent>
```

**Как это работает:**
1. При открытии модалки для другой записи `initialData.id` меняется
2. `key` меняется → React уничтожает старый компонент и создаёт новый
3. Новый компонент инициализирует `useState` с актуальными данными из `initialData`
4. Нет каскадных рендеров, нет `setState` в `useEffect`

---

## 4. Полный эталонный пример (EditRoleModal.tsx)

```tsx
import { useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQueryClient } from "@tanstack/react-query";

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { useToast } from "@/components/ui/use-toast";

import { useUpdateRoleRolesRoleIdPut } from "@/api/generated/roles/roles";
import type { RoleResponseSchema } from "@/api/generated/fastAPI.schemas";

const roleSchema = z.object({
  name: z.string().min(1, "Название обязательно"),
  description: z.string().optional(),
  is_active: z.boolean().optional(),
  section_ids: z.array(z.string().uuid()).optional(), // ✅ Часть формы
});

type RoleFormData = z.infer<typeof roleSchema>;

const CREATE_DEFAULTS: RoleFormData = {
  name: "",
  description: "",
  is_active: true,
  section_ids: [],
};

interface EditRoleModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData: RoleResponseSchema | null;
  onSaved: (id: string, name: string) => Promise<void>;
}

export const EditRoleModal = ({
  open,
  onOpenChange,
  initialData,
  onSaved,
}: EditRoleModalProps) => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const {
    control,
    handleSubmit,
    reset,
    watch, // ✅ Для реактивного получения section_ids
    formState: { errors, isSubmitting },
  } = useForm<RoleFormData>({
    resolver: zodResolver(roleSchema),
    defaultValues: CREATE_DEFAULTS,
  });

  const updateMutation = useUpdateRoleRolesRoleIdPut();

  // ✅ Правило №37: Синхронизация формы БЕЗ setState
  useEffect(() => {
    if (open) {
      if (initialData) {
        reset({
          name: initialData.name || "",
          description: initialData.description || "",
          is_active: initialData.is_active ?? true,
          section_ids: initialData.section_ids || [], // ✅ Форма сама это запомнит
        });
      } else {
        reset(CREATE_DEFAULTS);
      }
    }
  }, [open, initialData, reset]);

  // ✅ Реактивное получение значения из формы
  const selectedSectionIds = watch("section_ids") || [];

  const onSubmit = async (formData: RoleFormData) => {
    if (!initialData?.id) return;
    
    try {
      await updateMutation.mutateAsync({
        roleId: initialData.id,
        data: formData as any,
      });
      
      await queryClient.invalidateQueries({ queryKey: ["roles"] });
      onOpenChange(false);
      reset(CREATE_DEFAULTS); // ✅ Правило №20
      await onSaved(initialData.id, formData.name);
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: err?.response?.data?.detail || "Не удалось сохранить роль",
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {initialData ? "Редактирование" : "Создание"} роли
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Поля формы */}
          
          {/* ✅ Компонент выбора секций использует данные из формы */}
          <Controller
            name="section_ids"
            control={control}
            render={({ field }) => (
              <SectionSelector
                value={field.value ?? []}
                onChange={field.onChange}
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

## 5. Антипаттерны (запрещено)

### 5.1. Вызов `setState` внутри `useEffect`

```tsx
// ❌ ЗАПРЕЩЕНО:
useEffect(() => {
  if (initialData) {
    reset({ name: initialData.name });
    setSelectedSectionIds(initialData.section_ids || []); // ❌ Каскадные рендеры!
  }
}, [initialData, reset]);
```

**Почему плохо:**
- React выдаёт предупреждение о каскадных рендерах
- Производительность падает из-за лишних перерисовок
- Нарушается принцип единого источника истины

### 5.2. Дублирование состояния

```tsx
// ❌ ЗАПРЕЩЕНО: Держать section_ids и в форме, и в отдельном useState
const [selectedSectionIds, setSelectedSectionIds] = useState([]);

useEffect(() => {
  if (initialData) {
    reset({ name: initialData.name });
    setSelectedSectionIds(initialData.section_ids || []); // ❌ Дублирование!
  }
}, [initialData, reset]);

// В onSubmit:
const payload = {
  ...formData,
  section_ids: selectedSectionIds, // ❌ Откуда брать? Из формы или из useState?
};
```

**Почему плохо:**
- Два источника истины для одних данных
- Риск рассинхронизации
- Сложность поддержки

### 5.3. Отсутствие `reset` при закрытии

```tsx
// ❌ ЗАПРЕЩЕНО: Не сбрасывать форму при закрытии
useEffect(() => {
  if (open && initialData) {
    reset({ name: initialData.name });
  }
  // ❌ Нет ветки else для сброса при создании
}, [open, initialData, reset]);
```

**Почему плохо:**
- При следующем открытии модалки в режиме создания останутся данные от предыдущего редактирования
- Нарушение Правила №20

---

## 6. Обоснование архитектурных решений

### 6.1. Почему запрет на `setState` в `useEffect`?
- **Каскадные рендеры**: Вызов `setState` внутри `useEffect` запускает дополнительный цикл рендеринга, что снижает производительность
- **Нарушение принципа React**: `useEffect` предназначен для синхронизации с внешними системами (DOM, API, подписки), а не для управления состоянием React
- **Рекомендация React**: Официальная документация React явно не рекомендует этот паттерн (https://react.dev/learn/you-might-not-need-an-effect)

### 6.2. Почему `watch()` лучше отдельного `useState`?
- **Единый источник истины**: Данные хранятся только в `react-hook-form`, а не размазаны между формой и `useState`
- **Автоматическая синхронизация**: При вызове `reset()` форма обновляет все свои поля, включая `section_ids`
- **Валидация**: Данные проходят через Zod-схему, что гарантирует их корректность
- **Упрощение `onSubmit`**: Не нужно вручную собирать данные из разных источников

### 6.3. Почему паттерн с `key` работает?
- **Принудительное пересоздание**: Изменение `key` заставляет React полностью уничтожить и пересоздать компонент
- **Инициализация с актуальными данными**: Новый компонент инициализирует `useState` с правильными начальными значениями
- **Нет каскадных рендеров**: Пересоздание происходит один раз, без лишних обновлений

---

## 7. Чек-лист для проверки

При синхронизации формы убедитесь, что:

- [ ] `useEffect` имеет зависимости `[open, initialData, reset]`
- [ ] Внутри `useEffect` вызывается **только** `reset()`, без `setState`
- [ ] Есть ветка `else` для сброса формы к `CREATE_DEFAULTS` при создании
- [ ] Производные состояния (массивы ID) добавлены в Zod-схему и `CREATE_DEFAULTS`
- [ ] Для реактивного получения значений используется `watch()` из `react-hook-form`
- [ ] Если используется отдельный `useState`, применён паттерн с `key` на контейнере
- [ ] Нет дублирования состояния (данные не хранятся и в форме, и в `useState`)
- [ ] При закрытии модалки вызывается `reset(CREATE_DEFAULTS)` (Правило №20)
- [ ] React не выдаёт предупреждений о каскадных рендерах

---

## 8. Связь с другими правилами

- **Правило №20** (Сброс формы) — `reset(CREATE_DEFAULTS)` при закрытии модалки
- **Правило №24** (invalidateQueries ДО закрытия) — порядок действий при сохранении
- **Правило №35** (Вынесение модалок) — синхронизация происходит внутри вынесенного компонента
- **Правило №36** (Обработка ошибок) — при ошибке сохранения форма НЕ сбрасывается

---

## 9. Пример полного обработчика с учётом Правила №37

```tsx
const onSubmit = async (formData: RoleFormData) => {
  try {
    // 1. Попытка сохранения
    await updateMutation.mutateAsync({
      roleId: initialData.id,
      data: formData as any,
    });
    
    // 2. Успех: инвалидация, закрытие, сброс, callback
    await queryClient.invalidateQueries({ queryKey: ["roles"] });
    onOpenChange(false);
    reset(CREATE_DEFAULTS); // ✅ Правило №20 и №37
    await onSaved(initialData.id, formData.name);
  } catch (error: unknown) {
    // 3. Ошибка: безопасное извлечение сообщения
    const err = error as { response?: { data?: { detail?: string } } };
    toast({
      variant: "destructive",
      title: "Ошибка сохранения",
      description: err?.response?.data?.detail || "Не удалось сохранить роль",
    });
    // 4. Форма НЕ сбрасывается, модалка НЕ закрывается — пользователь может исправить
  }
};
```

---

## 10. Итоговая рекомендация

**Всегда используйте подход №1 (интеграция в форму через `watch()`)**, если производное состояние логически связано с формой (массивы ID секций, пользователей, тегов и т.д.). Это обеспечивает:
- Чистоту архитектуры
- Отсутствие каскадных рендеров
- Единый источник истины
- Автоматическую валидацию

**Используйте подход №2 (паттерн с `key`)** только в исключительных случаях, когда состояние управляет сложным внешним компонентом, который не может быть интегрирован в `react-hook-form`.

---

Это правило является **строгим стандартом** для синхронизации форм в модальных окнах. Любые вызовы `setState` внутри `useEffect`, который синхронизирует форму, будут считаться нарушением архитектуры и должны быть исправлены.