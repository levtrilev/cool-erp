# Правило №9: Использование Orval-хуков вместо прямого использования React Query

Вместо прямого использования хуков `useQuery` и `useMutation` из библиотеки TanStack Query (React Query) **ОБЯЗАТЕЛЬНО** использовать сгенерированные Orval-хуки (`useReadXxx...`, `useCreateXxx...`, `useUpdateXxx...`, `useDeleteXxx...`). Orval автоматически генерирует типобезопасные хуки на основе OpenAPI-спецификации бэкенда.

Прямое использование `useQuery`/`useMutation` с ручным описанием `queryKey` и `queryFn` **КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО**.

---

### 1. Обоснование (Почему это важно)

1. **Типобезопасность (Type Safety):** Orval генерирует хуки с точными типами параметров и возвращаемых значений, соответствующими Pydantic-схемам бэкенда. При ручном использовании `useQuery` легко допустить ошибку в типизации, которая обнаружится только в runtime.
2. **Синхронизация с API:** При изменении эндпоинта на бэкенде (например, добавлении нового параметра) достаточно перегенерировать Orval (`npm run orval`), и TypeScript сразу покажет ошибки в местах использования устаревших параметров. При ручном описании `queryFn` такие изменения легко пропустить.
3. **Единообразие `queryKey`:** Orval автоматически генерирует консистентные `queryKey` для всех запросов. Это критически важно для корректной работы `invalidateQueries` (Правило №24). При ручном описании ключей легко допустить расхождение, из-за чего инвалидация кэша не будет работать.
4. **Снижение объема кода:** Orval-хук — это одна строка импорта и вызова. Ручное описание `useQuery` требует 10-15 строк кода на каждый эндпоинт.
5. **Защита от опечаток:** URL эндпоинта, HTTP-метод и структура тела запроса генерируются автоматически. Невозможно случайно написать `"/api/v1/role/"` вместо `"/api/v1/roles/"`.

---

### 2. Обязательные требования к реализации

#### 2.1. Использование сгенерированных хуков
Все операции чтения, создания, обновления и удаления **ОБЯЗАТЕЛЬНО** выполняются через Orval-хуки, сгенерированные из OpenAPI-спецификации.

#### 2.2. Перегенерация после изменений на бэкенде
После любого изменения Pydantic-схем или роутеров на бэкенде **ОБЯЗАТЕЛЬНО** выполнять:
```bash
cd frontend
npm run orval
```

#### 2.3. Передача опций хука
Orval-хуки принимают второй аргумент — объект с опциями React Query (`retry`, `enabled`, `onSuccess` и т.д.). Это позволяет кастомизировать поведение без потери типобезопасности.

#### 2.4. Использование прямых функций для колбэков
Внутри обработчиков событий (например, в `onXxxSaved` после сохранения) **ОБЯЗАТЕЛЬНО** использовать прямые функции Orval (без `use` в названии), а не хуки, так как хуки нельзя вызывать внутри функций (Rules of Hooks).

---

### 3. Примеры кода

#### ✅ ПРАВИЛЬНО: Чтение списка через Orval-хук

```tsx
import { useReadRolesRolesGet } from "@/api/generated/roles/roles";
import type { RoleResponseSchema } from "@/api/generated/fastAPI.schemas";

export const RolesPage = () => {
  const [page, setPage] = useState(1);
  const [limit] = useState(10);
  const [search, setSearch] = useState("");

  // ✅ Orval-хук с типизированными параметрами
  const { data, isLoading, isError, refetch } = useReadRolesRolesGet(
    {
      skip: (page - 1) * limit,
      limit,
      search: search || undefined,
    },
    {
      // ✅ Опции React Query передаются вторым аргументом
      retry: 1,
      keepPreviousData: true,
    }
  );

  const roles: RoleResponseSchema[] = data?.data?.items || [];
  const total = data?.data?.total || 0;

  if (isLoading) return <div>Загрузка...</div>;
  if (isError) return <div>Ошибка загрузки</div>;

  return (
    <div>
      <p>Всего: {total}</p>
      {/* ... рендер таблицы ... */}
    </div>
  );
};
```

#### ✅ ПРАВИЛЬНО: Создание записи через Orval-мутацию

