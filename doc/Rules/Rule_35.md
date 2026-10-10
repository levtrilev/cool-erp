# Правило №35: Вынесение модальных окон в отдельный компонент

## 1. Область применения

Модальное окно редактирования (и создания) сущности **всегда** должно быть вынесено в отдельный компонент (например, `EditDoctypeModal.tsx`, `EditRoleModal.tsx`, `EditUserModal.tsx`). Страница списка отвечает только за отображение данных, управление открытием и передачу `initialData`, а вся логика формы, валидации и мутаций инкапсулирована в модалке.

---

## 2. Базовые требования

### 2.1. Запрет на "толстые" страницы списка
**Категорически запрещено** размещать форму создания/редактирования прямо внутри компонента страницы списка (`DoctypesPage.tsx`, `RolesPage.tsx` и т.д.). Вся логика формы должна быть инкапсулирована в отдельном файле.

```tsx
// ❌ ЗАПРЕЩЕНО: Вся логика в DoctypesPage.tsx
export const DoctypesPage = () => {
  const { control, handleSubmit, reset } = useForm<DoctypeFormData>({...});
  const createMutation = useCreateDoctypeDoctypesPost();
  const updateMutation = useUpdateDoctypeDoctypesDoctypeIdPut();
  
  const onSubmit = async (data) => { /* 100+ строк логики */ };
  
  return (
    <div>
      <Table>...</Table>
      <Dialog>
        <form onSubmit={handleSubmit(onSubmit)}>
          {/* Форма прямо в странице */}
        </form>
      </Dialog>
    </div>
  );
};

// ✅ ПРАВИЛЬНО: Страница только управляет состоянием
export const DoctypesPage = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingDoctype, setEditingDoctype] = useState<DoctypeResponseSchema | null>(null);
  
  const openEdit = (item: DoctypeResponseSchema) => {
    setEditingDoctype(item);
    setIsModalOpen(true);
  };
  
  return (
    <div>
      <Table>...</Table>
      <EditDoctypeModal
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        initialData={editingDoctype}
        onSaved={handleSaved}
      />
    </div>
  );
};
```

---

## 3. Структура пропсов модального окна

Каждый модальный компонент **обязан** принимать следующие пропсы:

```tsx
interface EditDoctypeModalProps {
  open: boolean;                                    // Состояние открытия
  onOpenChange: (open: boolean) => void;            // Обработчик закрытия
  initialData: DoctypeResponseSchema | null;        // null = режим создания
  onSaved: (id: string, name?: string) => Promise<void>; // Callback после сохранения
}
```

### 3.1. Назначение пропсов
- **`open`** — управляет видимостью модалки (Правило №20)
- **`onOpenChange`** — вызывается при закрытии, должен сбрасывать форму
- **`initialData`** — если `null`, модалка работает в режиме создания; иначе — редактирования
- **`onSaved`** — callback для умной навигации и подсветки (Правила №18, №23)

---

## 4. Синхронизация формы при открытии

При открытии модалки данные из `initialData` должны синхронизироваться с формой через `useEffect` с зависимостями `[open, initialData, reset]`.

```tsx
// ✅ ПРАВИЛЬНО: Синхронизация через useEffect
useEffect(() => {
  if (open) {
    if (initialData) {
      reset({
        name: initialData.name || "",
        description: initialData.description || "",
        is_active: initialData.is_active ?? true,
        domain_id: initialData.domain_id || "",
      });
    } else {
      reset(CREATE_DEFAULTS);
    }
  }
}, [open, initialData, reset]);
```

**Запрещено** вызывать `setState` (например, `setSelectedSectionIds`) внутри `useEffect` — это вызывает каскадные рендеры (Правило №37).

---

## 5. Сброс формы (Правило №20)

Константа `CREATE_DEFAULTS` должна быть объявлена **вне** компонента или в начале файла. Она используется:
- В `useForm({ defaultValues: CREATE_DEFAULTS })`
- В `reset(CREATE_DEFAULTS)` при закрытии модалки
- В `reset(CREATE_DEFAULTS)` после успешного сохранения

