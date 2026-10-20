# Правило №39: Паттерн «Название-ссылка» с пессимистической блокировкой редактирования

**Суть:** В таблицах документных модулей (реализующих контракт документов из ТЗ §3.3 + жизненный цикл) колонка «Название» оформляется как **кликабельная ссылка**, открывающая форму редактирования. Отдельная кнопка «Редактировать» (иконка-карандаш) в колонке «Действия» **не требуется**. Открытие формы сопровождается **атомарным захватом пессимистической блокировки** (`POST /{doctype}/{id}/lock`). Если документ уже заблокирован другим пользователем (423), форма открывается в режиме **только для чтения** (`readOnly`) с визуальным предупреждением. При закрытии формы блокировка освобождается (`DELETE /{doctype}/{id}/lock`).

Правило применяется к модулям, наследующим `DocumentLifecycleMixin` (поле `editing_by_user_id` + `editing_since` + `@property is_editing_locked`). Эталонная реализация — модуль `notes`.

---

## Строгие требования

### 1. Колонка «Название» — кликабельная ссылка

1.1. Название документа в первой колонке таблицы оборачивается в `<button type="button">` (не `<a>` без `href`, не `<div onClick>`).

1.2. Обязательные CSS-классы ссылки:
```
text-left text-blue-600 hover:text-blue-800 hover:underline underline-offset-2 font-medium cursor-pointer w-full truncate block focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 rounded-sm transition-colors
```

1.3. Обязательный атрибут `title={item.title}` для показа полного текста при обрезании.

1.4. Иконка замка `🔒` (`Lock` из `lucide-react`) отображается **рядом с названием**, если `item.is_editing_locked === true`.

### 2. Колонка «Действия» — только вторичные операции

2.1. Кнопка «Редактировать» (`<Pencil>`) **удалена** из колонки «Действия».

2.2. В колонке «Действия» остаются только деструктивные и специфичные операции: удаление (`<Trash2>`), делегирование, копирование.

2.3. Ширина колонки «Действия» уменьшается (обычно до `80px` вместо `140px`).

### 3. Открытие формы с блокировкой

3.1. При клике на название **сначала** проверяется `item.is_editing_locked`:
- если `true` → сразу открыть в `readOnly` (не вызывать `/lock`)
- если `false` → вызвать `POST /{doctype}/{id}/lock`

3.2. При успешном захвате (200) — открыть модалку в режиме редактирования (`readOnly={false}`).

3.3. При 423 ошибке — открыть модалку в режиме **только чтения** (`readOnly={true}`) + показать деструктивный toast с пояснением.

3.4. При иных ошибках — показать деструктивный toast, модалку **не открывать**.

### 4. Режим «только чтение» в модалке

4.1. Модалка принимает обязательный проп `readOnly?: boolean` (по умолчанию `false`).

4.2. Все поля формы получают `disabled={readOnly}`.

4.3. При `readOnly === true`:
- В заголовке: «Просмотр {сущность} (только чтение)»
- Показывается `<Alert variant="destructive">` с текстом о блокировке
- Кнопка «Сохранить» **не рендерится**
- Кнопка «Отмена» заменяется на «Закрыть»

4.4. В `onSubmit` обязательна защита: `if (readOnly) return;`

### 5. Освобождение блокировки

5.1. При закрытии модалки, если блокировка была захвачена (`!readOnly`), вызывается `DELETE /{doctype}/{id}/lock`.

5.2. Ошибки освобождения **игнорируются** (таймаут 30 минут всё равно снимет блокировку).

5.3. После освобождения состояние `editingNote` сбрасывается в `null`, `readOnly` в `false`.

### 6. Обработка ошибок в модалке

6.1. При сохранении (`PUT`) обработка статусов:
- `409` → «Документ был изменён другим пользователем. Обновите страницу…»
- `423` → «Документ сейчас редактируется другим пользователем…»
- иные → `detail` из ответа или дефолтное сообщение

---

## ✅ ПРАВИЛЬНО

### Фрагмент страницы списка (`NotesPage.tsx`)

