# Правило №29: Обязательная регулировка ширины колонок во всех таблицах

Все табличные представления **ОБЯЗАТЕЛЬНО** должны предоставлять пользователю возможность изменять ширину колонок путём перетаскивания. Это критически важно для адаптации интерфейса под разные сценарии использования (длинные названия, большое количество данных в ячейках и т.д.).

---

### 1. Обязательное использование хука `useResizableColumns`

Каждая таблица должна использовать кастомный хук `useResizableColumns` из `@/hooks/useResizableColumns`.

```typescript
import { useResizableColumns } from "@/hooks/useResizableColumns";

// Внутри компонента:
const columns = [
  { id: "name", initialWidth: 300, minWidth: 150 },
  { id: "description", initialWidth: 250, minWidth: 100 },
  { id: "sections", initialWidth: 350, minWidth: 200 },
  { id: "actions", initialWidth: 50, minWidth: 50 },
];

const { widths, handleMouseDown, resetWidths } = useResizableColumns(
  columns,
  "<domain>-<entity>-table-widths"  // Уникальный ключ для localStorage
);
```

---

### 2. Требования к хуку `useResizableColumns`

Хук должен обеспечивать:
- **Загрузку/сохранение ширин** в `localStorage` с уникальным ключом для каждой таблицы
- **Компенсацию соседней колонки**: при изменении ширины одной колонки соседняя должна изменяться на противоположную величину (общая ширина таблицы не меняется)
- **Минимальную ширину**: каждая колонка должна иметь `minWidth` (по умолчанию 50px), ниже которой сжатие невозможно
- **Глобальные обработчики** `mousemove` и `mouseup` на `document` для корректной работы при быстром движении мыши
- **Визуальную обратную связь**: курсор `col-resize` и отключение `user-select` во время перетаскивания
- **Функцию `resetWidths`** для сброса к значениям по умолчанию

---

### 3. Требования к UI таблицы

#### 3.1. Визуальные маркеры изменения размера
- Каждый заголовок колонки (кроме последней) должен содержать **визуальный маркер** — тонкую полоску справа:
  ```tsx
  <div
    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20 active:bg-primary/40 transition-colors"
    onMouseDown={(e) => handleMouseDown("columnId", e)}
  />
  ```
- Маркер должен быть виден при наведении (`hover:bg-primary/20`)
- Последняя колонка **не должна** иметь маркера (ей нечего компенсировать)

#### 3.2. Кнопка сброса
- Над таблицей (или в её шапке) должна быть кнопка **"Сбросить ширину"**, вызывающая `resetWidths()`
- Расположение: правый верхний угол, над таблицей, в блоке с `border-b`

#### 3.3. Применение ширин
- Каждая ячейка заголовка (`TableHead`) и данных (`TableCell`) должна иметь inline-стиль:
  ```tsx
  style={{ width: `${widths.columnId}px` }}
  ```
- Таблица должна иметь класс `table-fixed` для корректной работы фиксированных ширин

---

### 4. Требования к содержимому ячеек

При изменении ширины колонок содержимое должно корректно адаптироваться:

- **Текстовые колонки**: использовать `truncate` + `title` для показа полного текста при наведении
  ```tsx
  <button title={role.name} className="block w-full truncate">
    {role.name}
  </button>
  ```
- **Колонки с множеством элементов** (badge, теги): использовать `flex-wrap` + `overflow-hidden`
- **Колонки с действиями** (кнопки): фиксированная ширина, `align-top`

---

### 5. Требования к `storageKey`

Ключ для `localStorage` должен следовать формату:
```
<domain>-<entity>-table-widths
```

Примеры:
- `"roles-table-widths"` — таблица ролей
- `"users-table-widths"` — таблица пользователей
- `"tenants-table-widths"` — таблица организаций
- `"sections-table-widths"` — таблица разделов
- `"inventory-items-table-widths"` — таблица позиций склада

---

### 6. Пример полной реализации