```tsx
// ✅ ПРАВИЛЬНО: Константа вне компонента
const CREATE_DEFAULTS: DoctypeFormData = {
  domain_id: "",
  doctype: "",
  doctype_name: "",
  description: "",
  is_active: true,
  tenant_ids: [],
};

export const EditDoctypeModal = ({ open, onOpenChange, initialData, onSaved }) => {
  const { reset } = useForm<DoctypeFormData>({
    resolver: zodResolver(doctypeSchema),
    defaultValues: CREATE_DEFAULTS,
  });
  
  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      reset(CREATE_DEFAULTS); // ✅ Сброс при закрытии
    }
    onOpenChange(newOpen);
  };
  
  // ...
};
```

---

## 6. Порядок действий при сохранении (Правило №24)

При успешном сохранении **строго соблюдать** порядок:
1. `invalidateQueries` (или `refetch`) — обновить кэш
2. `onOpenChange(false)` — закрыть модалку
3. `reset(CREATE_DEFAULTS)` — сбросить форму
4. `onSaved(id, name)` — вызвать callback родителя для подсветки

```tsx
// ✅ ПРАВИЛЬНО: Строгий порядок
const onSubmit = async (formData: DoctypeFormData) => {
  try {
    if (initialData) {
      await updateMutation.mutateAsync({
        doctypeId: initialData.id,
        data: formData as DoctypeUpdateSchema,
      });
      // 1. Инвалидация кэша
      await queryClient.invalidateQueries({ queryKey: ["doctypes"] });
      // 2. Закрытие модалки
      onOpenChange(false);
      // 3. Сброс формы
      reset(CREATE_DEFAULTS);
      // 4. Callback родителя
      await onSaved(initialData.id, formData.doctype_name);
    } else {
      const res = await createMutation.mutateAsync({
        data: formData as DoctypeCreateSchema,
      });
      await queryClient.invalidateQueries({ queryKey: ["doctypes"] });
      onOpenChange(false);
      reset(CREATE_DEFAULTS);
      if (res.data?.id) {
        await onSaved(res.data.id, formData.doctype_name);
      }
    }
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } } };
    toast({
      variant: "destructive",
      title: "Ошибка",
      description: err?.response?.data?.detail || "Не удалось сохранить",
    });
  }
};
```

---

## 7. Обработка ошибок (Правило №36)

В блоках `catch` и `onError` **запрещено** использовать `any`. Всегда использовать `unknown` с безопасным приведением типа.

```tsx
// ✅ ПРАВИЛЬНО:
catch (error: unknown) {
  const err = error as { response?: { data?: { detail?: string } } };
  toast({
    variant: "destructive",
    title: "Ошибка",
    description: err?.response?.data?.detail || "Не удалось сохранить",
  });
}

// ❌ ЗАПРЕЩЕНО:
catch (error: any) {
  toast({ description: error.response?.data?.detail });
}
```

---

## 8. Полный эталонный пример (EditDoctypeModal.tsx)