```tsx
// ✅ Состояние для режима только чтения
const [readOnly, setReadOnly] = useState(false);

const acquireLockMutation = useAcquireNoteLockNotesNoteIdLockPost();
const releaseLockMutation = useReleaseNoteLockNotesNoteIdLockDelete();

// ✅ Открытие модалки с проверкой и захватом блокировки
const openEdit = async (item: NoteResponseSchema) => {
  setEditingNote(item);

  // 1. Если документ уже заблокирован — сразу открываем в readOnly
  if (item.is_editing_locked) {
    setReadOnly(true);
    setIsModalOpen(true);
    toast({
      variant: "destructive",
      title: "Документ занят",
      description: "Документ редактируется другим пользователем. Открыт в режиме только для чтения.",
    });
    return;
  }

  // 2. Документ свободен — пытаемся захватить блокировку
  try {
    await acquireLockMutation.mutateAsync({ noteId: item.id });
    setReadOnly(false);
    setIsModalOpen(true);
  } catch (error: unknown) {
    const err = error as { response?: { status?: number; data?: { detail?: string } } };

    if (err?.response?.status === 423) {
      // Блокировка захвачена между проверкой и вызовом — открываем в readOnly
      setReadOnly(true);
      setIsModalOpen(true);
      toast({
        variant: "destructive",
        title: "Документ занят",
        description: "Документ редактируется другим пользователем. Открыт в режиме только для чтения.",
      });
    } else {
      toast({
        variant: "destructive",
        title: "Ошибка блокировки",
        description: err?.response?.data?.detail || "Не удалось заблокировать документ",
      });
    }
  }
};

// ✅ Освобождение блокировки при закрытии модалки
const handleModalClose = async (open: boolean) => {
  if (!open && editingNote && !readOnly) {
    try {
      await releaseLockMutation.mutateAsync({ noteId: editingNote.id });
    } catch {
      // Игнорируем ошибки освобождения (таймаут всё равно снимет)
    }
  }

  setIsModalOpen(open);
  if (!open) {
    setEditingNote(null);
    setReadOnly(false);
  }
};
```

### Фрагмент таблицы (`NotesPage.tsx`)

```tsx
<TableBody>
  {items.map((item) => (
    <TableRow
      key={item.id}
      className={
        highlightedNoteId === item.id
          ? "bg-yellow-100 dark:bg-yellow-900/30 transition-colors duration-300"
          : ""
      }
    >
      {/* ✅ Название как кликабельная ссылка */}
      <TableCell style={{ width: widths.title }} className="py-1 align-top overflow-hidden">
        <button
          type="button"
          onClick={() => openEdit(item)}
          className="text-left text-blue-600 hover:text-blue-800 hover:underline underline-offset-2 font-medium cursor-pointer w-full truncate block focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 rounded-sm transition-colors"
          title={item.title}
        >
          {item.is_editing_locked && (
            <Lock className="inline h-3 w-3 mr-1 text-amber-500" />
          )}
          {item.title}
        </button>
      </TableCell>

      {/* Другие колонки: номер, дата, статус, раздел, обновлено */}
      {/* ... */}

      {/* ✅ Колонка Действия — только удаление */}
      <TableCell style={{ width: widths.actions }} className="py-1 align-top">
        <div className="flex gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-destructive hover:text-destructive"
            onClick={() => setDeleteNoteId(item.id)}
            title="Удалить"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </TableCell>
    </TableRow>
  ))}
</TableBody>
```

### Фрагмент модалки (`EditNoteModal.tsx`)

```tsx
interface EditNoteModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData: NoteResponseSchema | null;
  onSaved: (id: string, title?: string) => Promise<void>;
  readOnly?: boolean;
}

export const EditNoteModal = ({
  open,
  onOpenChange,
  initialData,
  onSaved,
  readOnly = false,
}: EditNoteModalProps) => {
  // ...

  const onSubmit = async (formData: NoteFormData) => {
    if (readOnly) return; // ✅ Защита от сохранения в режиме только чтения
    // ... логика сохранения
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {readOnly
              ? "Просмотр заметки (только чтение)"
              : initialData
              ? "Редактировать заметку"
              : "Новая заметка"}
          </DialogTitle>
        </DialogHeader>

        {/* ✅ Предупреждение в режиме только чтения */}
        {readOnly && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Документ заблокирован</AlertTitle>
            <AlertDescription>
              Документ редактируется другим пользователем. Вы можете только просматривать данные.
            </AlertDescription>
          </Alert>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" id="note-form">
          {/* Все поля получают disabled={readOnly} */}
          <Controller
            name="title"
            control={control}
            render={({ field }) => (
              <Input
                id="title"
                {...field}
                placeholder="Введите название заметки"
                disabled={readOnly}
              />
            )}
          />
          {/* ... остальные поля */}
        </form>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
            {readOnly ? "Закрыть" : "Отмена"}
          </Button>
          {/* ✅ Кнопка Сохранить не рендерится в режиме только чтения */}
          {!readOnly && (
            <Button
              type="submit"
              form="note-form"
              disabled={isSubmitting || createMutation.isPending || updateMutation.isPending}
            >
              {(isSubmitting || createMutation.isPending || updateMutation.isPending) && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              {initialData ? "Сохранить" : "Создать"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
```

