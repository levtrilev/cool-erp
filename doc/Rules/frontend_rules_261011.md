Изложи сразу все правила frontend, но при этом каждое правило максимально подробно с примерами кода

# 📜 ПОЛНЫЙ СВОД ПРАВИЛ FRONTEND (Cool ERP)

## Правило №9: Orval-хуки для API-запросов

**Суть:** Использование автоматически сгенерированных Orval-хуков вместо ручных вызовов axios/fetch для обеспечения типобезопасности и единообразия.

**Строгие требования:**
1. Все запросы к API выполняются **только** через Orval-сгенерированные хуки: `useGetXxx`, `useCreateXxx`, `useUpdateXxx`, `useDeleteXxx`.
2. Для разовых вызовов (например, в `handleSaved`) используются Orval-функции: `getXxx`, `createXxx` и т.д.
3. Запрещено использовать прямой `axios.get()` или `fetch()` для вызовов API.

**✅ ПРАВИЛЬНО:**
```tsx
import {
  useGetDoctypesDoctypesGet,
  useCreateDoctypeDoctypesPost,
  useUpdateDoctypeDoctypesDoctypeIdPut,
  useDeleteDoctypeDoctypesDoctypeIdDelete,
} from "@/api/generated/doctypes/doctypes";

import { getDoctypesDoctypesGet } from "@/api/generated/doctypes/doctypes";

export const DoctypesPage = () => {
  // ✅ Orval-хук для получения списка
  const { data, isLoading, refetch } = useGetDoctypesDoctypesGet({
    skip: (page - 1) * limit,
    limit,
    search: search || undefined,
  });

  // ✅ Orval-хуки для мутаций
  const createMutation = useCreateDoctypeDoctypesPost();
  const updateMutation = useUpdateDoctypeDoctypesDoctypeIdPut();
  const deleteMutation = useDeleteDoctypeDoctypesDoctypeIdDelete();

  const handleSaved = async (id: string) => {
    // ✅ Orval-функция для разового вызова
    const fullList = await getDoctypesDoctypesGet({ limit: 1000, skip: 0 });
    // ...
  };
};
```

**❌ НЕПРАВИЛЬНО:**
```tsx
import axios from "axios";

// ❌ Запрещено: прямой вызов axios
const { data } = await axios.get("/api/doctypes", { params: { skip, limit } });

// ❌ Запрещено: ручной fetch
const response = await fetch(`/api/doctypes?skip=${skip}&limit=${limit}`);
```

**Обоснование:** Orval генерирует типобезопасные хуки на основе OpenAPI-спецификации. Это гарантирует, что типы данных на фронтенде всегда совпадают с бэкендом, а при изменении API автоматически обновляются все вызовы.

---

## Правило №10: Использование существующих моделей

**Суть:** Запрет на создание избыточных таблиц или моделей, если в проекте уже есть подходящая сущность.

**Строгие требования:**
1. Перед созданием новой M2M-таблицы или модели проверить, существует ли уже подходящая сущность.
2. Использовать существующие модели с явными связями `relationship` и `cascade="all, delete-orphan"`.
3. Не создавать абстрактные связующие таблицы (например, `role_doctypes`), если есть полноценная модель `PermissionModel`.

**✅ ПРАВИЛЬНО:**
```python
# Backend: Использование существующей PermissionModel
class RoleModel(Base):
    __tablename__ = "roles"
    permissions = relationship(
        "PermissionModel",
        back_populates="role",
        lazy="selectin",
        cascade="all, delete-orphan"  # ✅ Каскадное удаление
    )

# Frontend: Работа с Permission через существующие эндпоинты
const { data: permissions } = useGetPermissionsPermissionsGet({
  role_id: roleId
});
```

**❌ НЕПРАВИЛЬНО:**
```python
# ❌ Создание избыточной M2M-таблицы
role_doctypes = Table(
    "role_doctypes", Base.metadata,
    Column("role_id", ForeignKey("roles.id")),
    Column("doctype_id", ForeignKey("doctypes.id"))
)
```

**Обоснование:** `PermissionModel` уже содержит все необходимые поля (флаги доступа, теги и т.д.). Создание дополнительной таблицы приведёт к дублированию данных и усложнит поддержку.

---

## Правило №11: Компактные таблицы

**Суть:** Оптимизация вертикального пространства в таблицах для отображения большего количества данных без прокрутки.