```tsx
// В компоненте страницы списка
const columns = [
  { id: "name", initialWidth: 300, minWidth: 150 },
  { id: "description", initialWidth: 250, minWidth: 100 },
  { id: "sections", initialWidth: 350, minWidth: 200 },
  { id: "actions", initialWidth: 50, minWidth: 50 },
];

const { widths, handleMouseDown, resetWidths } = useResizableColumns(
  columns,
  "roles-table-widths"
);

// В JSX:
<div className="rounded-md border bg-card">
  <div className="flex justify-end p-2 border-b">
    <Button variant="ghost" size="sm" onClick={resetWidths} className="text-xs">
      Сбросить ширину
    </Button>
  </div>
  
  <Table className="table-fixed w-full">
    <TableHeader>
      <TableRow className="h-10 hover:bg-transparent">
        {columns.slice(0, -1).map((col) => (
          <TableHead 
            key={col.id}
            className="relative"
            style={{ width: `${widths[col.id]}px` }}
          >
            {col.label}
            <div
              className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20 active:bg-primary/40"
              onMouseDown={(e) => handleMouseDown(col.id, e)}
            />
          </TableHead>
        ))}
        {/* Последняя колонка без маркера */}
        <TableHead style={{ width: `${widths.actions}px` }} />
      </TableRow>
    </TableHeader>
    {/* ... TableBody ... */}
  </Table>
</div>
```

---

### 7. Чего избегать

- ❌ **НЕ использовать** стандартные таблицы без возможности изменения ширины колонок
- ❌ **НЕ задавать** фиксированные ширины через `w-[Xpx]` в `TableHead` без использования хука
- ❌ **НЕ сохранять** ширины в глобальном хранилище (Redux/Zustand) — только `localStorage`
- ❌ **НЕ позволять** колонкам сжиматься ниже `minWidth`
- ❌ **НЕ забывать** про кнопку сброса — пользователь должен иметь возможность вернуть настройки по умолчанию
- ❌ **НЕ применять** `table-layout: auto` — только `table-fixed`

---

### 8. Исключения

Допускается отсутствие регулировки ширины для:
- Таблиц с фиксированным числом колонок и предсказуемым контентом (например, матрица полномочий в `EditRoleModal`)
- Таблиц внутри модальных окон с фиксированной шириной (если это обосновано UX)

---

### 9. Обоснование правила

1. **Единообразие UX**: Пользователь привыкает к единому механизму настройки таблиц во всём приложении
2. **Адаптивность**: Разные пользователи работают с разными данными — кому-то важны длинные названия, кому-то описания
3. **Сохранение настроек**: `localStorage` гарантирует, что настройки не теряются между сессиями
4. **Производительность**: Локальное хранение ширин не создаёт нагрузки на сервер
5. **Масштабируемость**: При добавлении новых доменов (`inventory`, `assets`, `cashflow`, `payable`) правило автоматически применяется ко всем новым таблицам

---

### 10. Чек-лист для разработчика при создании новой списочной страницы

- [ ] Импортирован хук `useResizableColumns`
- [ ] Определён массив `columns` с `id`, `initialWidth`, `minWidth`
- [ ] Вызван хук с уникальным `storageKey`
- [ ] Добавлена кнопка "Сбросить ширину"
- [ ] В `TableHead` каждой колонки (кроме последней) добавлен маркер `onMouseDown`
- [ ] В `TableHead` и `TableCell` применены inline-стили `width`
- [ ] Таблица имеет класс `table-fixed`
- [ ] Содержимое ячеек корректно адаптируется (`truncate`, `flex-wrap`, `overflow-hidden`)

---

**Размещение**: ЧАСТЬ 3. FRONTEND — СПИСОЧНЫЕ ФОРМЫ (CRUD СТРАНИЦЫ)

Следование этому правилу гарантирует, что все таблицы в проекте Cool ERP будут иметь единый, предсказуемый и удобный механизм настройки ширины колонок.