```tsx
import { useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { useToast } from "@/components/ui/use-toast";
import { ReferenceSelect } from "@/lib/reusable/ReferenceSelect";

import {
  useCreateDoctypeDoctypesPost,
  useUpdateDoctypeDoctypesDoctypeIdPut,
} from "@/api/generated/doctypes/doctypes";
import { getDomainsDomainsGet } from "@/api/generated/domains/domains";
import type { DoctypeResponseSchema } from "@/api/generated/fastAPI.schemas";

const doctypeSchema = z.object({
  domain_id: z.string().uuid("Выберите домен"),
  doctype: z.string().min(2, "Минимум 2 символа"),
  doctype_name: z.string().min(2, "Минимум 2 символа"),
  description: z.string().optional(),
  is_active: z.boolean().optional(),
});

type DoctypeFormData = z.infer<typeof doctypeSchema>;

// ✅ Правило №20: Константа вне компонента
const CREATE_DEFAULTS: DoctypeFormData = {
  domain_id: "",
  doctype: "",
  doctype_name: "",
  description: "",
  is_active: true,
};

interface EditDoctypeModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData: DoctypeResponseSchema | null;
  onSaved: (id: string, name?: string) => Promise<void>;
}

export const EditDoctypeModal = ({
  open,
  onOpenChange,
  initialData,
  onSaved,
}: EditDoctypeModalProps) => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<DoctypeFormData>({
    resolver: zodResolver(doctypeSchema),
    defaultValues: CREATE_DEFAULTS,
  });

  const createMutation = useCreateDoctypeDoctypesPost();
  const updateMutation = useUpdateDoctypeDoctypesDoctypeIdPut();

  // ✅ Правило №37: Синхронизация формы
  useEffect(() => {
    if (open) {
      if (initialData) {
        reset({
          domain_id: initialData.domain_id,
          doctype: initialData.doctype,
          doctype_name: initialData.doctype_name,
          description: initialData.description || "",
          is_active: initialData.is_active ?? true,
        });
      } else {
        reset(CREATE_DEFAULTS);
      }
    }
  }, [open, initialData, reset]);

  // ✅ Правило №24: Строгий порядок
  const onSubmit = async (formData: DoctypeFormData) => {
    try {
      if (initialData) {
        await updateMutation.mutateAsync({
          doctypeId: initialData.id,
          data: formData as any,
        });
        await queryClient.invalidateQueries({ queryKey: ["doctypes"] });
        onOpenChange(false);
        reset(CREATE_DEFAULTS);
        await onSaved(initialData.id, formData.doctype_name);
      } else {
        const res = await createMutation.mutateAsync({
          data: formData as any,
        });
        await queryClient.invalidateQueries({ queryKey: ["doctypes"] });
        onOpenChange(false);
        reset(CREATE_DEFAULTS);
        if (res.data?.id) {
          await onSaved(res.data.id, formData.doctype_name);
        }
      }
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: err?.response?.data?.detail || "Не удалось сохранить",
      });
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      reset(CREATE_DEFAULTS);
    }
    onOpenChange(newOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {initialData ? "Редактирование" : "Создание"} типа документа
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Поля формы */}
          <DialogFooter>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              Сохранить
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
```

---

## 9. Обоснование архитектурных решений

1. **Почему отдельный компонент?**
   - Разделение ответственности: страница списка отвечает за отображение, модалка — за форму
   - Переиспользование: модалку можно вызвать из дашборда, из другой страницы
   - Чистота кода: `DoctypesPage.tsx` уменьшается с 400 до 150 строк

2. **Почему `initialData: T | null`, а не два отдельных режима?**
   - Единый интерфейс для создания и редактирования
   - `null` — однозначный сигнал режима создания
   - Упрощает логику родителя: `setEditingDoctype(null)` перед открытием

3. **Почему `onSaved`, а не `onSuccess`?**
   - Родитель решает, что делать после сохранения (подсветка, навигация, toast)
   - Модалка не знает о структуре страницы списка
   - Соответствует принципу инверсии зависимостей

---

## 10. Чек-лист для проверки

При создании модального окна убедитесь, что:

- [ ] Модалка вынесена в отдельный файл `EditXxxModal.tsx`
- [ ] Пропсы: `open`, `onOpenChange`, `initialData`, `onSaved`
- [ ] Константа `CREATE_DEFAULTS` объявлена вне компонента
- [ ] `useForm({ defaultValues: CREATE_DEFAULTS })`
- [ ] `useEffect` с зависимостями `[open, initialData, reset]` для синхронизации
- [ ] При закрытии модалки вызывается `reset(CREATE_DEFAULTS)`
- [ ] При сохранении: `invalidateQueries` → `onOpenChange(false)` → `reset` → `onSaved`
- [ ] Обработка ошибок через `error: unknown` (Правило №36)
- [ ] Нет `setState` внутри `useEffect` (Правило №37)
- [ ] Страница списка содержит только `useState` для `isModalOpen` и `editingXxx`

---

## 11. Связь с другими правилами

- **Правило №20** (Сброс формы) — `reset(CREATE_DEFAULTS)` при закрытии
- **Правило №24** (invalidateQueries ДО закрытия) — строгий порядок
- **Правило №36** (Обработка ошибок) — `unknown` вместо `any`
- **Правило №37** (Синхронизация формы) — `useEffect` без `setState`

---

Это правило является **строгим стандартом** для всех модальных окон в проекте. Любые отклонения от него будут считаться нарушением архитектуры и должны быть исправлены.