**Строгие требования:**
1. Для ячеек таблицы использовать классы `py-1` (маленький вертикальный padding) и `align-top` (выравнивание по верху).
2. Для текста с возможностью переполнения использовать `overflow-hidden` и `truncate`.
3. Заголовок таблицы должен иметь фиксированную высоту: `h-10`.

**✅ ПРАВИЛЬНО:**
```tsx
<Table className="table-fixed w-full">
  <TableHeader>
    <TableRow className="h-10 hover:bg-transparent">
      <TableHead>Название</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    {items.map((item) => (
      <TableRow key={item.id}>
        {/* ✅ Компактная ячейка с выравниванием по верху */}
        <TableCell className="py-1 align-top overflow-hidden">
          <div title={item.name} className="block w-full truncate">
            {item.name}
          </div>
        </TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>
```

**❌ НЕПРАВИЛЬНО:**
```tsx
{/* ❌ Слишком большие отступы, нет выравнивания */}
<TableCell className="p-4">
  <div>{item.name}</div>
</TableCell>
```

**Обоснование:** Компактные таблицы позволяют отображать 15-20 строк на экране без прокрутки, что критично для ERP-систем с большими объёмами данных.

---

## Правило №12: Поиск через form

**Суть:** Реализация поиска через HTML-форму для поддержки отправки по Enter и корректной работы с браузерными функциями.

**Строгие требования:**
1. Поиск реализуется через `<form onSubmit>`, а не через `onChange` на input.
2. Используются два отдельных состояния: `searchInput` (текущий ввод) и `search` (значение для API).
3. При отправке формы вызывается `e.preventDefault()` и обновление состояния `search`.

**✅ ПРАВИЛЬНО:**
```tsx
const [searchInput, setSearchInput] = useState("");
const [search, setSearch] = useState("");

<form
  onSubmit={(e) => {
    e.preventDefault();
    setSearch(searchInput); // ✅ Обновляем только при отправке
    setPage(1); // ✅ Сброс пагинации
  }}
  className="flex gap-2 mb-2"
>
  <Input
    value={searchInput}
    onChange={(e) => setSearchInput(e.target.value)} // ✅ Обновляем только локальное состояние
    placeholder="Поиск..."
  />
  <Button type="submit">Найти</Button>
</form>

// ✅ Используем search для запроса
const { data } = useGetDoctypesDoctypesGet({
  search: search || undefined,
});
```

**❌ НЕПРАВИЛЬНО:**
```tsx
// ❌ Поиск на каждое нажатие клавиши
<Input
  onChange={(e) => {
    setSearch(e.target.value); // ❌ Запрос к API на каждый символ
  }}
/>
```

**Обоснование:** Разделение состояний предотвращает избыточные запросы к API и позволяет пользователю полностью ввести поисковый запрос перед отправкой.

---

## Правило №13: Фиксированная ширина таблицы

**Суть:** Использование `table-fixed` для стабильного отображения колонок и предотвращения "прыжков" при загрузке данных.

**Строгие требования:**
1. Таблица должна иметь классы `table-fixed w-full`.
2. Ширина колонок задаётся через `style={{ width: widths.columnName }}`.
3. Для текста с переполнением использовать `overflow-hidden` и `truncate`.

**✅ ПРАВИЛЬНО:**
```tsx
<Table className="table-fixed w-full">
  <TableHeader>
    <TableRow>
      <TableHead style={{ width: widths.doctype }}>Код</TableHead>
      <TableHead style={{ width: widths.doctype_name }}>Название</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    {items.map((item) => (
      <TableRow key={item.id}>
        <TableCell style={{ width: widths.doctype }} className="overflow-hidden">
          <div className="truncate">{item.doctype}</div>
        </TableCell>
      </TableRow>
    ))}
  </TableBody>
</Table>
```

**❌ НЕПРАВИЛЬНО:**
```tsx
{/* ❌ Автоматическая ширина колонок, "прыжки" при загрузке */}
<Table>
  <TableHead>Код</TableHead>
</Table>
```

**Обоснование:** `table-fixed` гарантирует, что ширина колонок не меняется в зависимости от содержимого, что улучшает UX и позволяет корректно работать с `useResizableColumns`.

---

## Правило №14: Sticky-заголовки таблицы

**Суть:** Закрепление заголовков таблицы при вертикальной прокрутке для улучшения навигации по большим спискам.

