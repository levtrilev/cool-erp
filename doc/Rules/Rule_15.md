# Правило №15: Пагинация с номерами страниц и эллипсисом

Компонент пагинации на всех списочных CRUD-страницах **ОБЯЗАТЕЛЬНО** должен отображать номера страниц с использованием логики «эллипсиса» (троеточия). Максимальное количество отображаемых числовых кнопок не должно превышать **5-7 элементов**.

Использование простого переключения «Назад / Вперед» без номеров страниц, а также рендеринг всех страниц подряд (например, от 1 до 100) **КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО**.

---

### 1. Обоснование (Почему это важно)

1. **Прямая навигация:** Если пользователь ищет запись, которая, по его памяти, находится в конце списка (например, на 45-й странице), ему не придется 40 раз нажимать кнопку «Вперед». Он сразу нажмет на нужную цифру или «...» для быстрого перехода.
2. **Экономия места на экране:** Рендеринг 100 кнопок с номерами сломает верстку на десктопе и сделает интерфейс непригодным на мобильных устройствах.
3. **Стандарт индустрии:** Паттерн `1 ... 4 5 6 ... 10` является общепринятым стандартом UX для таблиц с большим объемом данных (Google, Jira, GitHub).

---

### 2. Обязательные требования к реализации

#### 2.1. Динамическая генерация массива страниц
Необходимо использовать утилиту (хук или функцию), которая на основе `currentPage` и `totalPages` возвращает массив с номерами и маркерами пропуска (`ellipsis`).

#### 2.2. Ограничение видимых элементов
В видимой области пагинации должно быть **максимум 5 числовых кнопок** (не считая кнопок «Назад», «Вперед», «В начало», «В конец»).

#### 2.3. Использование компонентов shadcn/ui
Для отрисовки **ОБЯЗАТЕЛЬНО** использовать стандартные компоненты из `@/components/ui/pagination`:
* `Pagination`, `PaginationContent`, `PaginationItem`
* `PaginationLink` (для цифр)
* `PaginationEllipsis` (для троеточия)
* `PaginationPrevious`, `PaginationNext`

#### 2.4. Состояния кнопок
Кнопки «Назад» и «В начало» должны быть `disabled`, если пользователь на 1-й странице. Кнопки «Вперед» и «В конец» — если на последней.

---

### 3. Примеры кода

#### ✅ ПРАВИЛЬНО: Утилита для генерации и JSX пагинации

**1. Утилита для расчета страниц (`frontend/src/lib/utils.ts` или отдельный файл):**
```typescript
// Функция генерирует массив вида: [1, 'ellipsis', 4, 5, 6, 'ellipsis', 10]
export const getPaginationRange = (currentPage: number, totalPages: number): (number | 'ellipsis')[] => {
  if (totalPages <= 5) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  if (currentPage <= 3) {
    return [1, 2, 3, 4, 'ellipsis', totalPages];
  }

  if (currentPage >= totalPages - 2) {
    return [1, 'ellipsis', totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
  }

  return [
    1,
    'ellipsis',
    currentPage - 1,
    currentPage,
    currentPage + 1,
    'ellipsis',
    totalPages,
  ];
};
```