```tsx
import { useCreateRoleRolesPost } from "@/api/generated/roles/roles";
import type { RoleCreateSchema } from "@/api/generated/fastAPI.schemas";
import { useToast } from "@/components/ui/use-toast";

export const CreateRoleModal = ({ onRoleSaved }) => {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  
  // ✅ Orval-хук для мутации
  const createMutation = useCreateRoleRolesPost({
    onSuccess: async (res) => {
      // ✅ Инвалидация кэша (Правило №24)
      await queryClient.invalidateQueries({ queryKey: ["roles"] });
      onRoleSaved(res.data.id, res.data.name);
      toast({ title: "Роль создана" });
    },
    onError: (error) => {
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: "Не удалось создать роль",
      });
    },
  });

  const onSubmit = async (data: RoleCreateSchema) => {
    // ✅ Мутация вызывается через mutateAsync для await
    await createMutation.mutateAsync({ data });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {/* ... поля формы ... */}
      <Button type="submit" disabled={createMutation.isPending}>
        {createMutation.isPending ? "Сохранение..." : "Создать"}
      </Button>
    </form>
  );
};
```

#### ✅ ПРАВИЛЬНО: Использование прямой функции в колбэке

```tsx
import { readRolesRolesGet } from "@/api/generated/roles/roles"; // ✅ Прямая функция (без use)
import type { RoleResponseSchema } from "@/api/generated/fastAPI.schemas";

// Callback, переданный из модалки
const handleRoleSaved = async (id: string, name: string) => {
  // ✅ Прямая функция для поиска в полном списке (внутри обработчика)
  const fullListRes = await readRolesRolesGet({ limit: 1000, skip: 0 });
  const allItems: RoleResponseSchema[] = fullListRes.data?.items || [];
  
  const foundIndex = allItems.findIndex((item) => item.id === id);
  if (foundIndex !== -1) {
    const targetPage = Math.ceil((foundIndex + 1) / limit);
    toast({
      title: "Роль создана",
      description: `На странице ${targetPage}`,
      action: <Button onClick={() => setPage(targetPage)}>Перейти</Button>,
    });
  }
};
```

#### ❌ НЕПРАВИЛЬНО: Прямое использование useQuery

```tsx
// ❌ ГРУБОЕ НАРУШЕНИЕ ПРАВИЛА №9
import { useQuery } from "@tanstack/react-query";
import { readRolesRolesGet } from "@/api/generated/roles/roles";

export const RolesPage = () => {
  // ❌ ЗАПРЕЩЕНО: Ручное описание useQuery
  const { data, isLoading } = useQuery({
    queryKey: ["roles", page, limit, search], // ❌ Ручной queryKey — рассинхронизация с Orval
    queryFn: () => readRolesRolesGet({         // ❌ Ручной queryFn
      skip: (page - 1) * limit,
      limit,
      search,
    }),
  });

  return <div>...</div>;
};
```
*Почему это плохо:* 
1. `queryKey` может не совпасть с тем, который использует Orval для `invalidateQueries`, и инвалидация кэша не сработает.
2. Отсутствует типобезопасность параметров.
3. При изменении API на бэкенде этот код не обновится автоматически.

#### ❌ НЕПРАВИЛЬНО: Прямое использование useMutation

```tsx
// ❌ ГРУБОЕ НАРУШЕНИЕ ПРАВИЛА №9
import { useMutation } from "@tanstack/react-query";
import { createRoleRolesPost } from "@/api/generated/roles/roles";

export const CreateRoleModal = () => {
  // ❌ ЗАПРЕЩЕНО: Ручное описание useMutation
  const mutation = useMutation({
    mutationFn: (data: RoleCreateSchema) => createRoleRolesPost({ data }),
    onSuccess: () => { /* ... */ },
  });

  return <form>...</form>;
};
```
*Почему это плохо:* Те же причины — потеря типобезопасности, рассинхронизация с Orval, лишний boilerplate.

#### ❌ НЕПРАВИЛЬНО: Использование хука внутри обработчика

```tsx
// ❌ ОШИБКА: Вызов хука внутри функции
const handleRoleSaved = async (id: string) => {
  // ❌ Нарушение Rules of React! Хуки нельзя вызывать в колбэках.
  const { data } = useReadRolesRolesGet({ limit: 1000 }); 
};
```
*Почему это плохо:* React требует, чтобы хуки вызывались только на верхнем уровне компонента. Внутри обработчиков событий нужно использовать **прямые функции** Orval (без `use` в названии).