**Строгие требования:**
1. Заголовок таблицы (`TableHeader`) должен быть закреплён через CSS-класс `sticky top-0`.
2. Фон заголовка должен совпадать с фоном страницы: `bg-background`.
3. Z-index заголовка должен быть выше содержимого: `z-10`.

**✅ ПРАВИЛЬНО:**
```tsx
<Table>
  <TableHeader className="sticky top-0 bg-background z-10 shadow-sm">
    <TableRow>
      <TableHead>Название</TableHead>
    </TableRow>
  </TableHeader>
  <TableBody>
    {/* Содержимое */}
  </TableBody>
</Table>
```

**❌ НЕПРАВИЛЬНО:**
```tsx
{/* ❌ Заголовок прокручивается вместе с таблицей */}
<Table>
  <TableHeader>
    <TableRow>
      <TableHead>Название</TableHead>
    </TableRow>
  </TableHeader>
</Table>
```

**Обоснование:** Sticky-заголовки позволяют пользователю видеть названия колонок даже при прокрутке на 100+ строк вниз.

---

## Правило №16: Удаление через AlertDialog

**Суть:** Обязательное подтверждение удаления для предотвращения случайных потерь данных.

**Строгие требования:**
1. Удаление всегда требует подтверждения через `AlertDialog`.
2. В диалоге должно быть чёткое описание последствий удаления.
3. Кнопка подтверждения должна быть стилизована как деструктивная: `bg-destructive`.
4. Во время выполнения мутации кнопка должна быть заблокирована: `disabled={mutation.isPending}`.

**✅ ПРАВИЛЬНО:**
```tsx
const [deleteDoctypeId, setDeleteDoctypeId] = useState<string | null>(null);
const deleteMutation = useDeleteDoctypeDoctypesDoctypeIdDelete();

const handleDelete = async () => {
  if (!deleteDoctypeId) return;
  try {
    await deleteMutation.mutateAsync({ doctypeId: deleteDoctypeId });
    await refetch();
    setDeleteDoctypeId(null);
    toast({ title: "Удалено" });
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } } };
    toast({
      variant: "destructive",
      title: "Ошибка удаления",
      description: err?.response?.data?.detail || "Не удалось удалить",
    });
  }
};

<AlertDialog open={!!deleteDoctypeId} onOpenChange={(open) => !open && setDeleteDoctypeId(null)}>
  <AlertDialogContent>
    <AlertDialogHeader>
      <AlertDialogTitle>Удалить тип документа?</AlertDialogTitle>
      <AlertDialogDescription>
        Это действие нельзя отменить. Связанные полномочия могут быть затронуты.
      </AlertDialogDescription>
    </AlertDialogHeader>
    <AlertDialogFooter>
      <AlertDialogCancel>Отмена</AlertDialogCancel>
      <AlertDialogAction
        onClick={handleDelete}
        disabled={deleteMutation.isPending}
        className="bg-destructive text-destructive-foreground"
      >
        {deleteMutation.isPending ? <Loader2 className="animate-spin" /> : "Удалить"}
      </AlertDialogAction>
    </AlertDialogFooter>
  </AlertDialogContent>
</AlertDialog>
```

**❌ НЕПРАВИЛЬНО:**
```tsx
{/* ❌ Удаление без подтверждения */}
<Button onClick={() => deleteMutation.mutate({ doctypeId: item.id })}>
  <Trash2 />
</Button>
```

**Обоснование:** В ERP-системах удаление данных может привести к потере критичной информации. Подтверждение защищает от случайных кликов.

---

## Правило №17: Подсветка строки

**Суть:** Временная визуальная подсветка успешно изменённой/созданной строки для улучшения обратной связи.

**Строгие требования:**
1. Подсветка реализуется через `useEffect` с `setTimeout`.
2. Длительность подсветки: 3 секунды.
3. Цвет подсветки: `bg-yellow-100 dark:bg-yellow-900/30`.
4. Плавный переход: `transition-colors duration-300`.

**✅ ПРАВИЛЬНО:**
```tsx
const [highlightedDoctypeId, setHighlightedDoctypeId] = useState<string | null>(null);

// ✅ Подсветка через useEffect
useEffect(() => {
  if (highlightedDoctypeId && data?.data?.items?.some((i) => i.id === highlightedDoctypeId)) {
    const timer = setTimeout(() => setHighlightedDoctypeId(null), 3000);
    return () => clearTimeout(timer);
  }
}, [data, highlightedDoctypeId]);

<TableRow
  key={item.id}
  className={
    highlightedDoctypeId === item.id
      ? "bg-yellow-100 dark:bg-yellow-900/30 transition-colors duration-300"
      : ""
  }
>
  {/* Содержимое */}
</TableRow>
```

