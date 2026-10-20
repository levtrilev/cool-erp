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

## Правило №38: Асинхронная инициализация таблиц с отдельной загрузкой данных
Суть: Если в форме (модалке, странице) присутствует таблица или список, данные для которого загружаются **отдельным API-запросом** (не приходят вместе с основной сущностью), инициализация локального состояния-черновика должна происходить **только после завершения загрузки**. В противном случае возникает **асинхронный разрыв (async gap)**: компонент монтируется, `useState` инициализируется пустым массивом, и только потом приходят реальные данные — но `useState` уже зафиксировал начальное значение и игнорирует последующие изменения. Это особенно критично при **F5 (полной перезагрузке страницы)**, когда кэш React Query пуст.
Строгие требования:
1. `useState` начинается с пустого значения (или значения по умолчанию), а **не** с `initialData`, полученного из API.
2. `useRef` хранит ID сущности, для которой уже проведена инициализация (защита от повторной инициализации при фоновых refetch'ах).
3. `useEffect` синхронизации ждёт выполнения двух условий:
   - `!isLoading` — данные загружены
   - `data !== undefined` — данные существуют
4. **Спиннер** отображается вместо таблицы/списка, пока `isLoading === true`. Это физически предотвращает рендер с пустыми данными.
5. Условие `lastInitializedRef.current !== entityId` гарантирует, что инициализация произойдёт ровно один раз для каждой конкретной сущности.
6. Сброс состояния при закрытии модалки/переходе на другую сущность: `setState([])` + `lastInitializedRef.current = null`.
✅ ПРАВИЛЬНО:
// 1. Загрузка данных с флагом isLoading
 const { data: itemsData, isLoading } = useGetItemsQuery({ entityId });
 // 2. Вычисление начального черновика (мемоизировано, но НЕ используется в useState)
 const initialDraft = useMemo(() => {
   return (itemsData?.items ?? []).map((item) => ({
     id: item.id,
     name: item.name,
     markedForDeletion: false,
   }));
 }, [itemsData]);
 // 3. Состояние черновика начинается ПУСТЫМ
 const [draft, setDraft] = useState<ItemDraft[]>([]);
 // 4. Ref для отслеживания инициализированной сущности
 const lastInitializedId = useRef<string | null>(null);
 // 5. useEffect синхронизации: ждём загрузки перед инициализацией
 useEffect(() => {
   if (open && entityId) {
     // ✅ КРИТИЧНО: ждём завершения загрузки
     if (!isLoading && itemsData) {
       if (lastInitializedId.current !== entityId) {
         setDraft(initialDraft);
         lastInitializedId.current = entityId;
       }
     }
   } else {
     // Сброс при закрытии
     setDraft([]);
     lastInitializedId.current = null;
   }
 }, [open, entityId, initialDraft, isLoading, itemsData]);
 // 6. Спиннер вместо рендера таблицы
 {isLoading ? (
   <div className="flex items-center justify-center h-40">
     <Loader2 className="h-6 w-6 animate-spin" />
   </div>
 ) : (
   <ItemsTable items={draft} onChange={setDraft} />
 )}
❌ НЕПРАВИЛЬНО:
// ❌ ОШИБКА 1: useState инициализируется из данных, которые ещё не загружены
 const [draft, setDraft] = useState<ItemDraft[]>(initialDraft);
 // При F5 initialDraft === [], и useState зафиксирует это значение навсегда
 // ❌ ОШИБКА 2: Нет ожидания загрузки в useEffect
 useEffect(() => {
   if (open && entityId) {
     setDraft(initialDraft); // ❌ Срабатывает до загрузки данных
   }
 }, [open, entityId]);
 // ❌ ОШИБКА 3: Рендер таблицы с пустыми данными
 <ItemsTable items={draft} onChange={setDraft} />
 // Пользователь видит пустую таблицу, потом она "мигает" при загрузке
 // ❌ ОШИБКА 4: Нет защиты от повторной инициализации
 useEffect(() => {
   setDraft(initialDraft); // ❌ Срабатывает на каждый refetch, затирая черновик
 }, [initialDraft]);
Обоснование:
1. **F5-проблема**: При полной перезагрузке страницы кэш React Query пуст. `useQuery` возвращает `data: undefined, isLoading: true`. Если `useState` инициализируется из `initialDraft`, который вычислен из `undefined`, он получает `[]`. Когда данные приходят через 50-200 мс, `initialDraft` пересчитывается, но `useState` **игнорирует** новое значение — он инициализируется только один раз при маунте.
2. **Мигание UI**: Без спиннера пользователь видит пустую таблицу, которая через мгновение заполняется. Это создаёт ощущение "глючного" интерфейса.
3. **Потеря черновика**: Без `lastInitializedRef` каждый фоновый refetch (например, при `invalidateQueries`) будет перезаписывать черновик пользователя, если он уже начал редактирование.
4. **Универсальность паттерна**: Этот паттерн применим к любым таблицам/спискам с отдельной загрузкой: пользователи роли, товары заказа, документы в папке, участники события и т.д.
Чек-лист применения:
Перед коммитом проверьте, что в компоненте с таблицей отдельной загрузки:
- [ ] `useState<...>([])` — пустое начальное значение
- [ ] `useRef<string | null>(null)` — для отслеживания инициализации
- [ ] `useEffect` проверяет `!isLoading && data` перед `setState`
- [ ] Условие `lastInitializedRef.current !== entityId` защищает от повторной инициализации
- [ ] Спиннер отображается вместо таблицы при `isLoading === true`
- [ ] Сброс `setState([])` + `ref.current = null` при закрытии модалки



## Правило №39: Паттерн «Название-ссылка» с пессимистической блокировкой редактирования

**Суть:** В таблицах документных модулей (реализующих контракт документов из ТЗ §3.3 + жизненный цикл) колонка «Название» оформляется как **кликабельная ссылка**, открывающая форму редактирования. Отдельная кнопка «Редактировать» (иконка-карандаш) в колонке «Действия» **не требуется**. Открытие формы сопровождается **атомарным захватом пессимистической блокировки** (`POST /{doctype}/{id}/lock`). Если документ уже заблокирован другим пользователем (423), форма открывается в режиме **только для чтения** (`readOnly`) с визуальным предупреждением. При закрытии формы блокировка освобождается (`DELETE /{doctype}/{id}/lock`).

Правило применяется к модулям, наследующим `DocumentLifecycleMixin` (поле `editing_by_user_id` + `editing_since` + `@property is_editing_locked`). Эталонная реализация — модуль `notes`.

---

### Строгие требования

#### 1. Колонка «Название» — кликабельная ссылка

1.1. Название документа в первой колонке таблицы оборачивается в `<button type="button">` (не `<a>` без `href`, не `<div onClick>`).

1.2. Обязательные CSS-классы ссылки:
```
text-left text-blue-600 hover:text-blue-800 hover:underline underline-offset-2 font-medium cursor-pointer w-full truncate block focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 rounded-sm transition-colors
```

1.3. Обязательный атрибут `title={item.title}` для показа полного текста при обрезании.

1.4. Иконка замка `🔒` (`Lock` из `lucide-react`) отображается **рядом с названием**, если `item.is_editing_locked === true`.

#### 2. Колонка «Действия» — только вторичные операции

2.1. Кнопка «Редактировать» (`<Pencil>`) **удалена** из колонки «Действия».

2.2. В колонке «Действия» остаются только деструктивные и специфичные операции: удаление (`<Trash2>`), делегирование, копирование.

2.3. Ширина колонки «Действия» уменьшается (обычно до `80px` вместо `140px`).

#### 3. Открытие формы с блокировкой

3.1. При клике на название **сначала** проверяется `item.is_editing_locked`:
- если `true` → сразу открыть в `readOnly` (не вызывать `/lock`)
- если `false` → вызвать `POST /{doctype}/{id}/lock`

3.2. При успешном захвате (200) — открыть модалку в режиме редактирования (`readOnly={false}`).

3.3. При 423 ошибке — открыть модалку в режиме **только чтения** (`readOnly={true}`) + показать деструктивный toast с пояснением.

3.4. При иных ошибках — показать деструктивный toast, модалку **не открывать**.

#### 4. Режим «только чтение» в модалке

4.1. Модалка принимает обязательный проп `readOnly?: boolean` (по умолчанию `false`).

4.2. Все поля формы получают `disabled={readOnly}`.

4.3. При `readOnly === true`:
- В заголовке: «Просмотр {сущность} (только чтение)»
- Показывается `<Alert variant="destructive">` с текстом о блокировке
- Кнопка «Сохранить» **не рендерится**
- Кнопка «Отмена» заменяется на «Закрыть»

4.4. В `onSubmit` обязательна защита: `if (readOnly) return;`

#### 5. Освобождение блокировки

5.1. При закрытии модалки, если блокировка была захвачена (`!readOnly`), вызывается `DELETE /{doctype}/{id}/lock`.

5.2. Ошибки освобождения **игнорируются** (таймаут 30 минут всё равно снимет блокировку).

5.3. После освобождения состояние `editingNote` сбрасывается в `null`, `readOnly` в `false`.

#### 6. Обработка ошибок в модалке

6.1. При сохранении (`PUT`) обработка статусов:
- `409` → «Документ был изменён другим пользователем. Обновите страницу…»
- `423` → «Документ сейчас редактируется другим пользователем…»
- иные → `detail` из ответа или дефолтное сообщение

---

### ✅ ПРАВИЛЬНО

#### Фрагмент страницы списка (`NotesPage.tsx`)

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

#### Фрагмент таблицы (`NotesPage.tsx`)

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

#### Фрагмент модалки (`EditNoteModal.tsx`)

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

#### Обработка ошибок сохранения в модалке

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

### ❌ НЕПРАВИЛЬНО

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

### Обоснование

#### Почему название-ссылка, а не кнопка-карандаш?

| Аспект | Кнопка-карандаш | Название-ссылка |
|--------|-----------------|-----------------|
| **Горизонтальное пространство** | Занимает 40-60px в колонке «Действия» | Экономит место — колонка «Действия» сокращается до 80px |
| **Ментальная модель** | Пользователь ищет кнопку в правой части | Пользователь кликает на сам объект (естественно, как в файловых менеджерах) |
| **Скорость взаимодействия** | Два шага: найти строку → найти кнопку | Один шаг: кликнуть на название |
| **Доступность** | `<button>` с `title` | `<button>` с `title` + `focus:ring` для клавиатурной навигации |

#### Почему пессимистическая блокировка при открытии?

| Аспект | Без блокировки | С блокировкой |
|--------|----------------|---------------|
| **Конфликт** | Пользователь узнаёт о конфликте при сохранении (409) | Пользователь узнаёт о конфликте сразу при открытии (423 → readOnly) |
| **Потеря работы** | 10 минут редактирования могут быть потеряны | Пользователь сразу видит, что документ занят, и не тратит время |
| **Визуальная индикация** | Нет | Иконка 🔒 в списке + предупреждение в модалке |
| **Атомарность** | Нет гарантии | `UPDATE ... WHERE ... RETURNING` гарантирует атомарный захват |

#### Почему режим «только чтение», а не запрет открытия?

Пользователь может **хотеть просмотреть** документ, даже если не может его редактировать. Запрет открытия (показ только ошибки) ухудшает UX. Режим `readOnly` позволяет:
- Ознакомиться с содержимым документа
- Понять, кто сейчас редактирует (через иконку замка в списке)
- Вернуться позже, когда блокировка истечёт (таймаут 30 минут)

#### Связь с другими правилами

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

### Чек-лист применения

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

### Область применения

Правило №39 применяется **только** к модулям, реализующим контракт документов (ТЗ §3.3 + жизненный цикл):
- ✅ `notes` (эталон)
- ✅ будущие типы документов (`invoices`, `contracts`, `deals` и т.д.)

**Не применяется** к справочникам и административным модулям:
- ❌ `doctypes`, `roles`, `tenants`, `users`, `domains`, `sections`, `permissions` — для них остаётся паттерн с кнопкой-карандашом, так как у них нет пессимистической блокировки и сценария «документ занят»

#### Это правило является логическим продолжением Правил №35 и №37 и полностью соответствует ТЗ версии 2.0. Любое отклонение при реализации документного модуля будет считаться нарушением архитектуры.


## Правило №41: Общие требования к формам и уведомлениям на фронтенде

**Суть:** Все формы и пользовательские уведомления на фронтенде обязаны следовать единому технологическому стандарту: управление формами через `react-hook-form`, валидация через `zodResolver` с Zod-схемами, сложные поля через `<Controller>`, уведомления через `useToast()` из `shadcn/ui`. Запрещены «голые» `useState` для форм, ручная валидация, нативные `alert()`/`confirm()`/`console.log()` для пользователя и самописные компоненты уведомлений.

Правило является обобщающим и устанавливает базовый стандарт, на который ссылаются специализированные правила (№12, №20, №22, №27, №34, №35, №36, №37, №38, №39).

---

### Строгие требования

#### 1. Управление формами

1.1. Все формы (создание, редактирование, фильтры) обязаны использовать `useForm()` из `react-hook-form`.

1.2. Валидация обязательно выполняется через `zodResolver` из `@hookform/resolvers/zod` с Zod-схемой.

1.3. Схема валидации объявляется через `z.object({...})` и экспортируется как отдельная константа (`noteFormSchema`, `roleSchema` и т.д.).

1.4. Тип формы выводится из схемы: `type FormData = z.infer<typeof schema>`.

1.5. `defaultValues` формы объявляются как константа `CREATE_DEFAULTS` вне компонента или в самом его начале (детали — Правило №20).

#### 2. Использование `<Controller>` и `register`

2.1. Для полей, которые **не являются** нативными HTML-элементами с поддержкой `onChange`/`value` (справочники `ReferenceSelect`, переключатели `Switch`, `Select`, `Textarea` с кастомной логикой, массивы тегов), обязателен `<Controller>` из `react-hook-form`.

2.2. В проекте устоялся паттерн использования `<Controller>` для **всех** полей формы, включая простые `<Input>`. Это обеспечивает единообразие кода и упрощает рефакторинг.

2.3. Запрещено смешивать подходы в одной форме (часть полей через `register`, часть через `Controller`), если это не обосновано спецификой поля.

#### 3. Отображение ошибок валидации

3.1. Ошибки валидации обязаны отображаться **под соответствующим полем**.

3.2. Для отображения используется `<p className="text-xs text-destructive">` с текстом `errors.{fieldName}.message`.

3.3. Проверка наличия ошибки выполняется через `&&`: `{errors.name && <p>...</p>}`.

#### 4. Состояние загрузки формы

4.1. Кнопка отправки формы обязана быть заблокирована во время отправки через `disabled={isSubmitting}` из `formState`.

4.2. При блокировке рекомендуется отображать иконку загрузки `<Loader2 className="animate-spin" />`.

4.3. Текст кнопки может меняться в зависимости от состояния (например, «Сохранение...» / «Сохранить»).

#### 5. Уведомления пользователю

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

#### 6. Сброс формы

6.1. После успешной отправки формы вызывается `reset(CREATE_DEFAULTS)` (детали — Правило №20).

6.2. При закрытии модалки вызывается `reset(CREATE_DEFAULTS)` (детали — Правило №20).

6.3. При открытии модалки в режиме редактирования вызывается `reset({...})` с данными из `initialData` (детали — Правило №37).

---

### ✅ ПРАВИЛЬНО

#### Пример 1: Полная форма создания с валидацией

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

#### Пример 2: Уведомления через `useToast()`

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

#### Пример 3: Сложное поле через `<Controller>` (справочник)

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

### ❌ НЕПРАВИЛЬНО

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

### Обоснование

#### Почему `react-hook-form` + Zod?

| Аспект | `useState` + ручная валидация | `react-hook-form` + Zod |
|--------|-------------------------------|--------------------------|
| Типобезопасность | Нет (все значения — `string`) | ✅ Типы выводятся из схемы |
| Валидация | Ручная, дублируется | ✅ Декларативная, в одном месте |
| Производительность | Перерендер на каждое изменение | ✅ Перерендер только при отправке |
| Переиспользование | Невозможно | ✅ Схемы и хуки переиспользуются |
| Синхронизация с бэкендом | Нет | ✅ Zod ↔ Pydantic (похожий синтаксис) |

#### Почему `useToast()` из `shadcn/ui`?

| Аспект | Нативные `alert()` | Самописные компоненты | `useToast()` |
|--------|---------------------|------------------------|---------------|
| Единообразие стиля | ❌ Чужеродно | ⚠️ Зависит от реализации | ✅ Единый стиль |
| Тёмная тема | ❌ Нет | ⚠️ Нужно реализовать | ✅ Из коробки |
| Неблокирующий | ❌ Блокирует | ✅ | ✅ |
| Поддержка `action` (кнопка) | ❌ Нет | ⚠️ Нужно реализовать | ✅ Из коробки |
| Варианты (`destructive`) | ❌ Нет | ⚠️ Нужно реализовать | ✅ Из коробки |
| Интеграция с React | ❌ Нет | ⚠️ Нужно реализовать | ✅ Из коробки |

#### Почему `<Controller>` для всех полей?

В проекте устоялся паттерн использования `<Controller>` для **всех** полей формы, а не только для сложных. Это обеспечивает:
- **Единообразие кода** — все поля оформлены одинаково, легко читать и рефакторить
- **Лёгкость замены** — если `<Input>` нужно заменить на кастомный компонент, не нужно менять обвязку
- **Доступ к `fieldState`** — можно получить `fieldState.error` для каждого поля
- **Совместимость с Правилом №27** (`ReferenceSelect`) и **Правилом №34** (`Switch`)

---

### Чек-лист применения

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

### Связь с другими правилами

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

---

Этот документ является **единственным источником истины** для Frontend-разработки в проекте Cool ERP. Любое отклонение от этих правил будет считаться нарушением архитектуры и подлежит немедленному исправлению.