---

### 4. Нюансы и лучшие практики

#### 4.1. Опции хуков
Orval-хуки принимают стандартные опции React Query во втором аргументе:
```tsx
const { data } = useReadRolesRolesGet(
  { skip: 0, limit: 10 },
  {
    retry: 0,           // Отключить повторные попытки
    staleTime: 10000,   // Данные считаются свежими 10 секунд
    refetchOnWindowFocus: false, // Не обновлять при фокусе окна
    enabled: !!tenantId, // Условное включение запроса
  }
);
```

#### 4.2. Состояние `isPending` vs `isLoading`
В TanStack Query v5:
* `isLoading` — первый раз загружаются данные (кэш пуст).
* `isPending` — любые данные загружаются (включая фоновые обновления).

Для кнопок загрузки **ОБЯЗАТЕЛЬНО** использовать `isPending`:
```tsx
<Button disabled={createMutation.isPending}>
  {createMutation.isPending ? "Сохранение..." : "Сохранить"}
</Button>
```

#### 4.3. Обработка ошибок
Orval-хуки возвращают типизированную ошибку. Для обработки используйте `onError` в опциях мутации или проверяйте `isError` в хуках чтения:
```tsx
const { isError, error } = useReadRolesRolesGet({ skip: 0, limit: 10 });

if (isError) {
  return <div>Ошибка: {error.message}</div>;
}
```

#### 4.4. Условные запросы (enabled)
Если запрос зависит от состояния (например, ID выбранной записи), используйте `enabled`:
```tsx
const [selectedRoleId, setSelectedRoleId] = useState<string | null>(null);

const { data } = useReadRoleRolesRoleIdGet(
  { role_id: selectedRoleId! },
  { enabled: !!selectedRoleId } // ✅ Запрос выполнится только когда ID задан
);
```

#### 4.5. Инвалидация кэша
Для инвалидации используйте `queryKey`, сгенерированный Orval. Обычно это имя домена в нижнем регистре:
```tsx
await queryClient.invalidateQueries({ queryKey: ["roles"] });
```
Чтобы узнать точный `queryKey`, можно посмотреть в DevTools → React Query Devtools или в сгенерированном коде Orval.

#### 4.6. Связь с Правилом №10
Orval-хуки импортируются из `@/api/generated/<domain>/<domain>`, а типы — из `@/api/generated/fastAPI.schemas` (Правило №10). Эти два правила работают в паре:
```tsx
// ✅ Правило №9: Orval-хук
import { useReadRolesRolesGet } from "@/api/generated/roles/roles";
// ✅ Правило №10: Тип из схем
import type { RoleResponseSchema } from "@/api/generated/fastAPI.schemas";
```

#### 4.7. Мутации с параметрами URL
Для эндпоинтов с параметрами в URL (например, `PUT /roles/{role_id}`) Orval генерирует хук, принимающий `params`:
```tsx
const updateMutation = useUpdateRoleRolesRoleIdPut();

await updateMutation.mutateAsync({
  role_id: role.id,  // ✅ Параметр URL
  data: formData,     // ✅ Тело запроса
});
```

---

### 5. Чек-лист для разработчика

При работе с API в любом компоненте проверьте:

- [ ] Используются ли Orval-хуки (`useRead...`, `useCreate...`, `useUpdate...`, `useDelete...`) вместо прямого `useQuery`/`useMutation`?
- [ ] Импортируются ли хуки из `@/api/generated/<domain>/<domain>` (Правило №10)?
- [ ] Типизируются ли данные через типы из `@/api/generated/fastAPI.schemas`?
- [ ] Перегенерирован ли Orval после изменений на бэкенде (`npm run orval`)?
- [ ] Используются ли прямые функции Orval (без `use`) внутри обработчиков событий?
- [ ] Для кнопок загрузки используется `isPending`, а не `isLoading`?
- [ ] Настроены ли опции хука (`retry`, `enabled`, `staleTime`) при необходимости?
- [ ] Отсутствуют ли ручные `queryKey` и `queryFn`?

Следование этому правилу гарантирует, что фронтенд Cool ERP будет полностью типобезопасным, синхронизированным с бэкендом и легко поддерживаемым. Orval берет на себя всю рутину по генерации API-клиентов, позволяя разработчику сосредоточиться на бизнес-логике.