**❌ НЕПРАВИЛЬНО:**
```tsx
{/* ❌ Подсветка без автоматического сброса */}
<TableRow className="bg-yellow-100">
  {/* Никогда не сбросится */}
</TableRow>
```

**Обоснование:** Временная подсветка помогает пользователю быстро найти только что сохранённую запись в списке.

---

## Правило №18: Умная навигация

**Суть:** Автоматический переход на страницу, где находится сохранённая запись, если она не на текущей странице.

**Строгие требования:**
1. После сохранения вызвать `refetch()` для обновления данных.
2. Проверить, есть ли запись на текущей странице.
3. Если нет — загрузить полный список и вычислить целевую страницу.
4. Показать toast с кнопкой "Перейти" для навигации.

**✅ ПРАВИЛЬНО:**
```tsx
const handleSaved = async (id: string) => {
  await refetch();
  const currentItems = data?.data?.items || [];
  
  if (currentItems.some((item) => item.id === id)) {
    // ✅ Запись на текущей странице — просто подсвечиваем
    setHighlightedDoctypeId(id);
    setTimeout(() => setHighlightedDoctypeId(null), 3000);
    toast({ title: "Успешно сохранено" });
  } else {
    // ✅ Записи нет на текущей странице — ищем её
    const fullList = await getDoctypesDoctypesGet({ limit: 1000, skip: 0 });
    const foundIndex = (fullList.data?.items || []).findIndex((item) => item.id === id);
    
    if (foundIndex !== -1) {
      const targetPage = Math.ceil((foundIndex + 1) / limit);
      toast({
        title: "Сохранено",
        description: `На странице ${targetPage}`,
        action: (
          <Button variant="outline" size="sm" onClick={() => setPage(targetPage)}>
            Перейти
          </Button>
        ),
      });
    }
  }
};
```

**❌ НЕПРАВИЛЬНО:**
```tsx
{/* ❌ Пользователь не знает, где находится сохранённая запись */}
await createMutation.mutateAsync({ data });
toast({ title: "Сохранено" });
// Запись может быть на 5-й странице, а пользователь на 1-й
```

**Обоснование:** В ERP-системах с пагинацией пользователь должен быстро находить только что созданные/изменённые записи.

---

## Правило №20: Сброс формы

**Суть:** Гарантия чистого состояния формы при каждом открытии модального окна.

**Строгие требования:**
1. Константа `CREATE_DEFAULTS` объявляется **вне** компонента или в самом его начале.
2. При закрытии модалки вызывается `reset(CREATE_DEFAULTS)`.
3. При открытии модалки в режиме создания также вызывается `reset(CREATE_DEFAULTS)`.
4. При открытии в режиме редактирования вызывается `reset({ ...initialData })`.

**✅ ПРАВИЛЬНО:**
```tsx
// ✅ Константа вне компонента
const CREATE_DEFAULTS: DoctypeFormData = {
  domain_id: "",
  doctype: "",
  doctype_name: "",
  description: "",
  is_active: true,
  tenant_ids: [],
};

export const EditDoctypeModal = ({ open, onOpenChange, initialData }) => {
  const { reset } = useForm<DoctypeFormData>({
    defaultValues: CREATE_DEFAULTS,
  });

  // ✅ Синхронизация при открытии
  useEffect(() => {
    if (open) {
      if (initialData) {
        reset({
          domain_id: initialData.domain_id,
          doctype: initialData.doctype,
          // ...
        });
      } else {
        reset(CREATE_DEFAULTS); // ✅ Сброс при создании
      }
    }
  }, [open, initialData, reset]);

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      reset(CREATE_DEFAULTS); // ✅ Сброс при закрытии
    }
    onOpenChange(newOpen);
  };
};
```

**❌ НЕПРАВИЛЬНО:**
```tsx
{/* ❌ Форма не сбрасывается, остаются данные от предыдущего редактирования */}
<Dialog open={open} onOpenChange={onOpenChange}>
  {/* Нет reset при закрытии */}
</Dialog>
```

**Обоснование:** Без сброса формы при следующем открытии модалки пользователь увидит данные от предыдущей записи, что приведёт к ошибкам.

---

