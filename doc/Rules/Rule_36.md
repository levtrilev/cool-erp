# Правило №36: Безопасная обработка ошибок (замена `any` на `unknown`)

## 1. Область применения

Правило применяется во **всех** блоках обработки ошибок на фронтенде:
- Блоки `catch` в `try/catch`
- Обработчики `onError` в мутациях React Query (`useMutation`, Orval-хуки)
- Обработчики `onError` в `useQuery`
- Любые callback-функции, принимающие неизвестный объект ошибки

---

## 2. Базовые требования

### 2.1. Категорический запрет на `any`
В блоках обработки ошибок **запрещено** использовать тип `any`. Это нарушает строгую типизацию TypeScript и вызывает предупреждения линтера (`unexpected any`).

```tsx
// ❌ ЗАПРЕЩЕНО:
catch (error: any) {
  toast({ description: error.response?.data?.detail });
}

// ❌ ЗАПРЕЩЕНО:
onError: (error: any) => {
  console.log(error.message);
}

// ❌ ЗАПРЕЩЕНО (неявное any):
catch (error) { // TypeScript выведет unknown, но лучше явно
  // ...
}
```

### 2.2. Обязательное использование `unknown`
Вместо `any` **всегда** использовать тип `unknown` с последующим безопасным приведением типа.

```tsx
// ✅ ПРАВИЛЬНО:
catch (error: unknown) {
  const err = error as { response?: { data?: { detail?: string } } };
  // безопасное использование err?.response?.data?.detail
}
```

---

## 3. Эталонный паттерн приведения типа

Структура ошибки от Axios/FastAPI всегда имеет вид:
```
{
  response?: {
    data?: {
      detail?: string  // ← сообщение от бэкенда
    }
  }
}
```

Поэтому безопасное приведение типа выглядит так:

```tsx
const err = error as { response?: { data?: { detail?: string } } };
```

Все поля объявлены как **опциональные** (`?`), что защищает от падений при нестандартных структурах ошибок (например, сетевые ошибки без `response`).

---

## 4. Примеры использования

### 4.1. В блоке `try/catch`

```tsx
const onSubmit = async (formData: DoctypeFormData) => {
  try {
    if (initialData) {
      await updateMutation.mutateAsync({
        doctypeId: initialData.id,
        data: formData as DoctypeUpdateSchema,
      });
      await queryClient.invalidateQueries({ queryKey: ["doctypes"] });
      onOpenChange(false);
      reset(CREATE_DEFAULTS);
      await onSaved(initialData.id);
    }
  } catch (error: unknown) {
    // ✅ Правило №36: Безопасное приведение типа
    const err = error as { response?: { data?: { detail?: string } } };
    toast({
      variant: "destructive",
      title: "Ошибка",
      description: err?.response?.data?.detail || "Не удалось сохранить тип документа",
    });
  }
};
```

### 4.2. В `onError` мутации

```tsx
updateUserMutation.mutate(
  { userId: user.id, data: updateData },
  {
    onSuccess: async () => {
      toast({ title: "Пользователь обновлен" });
      await onUserUpdated(user.id, data.name);
      onOpenChange(false);
    },
    // ✅ Правило №36: onError с unknown
    onError: (error: unknown) => {
      const err = error as { response?: { data?: { detail?: string } } };
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: err?.response?.data?.detail || "Не удалось обновить пользователя",
      });
    },
  },
);
```

### 4.3. В `handleDelete` страницы списка

```tsx
const handleDelete = async () => {
  if (!deleteDoctypeId) return;
  try {
    await deleteMutation.mutateAsync({ doctypeId: deleteDoctypeId });
    await refetch();
    setDeleteDoctypeId(null);
    toast({ title: "Удалено" });
  } catch (error: unknown) {
    // ✅ Правило №36
    const err = error as { response?: { data?: { detail?: string } } };
    toast({
      variant: "destructive",
      title: "Ошибка удаления",
      description: err?.response?.data?.detail || "Не удалось удалить запись",
    });
  }
};
```

---

## 5. Антипаттерны (запрещено)

### 5.1. Использование `any`

```tsx
// ❌ ЗАПРЕЩЕНО:
catch (error: any) {
  toast({ description: error.response?.data?.detail });
}
```
**Почему плохо:** Отключает проверку типов, линтер выдаёт предупреждение `unexpected any`, возможна ошибка при обращении к несуществующим полям.

### 5.2. Прямое обращение без приведения

