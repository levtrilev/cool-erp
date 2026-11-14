// frontend/src/modules/sales/item_types/ItemTypesPage.tsx
import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useQueryClient, keepPreviousData } from "@tanstack/react-query";
import {
  Plus,
  Trash2,
  Search,
  Loader2,
  Lock,
  Copy,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/components/ui/use-toast";
import {
  useGetSalesItemTypesSalesItemTypesGet,
  useDeleteSalesItemTypeSalesItemTypesItemTypeIdDelete,
  getSalesItemTypesSalesItemTypesGet,
  useAcquireSalesItemTypeLockSalesItemTypesItemTypeIdLockPost,
  useReleaseSalesItemTypeLockSalesItemTypesItemTypeIdLockDelete,
} from "@/api/generated/sales-item-types/sales-item-types";
import {
  SalesItemTypeResponseSchema,
  SalesItemTypeSortField,
  SortOrder,
  type TableColumnStateSchema,
  type TablePreferenceSchema,
  type TablePreferenceSchemaColumnStates,
} from "@/api/generated/coolERP.schemas";
import { EditItemTypeModal } from "./EditItemTypeModal";
import { useResizableColumns } from "@/components/hooks/useResizableColumns";
import {
  // DOC_STATUS_LABELS,
  ITEM_CLASS_LABELS,
} from "./schemas";
import {
  ColumnHeaderMenu,
  type ColumnDef,
  type ColumnState,
  type ColumnStates,
} from "@/core/notes/ColumnHeaderMenu";
import { useTablePreferences } from "@/lib/ui-preferences/useTablePreferences";
import {
  columnFilterFromApi,
  columnFilterToApi,
  columnSortFromApi,
  columnSortToApi,
} from "@/lib/ui-preferences/tableColumnStates";

type ItemTypesListParams = NonNullable<
  Parameters<typeof getSalesItemTypesSalesItemTypesGet>[0]
>;
type ItemTypesQueryFilters = Omit<ItemTypesListParams, "skip" | "limit">;

const SORT_FIELD_BY_COLUMN: Record<string, SalesItemTypeSortField> = {
  name: SalesItemTypeSortField.name,
  item_class: SalesItemTypeSortField.item_class,
  vat_rate: SalesItemTypeSortField.vat_rate,
  doc_number: SalesItemTypeSortField.doc_number,
  updated_at: SalesItemTypeSortField.updated_at,
};

const SORT_FILTER_COLUMNS: ColumnDef[] = [
  { id: SalesItemTypeSortField.name, label: "Наименование", type: "string" },
  {
    id: SalesItemTypeSortField.item_class,
    label: "Тип",
    type: "select",
    options: Object.entries(ITEM_CLASS_LABELS).map(([value, label]) => ({
      value,
      label,
    })),
  },
  { id: SalesItemTypeSortField.vat_rate, label: "НДС %", type: "number" },
  { id: SalesItemTypeSortField.doc_number, label: "Номер", type: "string" },
  { id: SalesItemTypeSortField.updated_at, label: "Обновлено", type: "date" },
];

const COLUMNS = [
  { id: "name", initialWidth: 260, minWidth: 160 },
  { id: "item_class", initialWidth: 140, minWidth: 100 },
  { id: "vat_rate", initialWidth: 100, minWidth: 70 },
  { id: "base_uom", initialWidth: 90, minWidth: 60 },
  { id: "doc_number", initialWidth: 120, minWidth: 80 },
  { id: "updated_at", initialWidth: 160, minWidth: 120 },
  { id: "actions", initialWidth: 100, minWidth: 80 },
];

const buildInitialColumnStates = (): ColumnStates =>
  Object.fromEntries(
    SORT_FILTER_COLUMNS.map((c) => [c.id, { sort: null, filter: null }]),
  );

// ── Персистентный вид таблицы (серверный, как notes/orders) ───────
interface ItemTypesTableViewState {
  columnStates: ColumnStates;
  search: string;
  page: number;
}

const ITEM_TYPES_TABLE_DEFAULT_STATE: ItemTypesTableViewState = {
  columnStates: buildInitialColumnStates(),
  search: "",
  page: 1,
};

const toStoredItemTypes = (
  state: ItemTypesTableViewState,
): TablePreferenceSchema => ({
  column_states: Object.fromEntries(
    Object.entries(state.columnStates).map(([key, value]) => [
      key,
      {
        sort: columnSortToApi(value.sort),
        filter: columnFilterToApi(value.filter),
      },
    ]),
  ),
  search: state.search,
  page: state.page,
  page_size: 15,
});

const fromStoredItemTypes = (
  stored: TablePreferenceSchema | undefined,
  defaults: ItemTypesTableViewState,
): ItemTypesTableViewState => {
  if (stored === undefined) return defaults;

  const columnStates: ColumnStates = buildInitialColumnStates();
  const storedColumns: TablePreferenceSchemaColumnStates =
    stored.column_states ?? {};

  for (const column of SORT_FILTER_COLUMNS) {
    const raw: TableColumnStateSchema | undefined = storedColumns[column.id];
    if (raw === undefined) continue;
    columnStates[column.id] = {
      sort: columnSortFromApi(raw.sort),
      filter: columnFilterFromApi(raw.filter),
    };
  }

  return {
    columnStates,
    search: stored.search ?? "",
    page: stored.page ?? 1,
  };
};

export const ItemTypesPage = () => {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const {
    state: viewState,
    setState: setViewState,
    isRestored,
  } = useTablePreferences<ItemTypesTableViewState>({
    tableKey: "sales-item-types",
    defaultState: ITEM_TYPES_TABLE_DEFAULT_STATE,
    toStored: toStoredItemTypes,
    fromStored: fromStoredItemTypes,
  });

  const columnStates: ColumnStates = viewState.columnStates;
  const search: string = viewState.search;
  const page: number = viewState.page;
  const [limit] = useState(15);

  // ✅ Правило №47: состояние ввода поиска — транзиентное и живёт ВНЕ
  // персистентного view-state. Иначе каждый keystroke проходит round-trip
  // patch → fromStored и сбрасывает поле в применённое значение.
  const [searchInput, setSearchInput] = useState<string>("");
  const searchInputInitializedRef = useRef<boolean>(false);

  // После восстановления настроек показываем применённый поиск в поле
  // (однократно, защищено ref от сброса фоновыми refetch/overlay).
  useEffect(() => {
    if (!isRestored || searchInputInitializedRef.current) return;
    searchInputInitializedRef.current = true;
    setSearchInput(search);
  }, [isRestored, search, setSearchInput]);

  const setPage = useCallback(
    (next: number): void => setViewState((prev) => ({ ...prev, page: next })),
    [setViewState],
  );
  const setSearch = useCallback(
    (next: string): void => setViewState((prev) => ({ ...prev, search: next })),
    [setViewState],
  );

  const setColumnStates = useCallback<
    (action: ColumnStates | ((prev: ColumnStates) => ColumnStates)) => void
  >(
    (action) =>
      setViewState((prev) => ({
        ...prev,
        columnStates:
          typeof action === "function" ? action(prev.columnStates) : action,
      })),
    [setViewState],
  );

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingItemType, setEditingItemType] =
    useState<SalesItemTypeResponseSchema | null>(null);
  const [deleteItemTypeId, setDeleteItemTypeId] = useState<string | null>(null);
  const [highlightedItemTypeId, setHighlightedItemTypeId] = useState<
    string | null
  >(null);
  const [readOnly, setReadOnly] = useState(false);
  const [readOnlyReason, setReadOnlyReason] = useState<string>("");
  const [copyingItemType, setCopyingItemType] =
    useState<SalesItemTypeResponseSchema | null>(null);
  const [isCopyOpen, setIsCopyOpen] = useState(false);

  const { widths, handleMouseDown, resetWidths } = useResizableColumns(
    COLUMNS,
    "sales-item-types-table-widths",
  );

  const sortColumnId = useMemo(
    () =>
      Object.keys(columnStates).find((id) => columnStates[id].sort !== null) ??
      null,
    [columnStates],
  );
  const sortDirection = sortColumnId ? columnStates[sortColumnId].sort : null;

  const strFilter = useCallback(
    (columnId: string): string | undefined => {
      const value = columnStates[columnId]?.filter;
      return typeof value === "string" && value.length > 0 ? value : undefined;
    },
    [columnStates],
  );

  const hasActiveFiltersOrSort = useMemo(
    () =>
      sortColumnId !== null ||
      Object.values(columnStates).some(
        (s) => s.filter !== null && s.filter !== "",
      ),
    [columnStates, sortColumnId],
  );

  const queryFilters: ItemTypesQueryFilters = useMemo(
    () => ({
      search: search || undefined,
      sort_by: sortColumnId ? SORT_FIELD_BY_COLUMN[sortColumnId] : undefined,
      sort_order: sortColumnId
        ? sortDirection === "desc"
          ? SortOrder.desc
          : SortOrder.asc
        : undefined,
      filter_name: strFilter("name"),
      filter_item_class: strFilter("item_class"),
      filter_vat_rate: strFilter("vat_rate"),
      filter_doc_number: strFilter("doc_number"),
      filter_updated_at: strFilter("updated_at"),
    }),
    [search, sortColumnId, sortDirection, strFilter],
  );

  const { data, isLoading, refetch } = useGetSalesItemTypesSalesItemTypesGet(
    { skip: (page - 1) * limit, limit, ...queryFilters },
    { query: { enabled: isRestored, placeholderData: keepPreviousData } },
  );

  const deleteMutation = useDeleteSalesItemTypeSalesItemTypesItemTypeIdDelete();
  const acquireLockMutation =
    useAcquireSalesItemTypeLockSalesItemTypesItemTypeIdLockPost();
  const releaseLockMutation =
    useReleaseSalesItemTypeLockSalesItemTypesItemTypeIdLockDelete();

  const pageMeta = data?.data;
  const items: SalesItemTypeResponseSchema[] = useMemo(
    () => pageMeta?.items ?? [],
    [pageMeta?.items],
  );
  const total: number = pageMeta?.total ?? 0;
  const totalPages: number = Math.max(1, Math.ceil(total / limit));

  useEffect(() => {
    if (!isRestored || data === undefined) return;
    if (page > totalPages) setPage(totalPages);
  }, [isRestored, data, page, totalPages, setPage]);

  const handleColumnChange = useCallback(
    (columnId: string, patch: Partial<ColumnState>) => {
      setColumnStates((prev) => {
        const next: ColumnStates = {
          ...prev,
          [columnId]: { ...prev[columnId], ...patch },
        };
        if (patch.sort !== undefined && patch.sort !== null) {
          for (const key of Object.keys(next)) {
            if (key !== columnId) next[key] = { ...next[key], sort: null };
          }
        }
        return next;
      });
      setPage(1);
    },
    [setColumnStates, setPage],
  );

  const resetFiltersAndSort = useCallback(() => {
    setColumnStates(buildInitialColumnStates());
    setPage(1);
  }, [setColumnStates, setPage]);

  const handleSaved = useCallback(
    async (id: string, name?: string): Promise<void> => {
      await queryClient.invalidateQueries({ queryKey: ["sales-item-types"] });
      const refreshed = await refetch();
      const currentItems: SalesItemTypeResponseSchema[] =
        refreshed.data?.data?.items ?? [];
      if (currentItems.some((item) => item.id === id)) {
        setHighlightedItemTypeId(id);
        toast({ title: "Успешно сохранено" });
        return;
      }
      try {
        const fullList = await getSalesItemTypesSalesItemTypesGet({
          limit: 1000,
          skip: 0,
          ...queryFilters,
        });
        const foundIndex: number = (fullList.data?.items ?? []).findIndex(
          (item) => item.id === id,
        );
        if (foundIndex === -1) {
          toast({
            title: "Сохранено",
            description: hasActiveFiltersOrSort
              ? "Запись не отображается в текущем списке: она не подходит под активные фильтры или условия поиска."
              : "Запись не найдена в списке. Обновите страницу.",
          });
          return;
        }
        const targetPage: number = Math.floor(foundIndex / limit) + 1;
        toast({
          title: "Сохранено",
          description: `Запись «${name ?? ""}» теперь на странице ${targetPage}.`,
          action: (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setPage(targetPage);
                setHighlightedItemTypeId(id);
              }}
            >
              Перейти
            </Button>
          ),
        });
      } catch (error: unknown) {
        const err = error as { response?: { data?: { detail?: string } } };
        toast({
          variant: "destructive",
          title: "Ошибка навигации",
          description:
            err?.response?.data?.detail || "Не удалось определить страницу",
        });
      }
    },
    [
      queryClient,
      refetch,
      queryFilters,
      limit,
      setPage,
      toast,
      hasActiveFiltersOrSort,
    ],
  );

  const handleDelete = async (): Promise<void> => {
    if (!deleteItemTypeId) return;
    try {
      await deleteMutation.mutateAsync({ itemTypeId: deleteItemTypeId });
      await refetch();
      setDeleteItemTypeId(null);
      toast({ title: "Тип номенклатуры удалён" });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      toast({
        variant: "destructive",
        title: "Ошибка удаления",
        description: err?.response?.data?.detail || "Не удалось удалить",
      });
    }
  };

  const openEdit = async (item: SalesItemTypeResponseSchema): Promise<void> => {
    setEditingItemType(item);
    if (item.is_editing_locked) {
      setReadOnly(true);
      setReadOnlyReason(
        "Документ редактируется другим пользователем. Вы можете только просматривать данные.",
      );
      setIsModalOpen(true);
      return;
    }
    try {
      await acquireLockMutation.mutateAsync({ itemTypeId: item.id });
      setReadOnly(false);
      setReadOnlyReason("");
      setIsModalOpen(true);
    } catch (error: unknown) {
      const err = error as {
        response?: { status?: number; data?: { detail?: string } };
      };
      const status = err?.response?.status;
      if (status === 403) {
        setReadOnly(true);
        setReadOnlyReason(
          "У вас нет прав на изменение этого документа. Доступен только просмотр.",
        );
        setIsModalOpen(true);
      } else if (status === 423) {
        setReadOnly(true);
        setReadOnlyReason(
          "Документ редактируется другим пользователем. Открыт в режиме только для чтения.",
        );
        setIsModalOpen(true);
        toast({
          variant: "destructive",
          title: "Документ занят",
          description: "Документ редактируется другим пользователем.",
        });
      } else {
        toast({
          variant: "destructive",
          title: "Ошибка блокировки",
          description:
            err?.response?.data?.detail || "Не удалось открыть документ",
        });
      }
    }
  };

  const openCopy = (item: SalesItemTypeResponseSchema): void => {
    setCopyingItemType(item);
    setIsCopyOpen(true);
  };

  const handleCopyModalOpenChange = (open: boolean): void => {
    setIsCopyOpen(open);
    if (!open) setCopyingItemType(null);
  };

  const handleModalClose = async (open: boolean): Promise<void> => {
    if (!open && editingItemType && !readOnly) {
      try {
        await releaseLockMutation.mutateAsync({
          itemTypeId: editingItemType.id,
        });
      } catch {
        // Ошибки освобождения игнорируются (таймаут 30 минут снимет блокировку)
      }
    }
    setIsModalOpen(open);
    if (!open) {
      setEditingItemType(null);
      setReadOnly(false);
      setReadOnlyReason("");
    }
  };

  useEffect(() => {
    if (
      highlightedItemTypeId &&
      items.some((item) => item.id === highlightedItemTypeId)
    ) {
      const timer = setTimeout(() => setHighlightedItemTypeId(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [items, highlightedItemTypeId]);

  const openCreate = (): void => {
    setEditingItemType(null);
    setReadOnly(false);
    setIsModalOpen(true);
  };

  const formatDate = (iso: string | null | undefined): string => {
    if (!iso) return "—";
    return new Date(iso).toLocaleString("ru-RU", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const renderSortableHeader = (columnId: string) => {
    const col = SORT_FILTER_COLUMNS.find((c) => c.id === columnId);
    if (!col) return null;
    return (
      <TableHead
        style={{ width: widths[columnId as keyof typeof widths] }}
        className="relative"
      >
        <ColumnHeaderMenu
          column={col}
          state={columnStates[columnId]}
          onChange={handleColumnChange}
        />
        <div
          className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
          onMouseDown={(e) => handleMouseDown(columnId, e)}
        />
      </TableHead>
    );
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Типы номенклатуры</h1>
          <p className="text-xs text-muted-foreground mt-0.5 tabular-nums">
            Всего: {total}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={resetWidths}>
            Сбросить ширину
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={resetFiltersAndSort}
            disabled={!hasActiveFiltersOrSort}
          >
            Сбросить фильтры/сортировку
          </Button>
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4 mr-2" /> Создать тип
          </Button>
        </div>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          setSearch(searchInput);
          setPage(1);
        }}
        className="flex gap-2"
      >
        <Input
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Поиск по наименованию и описанию..."
          className="max-w-md"
        />
        <Button type="submit">
          <Search className="h-4 w-4 mr-2" /> Найти
        </Button>
      </form>

      {!isRestored || isLoading ? (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="h-6 w-6 animate-spin" />
        </div>
      ) : (
        <div className="rounded-md border overflow-auto max-h-[calc(100vh-260px)]">
          <Table className="table-fixed w-full">
            <TableHeader className="sticky top-0 bg-background z-10 shadow-sm">
              <TableRow className="h-10 hover:bg-transparent">
                {renderSortableHeader("name")}
                {renderSortableHeader("item_class")}
                {renderSortableHeader("vat_rate")}
                <TableHead
                  style={{ width: widths.base_uom }}
                  className="relative"
                >
                  Ед. изм.
                </TableHead>
                {renderSortableHeader("doc_number")}
                {renderSortableHeader("updated_at")}
                <TableHead
                  style={{ width: widths.actions }}
                  className="relative"
                >
                  Действия
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.length === 0 ? (
                <TableRow>
                  <TableCell
                    colSpan={7}
                    className="text-center py-8 text-muted-foreground"
                  >
                    {hasActiveFiltersOrSort || search
                      ? "Нет записей, соответствующих условиям"
                      : "Типы номенклатуры не найдены"}
                  </TableCell>
                </TableRow>
              ) : (
                items.map((item) => (
                  <TableRow
                    key={item.id}
                    className={
                      highlightedItemTypeId === item.id
                        ? "bg-yellow-100 dark:bg-yellow-900/30 transition-colors duration-300"
                        : ""
                    }
                  >
                    <TableCell
                      style={{ width: widths.name }}
                      className="py-1 align-top overflow-hidden"
                    >
                      <button
                        type="button"
                        onClick={() => openEdit(item)}
                        className="text-left text-link hover:text-link-hover hover:underline underline-offset-2 font-medium cursor-pointer w-full truncate block focus:outline-none focus:ring-2 focus:ring-link focus:ring-offset-1 rounded-sm transition-colors"
                        title={item.name}
                      >
                        {item.is_editing_locked && (
                          <Lock className="inline h-3 w-3 mr-1 text-amber-500" />
                        )}
                        {item.name}
                      </button>
                    </TableCell>
                    <TableCell
                      style={{ width: widths.item_class }}
                      className="py-1 align-top"
                    >
                      <Badge variant="secondary">
                        {ITEM_CLASS_LABELS[item.item_class] ?? item.item_class}
                      </Badge>
                    </TableCell>
                    <TableCell
                      style={{ width: widths.vat_rate }}
                      className="py-1 align-top text-right tabular-nums"
                    >
                      {Number(item.vat_rate).toFixed(2)}
                    </TableCell>
                    <TableCell
                      style={{ width: widths.base_uom }}
                      className="py-1 align-top overflow-hidden"
                    >
                      <div className="truncate">{item.base_uom ?? "—"}</div>
                    </TableCell>
                    <TableCell
                      style={{ width: widths.doc_number }}
                      className="py-1 align-top overflow-hidden"
                    >
                      <div className="truncate">{item.doc_number ?? "—"}</div>
                    </TableCell>
                    <TableCell
                      style={{ width: widths.updated_at }}
                      className="py-1 align-top text-xs text-muted-foreground"
                    >
                      {formatDate(item.updated_at)}
                    </TableCell>
                    <TableCell
                      style={{ width: widths.actions }}
                      className="py-1 align-top"
                    >
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => openCopy(item)}
                          title="Копировать"
                        >
                          <Copy className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-destructive hover:text-destructive"
                          onClick={() => setDeleteItemTypeId(item.id)}
                          title="Удалить"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-1 mt-3">
          <Button
            size="sm"
            variant="outline"
            className="h-8 w-8 p-0"
            disabled={page === 1}
            onClick={() => setPage(1)}
            aria-label="Первая страница"
          >
            <ChevronsLeft className="h-4 w-4" />
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="h-8 w-8 p-0"
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
            aria-label="Предыдущая страница"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
            let pageNum = i + 1;
            if (totalPages > 5 && page > 3) pageNum = page - 2 + i;
            if (pageNum > totalPages) return null;
            return (
              <Button
                key={pageNum}
                size="sm"
                variant={page === pageNum ? "default" : "outline"}
                className="h-8 w-8 p-0 tabular-nums"
                onClick={() => setPage(pageNum)}
                aria-current={page === pageNum ? "page" : undefined}
              >
                {pageNum}
              </Button>
            );
          })}
          <Button
            size="sm"
            variant="outline"
            className="h-8 w-8 p-0"
            disabled={page === totalPages}
            onClick={() => setPage(page + 1)}
            aria-label="Следующая страница"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="h-8 w-8 p-0"
            disabled={page === totalPages}
            onClick={() => setPage(totalPages)}
            aria-label="Последняя страница"
          >
            <ChevronsRight className="h-4 w-4" />
          </Button>
        </div>
      )}

      <EditItemTypeModal
        open={isModalOpen}
        onOpenChange={handleModalClose}
        initialData={editingItemType}
        onSaved={handleSaved}
        readOnly={readOnly}
        readOnlyReason={readOnlyReason}
      />

      {isCopyOpen && copyingItemType && (
        <EditItemTypeModal
          key={`copy-${copyingItemType.id}`}
          open={isCopyOpen}
          onOpenChange={handleCopyModalOpenChange}
          initialData={null}
          copyFromItemType={copyingItemType}
          onSaved={handleSaved}
        />
      )}

      <AlertDialog
        open={!!deleteItemTypeId}
        onOpenChange={(open) => !open && setDeleteItemTypeId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить тип номенклатуры?</AlertDialogTitle>
            <AlertDialogDescription>
              Запись будет помечена как удалённая (мягкое удаление) и перестанет
              отображаться в списках.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Отмена</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? (
                <Loader2 className="animate-spin mr-2 h-4 w-4" />
              ) : (
                <Trash2 className="mr-2 h-4 w-4" />
              )}
              Удалить
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