## Правило №22: Разделение состояний поиска

**Суть:** Архитектурное разделение состояния ввода пользователя и состояния, отправляемого в API.

**Строгие требования:**
1. `searchInput` — хранит текущий ввод пользователя (обновляется на каждое нажатие клавиши).
2. `search` — хранит значение, отправляемое в API (обновляется только при отправке формы).
3. Это предотвращает избыточные запросы к API.

**✅ ПРАВИЛЬНО:**
```tsx
const [searchInput, setSearchInput] = useState("");
const [search, setSearch] = useState("");

<form onSubmit={(e) => {
  e.preventDefault();
  setSearch(searchInput); // ✅ Обновляем только при отправке
  setPage(1);
}}>
  <Input
    value={searchInput}
    onChange={(e) => setSearchInput(e.target.value)} // ✅ Локальное состояние
  />
  <Button type="submit">Найти</Button>
</form>

const { data } = useGetDoctypesDoctypesGet({
  search: search || undefined, // ✅ Используем search для API
});
```

**❌ НЕПРАВИЛЬНО:**
```tsx
{/* ❌ Одно состояние для ввода и API */}
const [search, setSearch] = useState("");

<Input onChange={(e) => {
  setSearch(e.target.value); // ❌ Запрос к API на каждый символ
}} />
```

**Обоснование:** Разделение состояний позволяет пользователю полностью ввести поисковый запрос перед отправкой и снижает нагрузку на сервер.

---

## Правило №23: Подсветка сохранённой записи

**Суть:** Визуальное выделение только что сохранённой записи в списке (работает в паре с Правилом №18).

**Строгие требования:**
1. Использовать состояние `highlightedDoctypeId` для хранения ID подсвеченной записи.
2. Применять CSS-класс `bg-yellow-100 dark:bg-yellow-900/30` к строке таблицы.
3. Автоматически сбрасывать подсветку через 3 секунды.

**✅ ПРАВИЛЬНО:**
```tsx
const [highlightedDoctypeId, setHighlightedDoctypeId] = useState<string | null>(null);

const handleSaved = async (id: string) => {
  await refetch();
  setHighlightedDoctypeId(id); // ✅ Подсвечиваем
  setTimeout(() => setHighlightedDoctypeId(null), 3000); // ✅ Сбрасываем через 3 сек
};

<TableRow
  className={
    highlightedDoctypeId === item.id
      ? "bg-yellow-100 dark:bg-yellow-900/30 transition-colors duration-300"
      : ""
  }
>
```

**Обоснование:** Подсветка помогает пользователю быстро найти только что сохранённую запись, особенно после умной навигации.

---

## Правило №24: invalidateQueries ДО закрытия модалки

**Суть:** Строгий порядок действий при успешном сохранении для предотвращения гонок данных.

**Строгие требования:**
1. `invalidateQueries` (или `refetch`) — обновить кэш.
2. `onOpenChange(false)` — закрыть модалку.
3. `reset(CREATE_DEFAULTS)` — сбросить форму.
4. `onSaved(id, name)` — вызвать callback родителя для подсветки.

**✅ ПРАВИЛЬНО:**
```tsx
const onSubmit = async (formData: DoctypeFormData) => {
  try {
    if (editingDoctype) {
      await updateMutation.mutateAsync({
        doctypeId: editingDoctype.id,
        data: formData,
      });
      
      // ✅ Строгий порядок:
      // 1. Инвалидация кэша
      await queryClient.invalidateQueries({ queryKey: ["doctypes"] });
      
      // 2. Закрытие модалки
      onOpenChange(false);
      
      // 3. Сброс формы
      reset(CREATE_DEFAULTS);
      
      // 4. Callback родителя
      await onSaved(editingDoctype.id, formData.doctype_name);
    }
  } catch (error: unknown) {
    // Обработка ошибки
  }
};
```

**❌ НЕПРАВИЛЬНО:**
```tsx
{/* ❌ Неправильный порядок: закрытие до инвалидации */}
onOpenChange(false); // Сначала закрыли
await queryClient.invalidateQueries({ queryKey: ["doctypes"] }); // Потом обновили
// Пользователь может увидеть устаревшие данные
```

**Обоснование:** Инвалидация кэша ДО закрытия модалки гарантирует, что при следующем открытии списка пользователь увидит актуальные данные.

---

## Правило №25: refetch после удаления

**Суть:** Обязательное обновление списка после успешного удаления записи.