### Обработка ошибок сохранения в модалке

```tsx
} catch (error: unknown) {
  let message = "Не удалось сохранить заметку";
  const err = error as { response?: { data?: { detail?: string }; status?: number } };
  const status = err?.response?.status;
  const detail = err?.response?.data?.detail;

  if (status === 409) {
    message = "Документ был изменён другим пользователем. Обновите страницу и попробуйте снова.";
  } else if (status === 423) {
    message = "Документ сейчас редактируется другим пользователем. Попробуйте позже.";
  } else if (detail) {
    message = detail;
  }

  toast({
    variant: "destructive",
    title: "Ошибка сохранения",
    description: message,
  });
}
```

---

## ❌ НЕПРАВИЛЬНО

```tsx
{/* ❌ ОШИБКА 1: Отдельная кнопка "Редактировать" в колонке "Действия" */}
<TableCell>
  <div className="truncate">{item.title}</div>
</TableCell>
<TableCell>
  <Button onClick={() => openEdit(item)}>
    <Pencil className="h-4 w-4" />
  </Button>
</TableCell>

{/* ❌ ОШИБКА 2: Название как <div> или <a> без href */}
<div onClick={() => openEdit(item)} className="cursor-pointer">
  {item.title}
</div>
<a onClick={() => openEdit(item)}>{item.title}</a>

{/* ❌ ОШИБКА 3: Захват блокировки без проверки is_editing_locked */}
const openEdit = async (item: NoteResponseSchema) => {
  // Всегда вызываем /lock, даже если документ уже заблокирован
  // → лишний запрос, лишний шанс на гонку
  await acquireLockMutation.mutateAsync({ noteId: item.id });
  setIsModalOpen(true);
};

{/* ❌ ОШИБКА 4: При 423 показываем ошибку и не открываем модалку */}
} catch (error: unknown) {
  const err = error as { response?: { status?: number } };
  if (err?.response?.status === 423) {
    // ❌ Пользователь не может даже просмотреть документ
    toast({ variant: "destructive", title: "Документ занят" });
    return;
  }
}

{/* ❌ ОШИБКА 5: Модалка не имеет пропа readOnly */}
<EditNoteModal
  open={isModalOpen}
  onOpenChange={setIsModalOpen}
  initialData={editingNote}
  onSaved={handleSaved}
  // Нет readOnly — нельзя открыть в режиме только чтения
/>

{/* ❌ ОШИБКА 6: В режиме readOnly кнопка "Сохранить" всё равно рендерится */}
<DialogFooter>
  <Button type="submit" form="note-form" disabled={readOnly}>
    Сохранить
  </Button>
</DialogFooter>

{/* ❌ ОШИБКА 7: Блокировка не освобождается при закрытии модалки */}
const handleModalClose = (open: boolean) => {
  setIsModalOpen(open);
  // Нет вызова DELETE /{doctype}/{id}/lock
};

{/* ❌ ОШИБКА 8: Ошибка освобождения блокировки показывается пользователю */}
try {
  await releaseLockMutation.mutateAsync({ noteId: editingNote.id });
} catch (error: unknown) {
  // ❌ Не нужно показывать пользователю ошибки освобождения
  toast({ variant: "destructive", title: "Ошибка освобождения блокировки" });
}

{/* ❌ ОШИБКА 9: Отсутствие защиты от сохранения в режиме только чтения */}
const onSubmit = async (formData: NoteFormData) => {
  // Нет проверки `if (readOnly) return;`
  // Если пользователь каким-то образом отправит форму — сохранение пройдёт
  await updateMutation.mutateAsync({ ... });
};
```

---

## Обоснование

### Почему название-ссылка, а не кнопка-карандаш?