**2. Использование в компоненте страницы (`RolesPage.tsx`):**
```tsx
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { getPaginationRange } from "@/lib/utils";

// ... внутри компонента ...
const totalPages = Math.ceil((data?.data?.total || 0) / limit);
const paginationRange = getPaginationRange(page, totalPages);

return (
  // ... таблица ...
  
  <div className="mt-4">
    <Pagination>
      <PaginationContent>
        {/* Кнопка "В начало" (опционально, но рекомендуется) */}
        <PaginationItem>
          <PaginationLink 
            onClick={() => setPage(1)} 
            isActive={false}
            className={page === 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
          >
            1
          </PaginationLink>
        </PaginationItem>

        <PaginationItem>
          <PaginationPrevious 
            onClick={() => setPage(prev => Math.max(1, prev - 1))}
            className={page === 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
          />
        </PaginationItem>

        {/* Динамические номера страниц */}
        {paginationRange.map((item, index) => (
          <PaginationItem key={index}>
            {item === 'ellipsis' ? (
              <PaginationEllipsis />
            ) : (
              <PaginationLink
                onClick={() => setPage(item)}
                isActive={item === page}
                className="cursor-pointer"
              >
                {item}
              </PaginationLink>
            )}
          </PaginationItem>
        ))}

        <PaginationItem>
          <PaginationNext 
            onClick={() => setPage(prev => Math.min(totalPages, prev + 1))}
            className={page === totalPages ? "pointer-events-none opacity-50" : "cursor-pointer"}
          />
        </PaginationItem>
      </PaginationContent>
    </Pagination>
  </div>
);
```

#### ❌ НЕПРАВИЛЬНО: Рендеринг всех страниц (Антипаттерн)

```tsx
// ❌ ГРУБОЕ НАРУШЕНИЕ ПРАВИЛА №15
// Если в базе 1000 записей и limit=10, это отрендерит 100 кнопок!
{Array.from({ length: totalPages }, (_, i) => i + 1).map((pageNum) => (
  <PaginationItem key={pageNum}>
    <PaginationLink onClick={() => setPage(pageNum)} isActive={pageNum === page}>
      {pageNum}
    </PaginationLink>
  </PaginationItem>
))}
```

#### ❌ НЕПРАВИЛЬНО: Только кнопки "Назад" и "Вперед"

```tsx
// ❌ ОШИБКА UX: Пользователь не знает, сколько всего страниц, 
// и не может быстро перейти на последнюю.
<PaginationPrevious onClick={() => setPage(page - 1)} />
<PaginationNext onClick={() => setPage(page + 1)} />
```

---

### 4. Нюансы и лучшие практики

#### 4.1. Обработка `totalPages === 0` или `1`
Если записей нет или они все помещаются на одну страницу (`totalPages <= 1`), компонент пагинации **НЕ ДОЛЖЕН** рендериться вообще. Это избавляет интерфейс от визуального шума.

```tsx
{totalPages > 1 && (
  <Pagination>
    {/* ... */}
  </Pagination>
)}
```

#### 4.2. Сброс на первую страницу при изменении фильтров
Если пользователь меняет поиск (`search`) или лимит записей на странице (`limit`), переменная `page` **ОБЯЗАТЕЛЬНО** должна сбрасываться в `1`. Иначе пользователь может остаться на 5-й странице, где для нового фильтра данных уже нет (Правило №22).

```tsx
const handleSearch = (e: React.FormEvent) => {
  e.preventDefault();
  setSearch(searchInput);
  setPage(1); // ✅ Сброс страницы
};
```

#### 4.3. Курсор и отключение кликов
Вместо того чтобы полностью удалять кнопку из DOM или использовать атрибут `disabled` (который в `shadcn/ui` PaginationLink может стилизоваться неочевидно), лучше использовать комбинацию `pointer-events-none opacity-50` для неактивных кнопок. Это сохраняет верстку стабильной.

---

### 5. Чек-лист для разработчика

При добавлении пагинации на списочную страницу проверьте:

- [ ] Скрывается ли блок пагинации, если `totalPages <= 1`?
- [ ] Используется ли утилита для генерации массива с эллипсисом (`...`)?
- [ ] Отображается ли **не более 5-7** числовых кнопок одновременно?
- [ ] Используются ли компоненты `PaginationEllipsis`, `PaginationPrevious`, `PaginationNext` из shadcn/ui?
- [ ] Заблокированы ли (визуально и функционально) кнопки перехода назад на 1-й странице и вперед на последней?
- [ ] Сбрасывается ли `page` в `1` при изменении поискового запроса или лимита?

Следование этому правилу гарантирует, что интерфейс списка останется чистым, отзывчивым и удобным для навигации даже при работе с десятками тысяч записей.