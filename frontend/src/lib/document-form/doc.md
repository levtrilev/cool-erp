Что нужно для следующей модалки (например, EditInvoiceModal)
Создать InvoiceCustomFields.tsx со своими полями.
Создать schemas.ts с invoiceFormSchema (расширяет DocumentBaseFormValues<InvoiceUpdateSchemaDocStatus> своими полями) и CREATE_DEFAULTS.
Написать EditInvoiceModal.tsx по образцу выше: подставить мутации, схему, entityLabel, formId, buildCopyTitle.
Готово. Типовые поля, сохранение, ошибки, блокировки, режимы — из каркаса.

Архитектура:
Бизнес-часть (знает только о своих полях)
  EditNoteModal.tsx       → ~50 строк: мутации + конфиг + <DocumentFormShell>
  NoteCustomFields.tsx    → ~40 строк: только title и content
  schemas.ts              → схема, дефолты (без изменений логики)

Каркас (не знает о конкретной сущности)
  src/lib/document-form/
    documentFormTypes.ts    → базовые типы значений формы и пропсов
    documentFormHelpers.ts  → parseTags/joinTags/mapEnumByValue + метки статусов
    useDocumentSave.ts      → форма, режимы, сохранение, ошибки 409/423, порядок действий
    DocumentFormShell.tsx   → Dialog + типовые поля + версия/блокировка + футер

Файл 1. src/lib/document-form/documentFormTypes.ts
Базовый интерфейс значений формы документа. Параметризован типом статуса, чтобы каждая сущность подставляла свой enum (Решение 2).

Файл 2. src/lib/document-form/documentFormHelpers.ts
Чистые функции без состояния. Сюда переносятся parseTags, joinTags, маппинг enum по значению и общие метки статусов (единый контракт DocStatus).

Файл 3. src/lib/document-form/useDocumentSave.ts
Хук инкапсулирует: режимы (создание/редактирование/копирование), синхронизацию формы при открытии (Правило №37), ветвление сохранения, обработку 409/423, строгий порядок invalidate → close → reset → onSaved (Правило №24).
Бизнес-код передаёт только мутации, схему, дефолты и функции сборки полезной нагрузки.

Файл 4. src/lib/document-form/DocumentFormShell.tsx
UI-каркас: Dialog с resize/drag, заголовок по режиму, readOnly-алерт, типовые поля документа (раздел, статус, номер, дата, теги), версия/блокировка, футер. Бизнес-поля передаются через children.

Файл 5. src/core/notes/NoteCustomFields.tsx (бизнес-поля)
Только поля, специфичные для заметок: title и content. Больше ничего.

Файл 6. src/core/notes/EditNoteModal.tsx (рефакторинг)
Тонкая бизнес-модалка. Знает только о мутациях заметок, схеме и своих полях. Вся типовая логика — в каркасе.

Что получилось (см таблицу в csv)
До рефакторинга
После рефакторинга
EditNoteModal.tsx ~450 строк
~120 строк
Типовые поля прямо в модалке
В DocumentFormShell
Логика сохранения в onSubmit
В useDocumentSave
parseTags/joinTags/mapDocStatus локально
В documentFormHelpers
Бизнес-поля перемешаны с типовыми
NoteCustomFields отдельно
Бизнес-часть (EditNoteModal + NoteCustomFields + schemas) теперь знает только о title, content и мутациях заметок. Всё остальное — каркас.