```tsx
// ❌ ЗАПРЕЩЕНО:
catch (error: unknown) {
  toast({ description: error.response.data.detail }); // Ошибка TypeScript!
}
```
**Почему плохо:** TypeScript не позволит обратиться к полям `unknown` напрямую.

### 5.3. Использование `String(error)`

```tsx
// ❌ ЗАПРЕЩЕНО:
catch (error) {
  toast({ description: String(error) }); // Выведет "[object Object]"
}
```
**Почему плохо:** Пользователь увидит бесполезный текст `"[object Object]"` вместо реального сообщения об ошибке.

### 5.4. Игнорирование ошибки

```tsx
// ❌ ЗАПРЕЩЕНО:
catch (error: unknown) {
  // Ничего не делаем — ошибка проглочена
}
```
**Почему плохо:** Пользователь не узнает о проблеме, отладка невозможна.

---

## 6. Обоснование архитектурных решений

### 6.1. Почему `unknown`, а не `any`?
- **`any`** отключает проверку типов полностью — это "дыра" в типобезопасности
- **`unknown`** заставляет TypeScript требовать явной проверки или приведения типа перед использованием
- Линтер (например, `@typescript-eslint/no-explicit-any`) не выдаёт предупреждений на `unknown`

### 6.2. Почему приведение типа, а не `instanceof`?
- Ошибки от Axios/Orval — это обычные объекты, а не экземпляры классов
- `instanceof Error` не даст доступа к структуре `response.data.detail`
- Приведение через `as` — стандартный и декларативный способ работы с API-ошибками

### 6.3. Почему все поля опциональные?
- Сетевые ошибки не имеют `response`
- Ошибки валидации могут иметь другую структуру
- Опциональность защищает от `TypeError: Cannot read property 'data' of undefined`

---

## 7. Универсальная утилита (опционально)

Если в проекте много мест с обработкой ошибок, можно вынести приведение типа в утилиту:

```tsx
// src/lib/utils/error.ts
export const extractErrorMessage = (error: unknown, fallback = "Произошла ошибка"): string => {
  const err = error as { response?: { data?: { detail?: string } } };
  return err?.response?.data?.detail || fallback;
};

// Использование:
catch (error: unknown) {
  toast({
    variant: "destructive",
    title: "Ошибка",
    description: extractErrorMessage(error, "Не удалось сохранить"),
  });
}
```

Это уменьшает дублирование кода и централизует логику извлечения сообщений.

---

## 8. Чек-лист для проверки

При обработке ошибки убедитесь, что:

- [ ] Тип параметра `error` явно указан как `unknown` (не `any`, не пропущен)
- [ ] Выполнено безопасное приведение типа через `as { response?: { data?: { detail?: string } } }`
- [ ] Используется optional chaining (`?.`) при доступе к полям
- [ ] Есть fallback-сообщение на случай, если `detail` отсутствует
- [ ] Пользователю показывается `toast` с `variant: "destructive"`
- [ ] Ошибка не проглочена (есть хотя бы логирование или уведомление)
- [ ] Линтер не выдаёт предупреждений

---

## 9. Связь с другими правилами

- **Правило №24** (invalidateQueries ДО закрытия) — обработка ошибок не должна нарушать порядок
- **Правило №25** (refetch после удаления) — при ошибке удаления НЕ вызываем `refetch`
- **Правило №35** (вынесение модалок) — обработка ошибок инкапсулирована внутри модалки
- **Правило №37** (синхронизация формы) — при ошибке сохранения форма НЕ сбрасывается

---

## 10. Пример полного обработчика (эталон)

```tsx
const handleSave = async (data: FormData) => {
  try {
    // 1. Попытка сохранения
    await mutation.mutateAsync({ data });
    
    // 2. Успех: инвалидация, закрытие, сброс, callback
    await queryClient.invalidateQueries({ queryKey: ["items"] });
    onOpenChange(false);
    reset(CREATE_DEFAULTS);
    await onSaved();
  } catch (error: unknown) {
    // 3. Ошибка: безопасное извлечение сообщения
    const err = error as { response?: { data?: { detail?: string } } };
    toast({
      variant: "destructive",
      title: "Ошибка сохранения",
      description: err?.response?.data?.detail || "Не удалось сохранить запись",
    });
    // 4. Форма НЕ сбрасывается, модалка НЕ закрывается — пользователь может исправить
  }
};
```

---

Это правило является **строгим стандартом** для обработки ошибок на фронтенде. Любое использование `any` в блоках `catch` или `onError` будет считаться нарушением архитектуры и должно быть исправлено.