**Строгие требования:**
1. После успешного вызова `deleteMutation.mutateAsync()` вызвать `refetch()` или `invalidateQueries`.
2. Сбросить состояние `deleteDoctypeId` в `null`.
3. Показать toast об успешном удалении.

**✅ ПРАВИЛЬНО:**
```tsx
const handleDelete = async () => {
  if (!deleteDoctypeId) return;
  try {
    await deleteMutation.mutateAsync({ doctypeId: deleteDoctypeId });
    await refetch(); // ✅ Обновляем список
    setDeleteDoctypeId(null); // ✅ Сбрасываем состояние
    toast({ title: "Удалено" });
  } catch (error: unknown) {
    const err = error as { response?: { data?: { detail?: string } } };
    toast({
      variant: "destructive",
      title: "Ошибка удаления",
      description: err?.response?.data?.detail || "Не удалось удалить",
    });
  }
};
```

**❌ НЕПРАВИЛЬНО:**
```tsx
{/* ❌ Список не обновляется после удаления */}
await deleteMutation.mutateAsync({ doctypeId });
toast({ title: "Удалено" });
// Запись всё ещё отображается в списке до ручного обновления страницы
```

**Обоснование:** Пользователь ожидает, что удалённая запись мгновенно исчезнет из списка.

---

## Правило №27: ReferenceSelect для справочников (РАСШИРЕННАЯ РЕДАКЦИЯ)

**Суть:** Использование универсального компонента `ReferenceSelect` для всех справочников с обязательным пропом `selectedLabel` для мгновенного отображения значения при редактировании.

**Строгие требования:**
1. **Запрещён** `<Input>` для ручного ввода UUID.
2. Обязательный паттерн адаптера в `fetchFn`, возвращающий `{ items, total }`.
3. Для строковых ID (например, `doctype`) подменять `id` в адаптере.
4. Для дополнительных колонок использовать ключ `column` (не `key`!).
5. **ОБЯЗАТЕЛЬНО:** проп `selectedLabel={initialData?.related_name ?? "Выберите..."}` для мгновенного отображения.
6. **ЗАПРЕЩЕНО:** использовать `prefetchQuery` или `setQueryData` для отображения label.
7. **ЗАПРЕЩЕНО:** изменять файл `ReferenceSelect.tsx`.

**✅ ПРАВИЛЬНО:**
```tsx
<Controller
  name="domain_id"
  control={control}
  render={({ field }) => (
    <ReferenceSelect
      // ✅ Адаптер в fetchFn
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
      // ✅ ОБЯЗАТЕЛЬНО: selectedLabel для мгновенного отображения
      selectedLabel={initialData?.domain_name ?? "Выберите домен..."}
      limit={50}
      heading="Домены"
      // ✅ Ключ "column", не "key"
      columns={[{ column: "description", label: "Описание" }]}
    />
  )}
/>

// ✅ Для строковых ID (doctype):
fetchFn={async (params) => {
  const response = await getDoctypesDoctypesGet(params);
  const items = (response?.data?.items ?? []).map((item) => ({
    ...item,
    id: item.doctype, // ✅ Подмена UUID на строковый код
    name: item.doctype_name || item.doctype, // ✅ Гарантированное поле name
  }));
  return { items, total: response?.data?.total ?? 0 };
}}
```

**❌ НЕПРАВИЛЬНО:**
```tsx
{/* ❌ Ручной ввод UUID */}
<Input {...register("domain_id")} placeholder="UUID домена" />

{/* ❌ Отсутствие selectedLabel */}
<ReferenceSelect
  fetchFn={...}
  value={field.value}
  // Нет selectedLabel — при редактировании поле будет пустым
/>

{/* ❌ Использование prefetchQuery для решения проблемы label */}
useEffect(() => {
  queryClient.prefetchQuery({ queryKey: ["domains"], ... });
}, []);
```

**Обоснование:** Проп `selectedLabel` решает проблему отображения label при редактировании декларативно, без лишних запросов и манипуляций с кэшем.

---

## Правило №29: Изменяемая ширина колонок

**Суть:** Возможность для пользователя настраивать ширину колонок таблицы с сохранением в localStorage.

**Строгие требования:**
1. Использовать хук `useResizableColumns` с массивом колонок.
2. Для каждой колонки указать `initialWidth` и `minWidth`.
3. Применять ширину через `style={{ width: widths.columnName }}`.
4. Добавлять draggable-элемент в заголовок: `onMouseDown={(e) => handleMouseDown("columnName", e)}`.
5. Кнопка "Сбросить ширину" вызывает `resetWidths()`.