| Аспект | Кнопка-карандаш | Название-ссылка |
|--------|-----------------|-----------------|
| **Горизонтальное пространство** | Занимает 40-60px в колонке «Действия» | Экономит место — колонка «Действия» сокращается до 80px |
| **Ментальная модель** | Пользователь ищет кнопку в правой части | Пользователь кликает на сам объект (естественно, как в файловых менеджерах) |
| **Скорость взаимодействия** | Два шага: найти строку → найти кнопку | Один шаг: кликнуть на название |
| **Доступность** | `<button>` с `title` | `<button>` с `title` + `focus:ring` для клавиатурной навигации |

### Почему пессимистическая блокировка при открытии?

| Аспект | Без блокировки | С блокировкой |
|--------|----------------|---------------|
| **Конфликт** | Пользователь узнаёт о конфликте при сохранении (409) | Пользователь узнаёт о конфликте сразу при открытии (423 → readOnly) |
| **Потеря работы** | 10 минут редактирования могут быть потеряны | Пользователь сразу видит, что документ занят, и не тратит время |
| **Визуальная индикация** | Нет | Иконка 🔒 в списке + предупреждение в модалке |
| **Атомарность** | Нет гарантии | `UPDATE ... WHERE ... RETURNING` гарантирует атомарный захват |

### Почему режим «только чтение», а не запрет открытия?

Пользователь может **хотеть просмотреть** документ, даже если не может его редактировать. Запрет открытия (показ только ошибки) ухудшает UX. Режим `readOnly` позволяет:
- Ознакомиться с содержимым документа
- Понять, кто сейчас редактирует (через иконку замка в списке)
- Вернуться позже, когда блокировка истечёт (таймаут 30 минут)

### Связь с другими правилами

| Правило | Связь |
|---------|-------|
| №11 (Компактные таблицы) | `py-1 align-top truncate` для ячейки названия |
| №13 (Фиксированная ширина) | `style={{ width: widths.title }}` для колонки |
| №17/23 (Подсветка строки) | Работает вместе с подсветкой |
| №29 (Изменяемая ширина) | Колонка «Название» участвует в ресайзе |
| №35 (Вынесение модалок) | `readOnly` — это дополнительный проп к стандартному контракту |
| №36 (Безопасная обработка ошибок) | `error as { response?: ... }` с `unknown` |
| Backend №31 (CRUDBase) | CRUD-методы блокировки наследуют паттерн |
| ТЗ §3.3 | Требует `DocumentLifecycleMixin` в модели |
| ТЗ §12.2 | Аудит операций с документом |

---

## Чек-лист применения

Перед коммитом документного модуля проверьте:

- [ ] Колонка «Название» — `<button type="button">` со всеми ссылочными классами
- [ ] Иконка `Lock` отображается при `item.is_editing_locked`
- [ ] Кнопка «Редактировать» удалена из колонки «Действия»
- [ ] Ширина колонки «Действия» уменьшена (~80px)
- [ ] `openEdit` проверяет `item.is_editing_locked` перед вызовом `/lock`
- [ ] При 423 модалка открывается в `readOnly` с деструктивным toast
- [ ] При иных ошибках модалка не открывается
- [ ] Модалка принимает проп `readOnly?: boolean`
- [ ] Все поля формы имеют `disabled={readOnly}`
- [ ] При `readOnly` рендерится `<Alert variant="destructive">`
- [ ] Кнопка «Сохранить» не рендерится при `readOnly`
- [ ] В `onSubmit` есть защита `if (readOnly) return;`
- [ ] При закрытии модалки вызывается `DELETE /{doctype}/{id}/lock` (если блокировка была захвачена)
- [ ] Ошибки освобождения блокировки игнорируются
- [ ] В `catch` обработки сохранения обрабатываются статусы 409 и 423
- [ ] Бэкенд: `save_with_version` проверяет `editing_by_user_id` перед сохранением
- [ ] Бэкенд: `mark_deleted` проверяет `editing_by_user_id` перед удалением

---

## Область применения

Правило №39 применяется **только** к модулям, реализующим контракт документов (ТЗ §3.3 + жизненный цикл):
- ✅ `notes` (эталон)
- ✅ будущие типы документов (`invoices`, `contracts`, `deals` и т.д.)

**Не применяется** к справочникам и административным модулям:
- ❌ `doctypes`, `roles`, `tenants`, `users`, `domains`, `sections`, `permissions` — для них остаётся паттерн с кнопкой-карандашом, так как у них нет пессимистической блокировки и сценария «документ занят»

---

Это правило является логическим продолжением Правил №35 и №37 и полностью соответствует ТЗ версии 2.0. Любое отклонение при реализации документного модуля будет считаться нарушением архитектуры.