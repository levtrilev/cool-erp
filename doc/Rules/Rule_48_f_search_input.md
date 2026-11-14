Правило №47: Транзиентные состояния ввода не входят в персистентный view-state таблицы

Суть: поля НЕЗАВЕРШЁННОГО ввода (searchInput, поле перехода к странице,
черновики внутри меню колонок) НЕ ДОЛЖНЫ входить в объект, персистентно
хранящийся через useTablePreferences / user_ui_preferences. Персистентное
состояние таблицы содержит только ПРИМЕНЁННЫЕ значения: columnStates, search,
page, page_size. Текущий ввод живёт в локальном useState и инициализируется
один раз из восстановленного применённого значения после isRestored.

Нарушение приводит к дефекту «откатывающийся ввод»: каждый keystroke вызывает
setViewState → patch → пересчёт state через fromStored, где поле ввода
восстанавливается из применённого значения, — пользователь не может ввести
ни одного символа. Дефект воспроизводился трижды (Notes, Orders, ItemTypes),
поэтому закреплён отдельным правилом.

Строгие требования
47.1. Интерфейс TState для useTablePreferences ЗАПРЕЩАЕТСЯ наполнять полями
      «текущего ввода» (searchInput, jumpInput и т.п.). Допустимый состав:
      columnStates, search, page, page_size.
47.2. Состояние ввода объявляется локальным useState в компоненте страницы;
      его сеттер НЕ оборачивается в setViewState / setState хука.
47.3. Инициализация ввода из восстановленного применённого значения
      выполняется ОДНОКРАТНО: useEffect с условием isRestored и ref-флагом
      (защита от повторного сброса при фоновых refetch и overlay-обновлениях).
47.4. Применение ввода к персистентному состоянию происходит только в submit
      формы поиска: setSearch(searchInput); setPage(1) (Правила №12, №22).
47.5. Согласованность адаптеров: каждое поле TState обязано присутствовать
      в серверной схеме TablePreferenceSchema. Поле, которое toStored
      отбрасывает, а fromStored восстанавливает из ДРУГОГО поля, —
      гарантированное нарушение этого правила.
47.6. Код-ревью новой страницы с useTablePreferences: сверить состав TState
      с картой toStored; расхождение = нарушение №47.

✅ ПРАВИЛЬНО:
const [searchInput, setSearchInput] = useState<string>("");
const searchInputInitializedRef = useRef<boolean>(false);

useEffect(() => {
  if (!isRestored || searchInputInitializedRef.current) return;
  searchInputInitializedRef.current = true;
  setSearchInput(search);
}, [isRestored, search]);

<form onSubmit={(e) => { e.preventDefault(); setSearch(searchInput); setPage(1); }}>
  <Input value={searchInput} onChange={(e) => setSearchInput(e.target.value)} />
</form>

❌ НЕПРАВИЛЬНО:
interface TableViewState {
  columnStates: ColumnStates;
  search: string;
  searchInput: string;   // ❌ транзиентное поле в персистентном состоянии
  page: number;
}
const setSearchInput = useCallback(
  (next: string) => setViewState((prev) => ({ ...prev, searchInput: next })),
  [setViewState],
);
// keystroke → patch → fromStored → searchInput = stored.search → ввод откатывается

Обоснование (механика дефекта)
| Шаг|Что происходит|
| ---|---|
| 1|Пользователь вводит символ: setSearchInput("а") → setViewState|
| 2|useTablePreferences шлёт patch({ tables: { key: toStored(next) } })|
| 3|Провайдер обновляет overlay → preferences.tables[key] меняется|
| 4|state пересчитывается через fromStored, где searchInput = stored.search|
| 5|stored.search — применённое значение (пустое до submit) → поле очищается|

Чек-лист применения
[ ] TState не содержит searchInput / jumpInput / иных полей ввода
[ ] Ввод объявлен локальным useState, сеттер не обёрнут в setViewState
[ ] Инициализация ввода — useEffect с isRestored + ref-флаг (однократно)
[ ] Submit формы пишет применённое значение в персистентное состояние
[ ] Каждое поле TState присутствует в TablePreferenceSchema (п. 47.5)

Связь с другими правилами
| Правило|Связь|
| ---|---|
| №12 (Поиск через form)|Применение ввода только по submit|
| №22 (Разделение состояний поиска)|searchInput и search — разные состояния|
| №46 (Архитектура сложных форм)|п. 1.4: один источник истины на значение|
| useTablePreferences|контракт toStored/fromStored|

Это правило обязательно для всех страниц, использующих персистентный вид
таблицы. Наличие поля ввода в TState считается дефектом архитектуры и
исправляется при код-ревью без обсуждения.