**✅ ПРАВИЛЬНО:**
```tsx
const columns = [
  { id: "doctype", initialWidth: 150, minWidth: 100 },
  { id: "doctype_name", initialWidth: 250, minWidth: 150 },
];

const { widths, handleMouseDown, resetWidths } = useResizableColumns(
  columns,
  "doctypes-table-widths" // Ключ для localStorage
);

<Table className="table-fixed w-full">
  <TableHeader>
    <TableRow>
      <TableHead style={{ width: widths.doctype }} className="relative">
        Код
        <div
          className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
          onMouseDown={(e) => handleMouseDown("doctype", e)}
        />
      </TableHead>
    </TableRow>
  </TableHeader>
</Table>

<Button onClick={resetWidths}>Сбросить ширину</Button>
```

**Обоснование:** Пользователи ERP-систем часто работают с разными наборами данных и нуждаются в гибкой настройке интерфейса.

---

## Правило №34: Switch в формах

**Суть:** Использование компонента `Switch` из shadcn/ui для булевых полей с визуальной обратной связью.

**Строгие требования:**
1. Использовать `Controller` из `react-hook-form`.
2. `checked={field.value}`, `onCheckedChange={field.onChange}`.
3. Рядом разместить `Label` с `htmlFor`, меняющий цвет и иконку.
4. В Zod-схеме: `z.boolean().optional()`.
5. В `defaultValues`: `is_active: true`.

**✅ ПРАВИЛЬНО:**
```tsx
// Zod-схема
const doctypeSchema = z.object({
  is_active: z.boolean().optional(),
});

// defaultValues
const CREATE_DEFAULTS = {
  is_active: true,
};

// Компонент
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
```

**❌ НЕПРАВИЛЬНО:**
```tsx
{/* ❌ Использование .default() в Zod */}
is_active: z.boolean().default(true) // ❌ Может вызвать проблемы с типами

{/* ❌ Отсутствие визуальной обратной связи */}
<Switch checked={field.value} onCheckedChange={field.onChange} />
{/* Нет Label с иконкой и цветом */}
```

**Обоснование:** Визуальная обратная связь (цвет, иконка) помогает пользователю мгновенно понять текущее состояние переключателя.

---

## Правило №35: Вынесение модальных окон в отдельный компонент

**Суть:** Модальное окно создания/редактирования всегда выносится в отдельный компонент для разделения ответственности.

**Строгие требования:**
1. Модалка создаётся в отдельном файле: `EditXxxModal.tsx`.
2. Страница списка отвечает только за управление состоянием открытия и передачу `initialData`.
3. Обязательные пропсы: `open`, `onOpenChange`, `initialData`, `onSaved`.
4. Вся логика формы, валидации и мутаций инкапсулирована в модалке.

**✅ ПРАВИЛЬНО:**
```tsx
// DoctypesPage.tsx — только управление состоянием
const [isModalOpen, setIsModalOpen] = useState(false);
const [editingDoctype, setEditingDoctype] = useState<DoctypeResponseSchema | null>(null);

const openEdit = (item: DoctypeResponseSchema) => {
  setEditingDoctype(item);
  setIsModalOpen(true);
};

<EditDoctypeModal
  open={isModalOpen}
  onOpenChange={setIsModalOpen}
  initialData={editingDoctype}
  onSaved={handleSaved}
/>

// EditDoctypeModal.tsx — вся логика формы
interface EditDoctypeModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData: DoctypeResponseSchema | null;
  onSaved: (id: string, name?: string) => Promise<void>;
}

export const EditDoctypeModal = ({ open, onOpenChange, initialData, onSaved }) => {
  const { reset } = useForm<DoctypeFormData>({ defaultValues: CREATE_DEFAULTS });
  
  useEffect(() => {
    if (open) {
      if (initialData) {
        reset({ ...initialData });
      } else {
        reset(CREATE_DEFAULTS);
      }
    }
  }, [open, initialData, reset]);
  
  // Логика мутаций, валидация и т.д.
};
```

**❌ НЕПРАВИЛЬНО:**
```tsx
{/* ❌ Вся логика в DoctypesPage.tsx */}
export const DoctypesPage = () => {
  const { control, handleSubmit, reset } = useForm();
  const createMutation = useCreateDoctype();
  const updateMutation = useUpdateDoctype();
  
  const onSubmit = async (data) => { /* 100+ строк */ };
  
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
```

**Обоснование:** Разделение ответственности улучшает читаемость кода, упрощает тестирование и позволяет переиспользовать модалку в других местах.

---

## Правило №36: Безопасная обработка ошибок

**Суть:** Использование `unknown` вместо `any` в блоках обработки ошибок для строгой типизации.

**Строгие требования:**
1. В `catch` и `onError` **запрещено** использовать `any`.
2. Всегда использовать `unknown` с безопасным приведением типа.
3. Приведение типа: `error as { response?: { data?: { detail?: string } } }`.
4. Использовать optional chaining (`?.`) при доступе к полям.
5. Всегда иметь fallback-сообщение.

**✅ ПРАВИЛЬНО:**
```tsx
// В catch
try {
  await mutation.mutateAsync({ data });
} catch (error: unknown) {
  const err = error as { response?: { data?: { detail?: string } } };
  toast({
    variant: "destructive",
    title: "Ошибка",
    description: err?.response?.data?.detail || "Не удалось выполнить действие",
  });
}

// В onError
updateMutation.mutate(
  { data },
  {
    onError: (error: unknown) => {
      const err = error as { response?: { data?: { detail?: string } } };
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: err?.response?.data?.detail || "Не удалось сохранить",
      });
    },
  }
);
```

**❌ НЕПРАВИЛЬНО:**
```tsx
{/* ❌ Использование any */}
catch (error: any) {
  toast({ description: error.response?.data?.detail });
}

{/* ❌ Прямое обращение без приведения */}
catch (error: unknown) {
  toast({ description: error.response.data.detail }); // ❌ Ошибка TypeScript
}

{/* ❌ String(error) */}
catch (error) {
  toast({ description: String(error) }); // ❌ Выведет "[object Object]"
}
```

**Обоснование:** `unknown` заставляет TypeScript требовать явной проверки типа, что предотвращает ошибки runtime. Fallback-сообщение защищает от случаев, когда `detail` отсутствует.

---

## Правило №37: Синхронизация формы при открытии модалки

**Суть:** Синхронизация данных из `initialData` с формой через `useEffect` без вызова `setState` внутри.

**Строгие требования:**
1. `useEffect` с зависимостями `[open, initialData, reset]`.
2. **ЗАПРЕЩЕНО** вызывать `setState` (например, `setSelectedSectionIds`) внутри `useEffect`.
3. Для производных состояний использовать `watch()` из `react-hook-form` или паттерн с `key`.
4. При `initialData === null` вызывать `reset(CREATE_DEFAULTS)`.

**✅ ПРАВИЛЬНО:**
```tsx
// Вариант 1: Интеграция в форму через watch()
const roleSchema = z.object({
  name: z.string(),
  section_ids: z.array(z.string()).optional(),
});

const { reset, watch } = useForm<RoleFormData>({ defaultValues: CREATE_DEFAULTS });

// ✅ Реактивное получение значения из формы
const selectedSectionIds = watch("section_ids") || [];

useEffect(() => {
  if (open) {
    if (initialData) {
      reset({
        name: initialData.name,
        section_ids: initialData.section_ids || [], // ✅ Форма сама это запомнит
      });
    } else {
      reset(CREATE_DEFAULTS);
    }
  }
}, [open, initialData, reset]);

// Вариант 2: Паттерн с key
<TabsContent value="sections" key={initialData?.id || "new"}>
  <SectionSelector
    selectedIds={selectedSectionIds}
    onChange={setSelectedSectionIds}
  />
</TabsContent>
```

**❌ НЕПРАВИЛЬНО:**
```tsx
{/* ❌ Вызов setState внутри useEffect */}
useEffect(() => {
  if (initialData) {
    reset({ name: initialData.name });
    setSelectedSectionIds(initialData.section_ids || []); // ❌ Каскадные рендеры!
  }
}, [initialData, reset]);
```

**Обоснование:** Вызов `setState` внутри `useEffect` вызывает каскадные рендеры и предупреждение React. Использование `watch()` обеспечивает единый источник истины в `react-hook-form`.

---

Этот документ является **единственным источником истины** для Frontend-разработки в проекте Cool ERP. Любое отклонение от этих правил будет считаться нарушением архитектуры и подлежит немедленному исправлению.