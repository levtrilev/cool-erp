// frontend/src/core/doctypes/DoctypesPage.tsx
import { useState, useEffect, useMemo, useCallback } from "react";
import type { FormEvent } from "react";
import { keepPreviousData } from "@tanstack/react-query";
import {
  Plus,
  Search,
  Trash2,
  Loader2,
  CheckCircle2,
  XCircle,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { useToast } from "@/components/ui/use-toast";
import { useResizableColumns } from "@/components/hooks/useResizableColumns";
import {
  useGetDoctypesDoctypesGet,
  useDeleteDoctypeDoctypesDoctypeIdDelete,
} from "@/api/generated/doctypes/doctypes";
import { getDoctypesDoctypesGet } from "@/api/generated/doctypes/doctypes";
import type { DoctypeResponseSchema } from "@/api/generated/coolERP.schemas";
import { EditDoctypeModal } from "./EditDoctypeModal";

/** Размеры страницы, доступные пользователю. */
const PAGE_SIZE_OPTIONS: readonly number[] = [10, 15, 25, 50, 100];
const DEFAULT_PAGE_SIZE = 10;

/** Сколько кнопок номеров показываем одновременно (включая первую и последнюю). */
const MAX_VISIBLE_PAGES = 7;

/** Элемент ленты номеров: либо номер страницы, либо разрыв. */
type PageItem = number | "gap-left" | "gap-right";

/**
 * Лента номеров страниц постоянной длины:
 * первая, последняя и окно вокруг текущей, разрывы обозначаются многоточием.
 * Длина не меняется при навигации — панель не «прыгает».
 */
const buildPageItems = (current: number, total: number): PageItem[] => {
  if (total <= MAX_VISIBLE_PAGES) {
    return Array.from({ length: total }, (_, index) => index + 1);
  }
  const windowStart: number = Math.max(2, Math.min(current - 1, total - 4));
  const windowEnd: number = Math.min(total - 1, Math.max(current + 1, 5));

  const items: PageItem[] = [1];
  if (windowStart > 2) items.push("gap-left");
  for (let value = windowStart; value <= windowEnd; value += 1) {
    items.push(value);
  }
  if (windowEnd < total - 1) items.push("gap-right");
  items.push(total);
  return items;
};

export const DoctypesPage = () => {
  const { toast } = useToast();

  // ✅ Правило №22: раздельные состояния ввода и запроса
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");

  // ✅ Пагинация: номер страницы и размер страницы
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);
  const [jumpInput, setJumpInput] = useState("");

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingDoctype, setEditingDoctype] =
    useState<DoctypeResponseSchema | null>(null);
  const [deleteDoctypeId, setDeleteDoctypeId] = useState<string | null>(null);
  const [highlightedDoctypeId, setHighlightedDoctypeId] = useState<
    string | null
  >(null);

  // ✅ Правило №29: Изменяемые колонки
  const columns = [
    { id: "doctype", initialWidth: 150, minWidth: 100 },
    { id: "doctype_name", initialWidth: 200, minWidth: 100 },
    { id: "domain", initialWidth: 100, minWidth: 50 },
    { id: "is_active", initialWidth: 100, minWidth: 50 },
    { id: "apply_or_tags", initialWidth: 100, minWidth: 50 },
    { id: "apply_and_tags", initialWidth: 100, minWidth: 50 },
    { id: "tenants", initialWidth: 200, minWidth: 150 },
    { id: "actions", initialWidth: 50, minWidth: 50 },
  ];

  const { widths, handleMouseDown, resetWidths } = useResizableColumns(
    columns,
    "doctypes-table-widths",
  );

  // ✅ Производные значения пагинации (Правило №46: useMemo, без setState в effect).
  // keepPreviousData удерживает предыдущий ответ на время запроса новой страницы:
  // total не обнуляется, таблица не мигает, границы страницы не схлопываются.
  const { data, isLoading, isFetching, refetch } = useGetDoctypesDoctypesGet(
    {
      skip: (page - 1) * pageSize,
      limit: pageSize,
      search: search || undefined,
    },
    { query: { placeholderData: keepPreviousData } },
  );

  const pageMeta = data?.data;
  const total: number = pageMeta?.total ?? 0;
  // ✅ Правило №46, п. 2.3: ссылка на список стабилизируется через useMemo.
  // Пока данных нет, пустой массив создаётся один раз и переиспользуется;
  // после загрузки возвращается та же ссылка, что хранит React Query
  // (structural sharing сохраняет её между фоновыми refetch).
  // Зависимость — сама ссылка на массив, а не объект pageMeta целиком.
  const items: DoctypeResponseSchema[] = useMemo(
    () => pageMeta?.items ?? [],
    [pageMeta?.items],
  );

  const totalPages: number = Math.max(1, Math.ceil(total / pageSize));
  
  // Пока данных нет вовсе (первая загрузка) — номер не клампим,
  // иначе запрос ушёл бы на первую страницу вместо запрошенной.
  const currentPage: number = pageMeta ? Math.min(page, totalPages) : page;

  // const shownPage: number = pageMeta?.page ?? currentPage;
  // const shownSize: number = pageMeta?.size ?? pageSize;
  // const rangeStart: number = total === 0 ? 0 : (shownPage - 1) * shownSize + 1;
  // const rangeEnd: number = Math.min(shownPage * shownSize, total);

  // ✅ Диапазон выводится ТОЛЬКО из параметров запроса и total.
  // page/size из ответа не используются: они не соответствуют
  // фактическому skip/limit этого эндпоинта и завышали старт (101 вместо 11).
  // SQL OFFSET/LIMIT даёт полные страницы, кроме последней, поэтому
  // items.length не нужен — диапазон верен и во время keepPreviousData.
  const rangeStart: number = total === 0 ? 0 : (currentPage - 1) * pageSize + 1;
  const rangeEnd: number = Math.min(currentPage * pageSize, total);

  const pageItems: PageItem[] = useMemo(
    () => buildPageItems(currentPage, totalPages),
    [currentPage, totalPages],
  );

  const goToPage = useCallback(
    (next: number): void => {
      setPage(Math.min(Math.max(1, next), totalPages));
    },
    [totalPages],
  );

  const handlePageSizeChange = useCallback((value: string): void => {
    const nextSize: number = Number(value);
    if (!PAGE_SIZE_OPTIONS.includes(nextSize)) return;
    setPageSize(nextSize);
    setPage(1);
  }, []);

  const handleJumpSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>): void => {
      event.preventDefault();
      const parsed: number = Number.parseInt(jumpInput, 10);
      if (!Number.isNaN(parsed)) goToPage(parsed);
      setJumpInput("");
    },
    [jumpInput, goToPage],
  );

  const deleteMutation = useDeleteDoctypeDoctypesDoctypeIdDelete();

  // ✅ Правило №18 и №23: Умная навигация и подсветка
  const handleSaved = async (id: string) => {
    // Берём результат refetch, а не data из замыкания — там прежняя страница.
    const refreshed = await refetch();
    const currentItems: DoctypeResponseSchema[] =
      refreshed.data?.data?.items ?? [];

    if (currentItems.some((item) => item.id === id)) {
      setHighlightedDoctypeId(id);
      toast({ title: "Успешно сохранено" });
      return;
    }

    const fullList = await getDoctypesDoctypesGet({ limit: 1000, skip: 0 });
    const foundIndex: number = (fullList.data?.items ?? []).findIndex(
      (item) => item.id === id,
    );
    if (foundIndex === -1) return;

    const targetPage: number = Math.floor(foundIndex / pageSize) + 1;
    toast({
      title: "Сохранено",
      description: `Запись на странице ${targetPage}`,
      action: (
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            setPage(targetPage);
            setHighlightedDoctypeId(id);
          }}
        >
          Перейти
        </Button>
      ),
    });
  };

  // ✅ Правило №25: refetch() после удаления + безопасная обработка ошибок
  const handleDelete = async () => {
    if (!deleteDoctypeId) return;
    try {
      await deleteMutation.mutateAsync({ doctypeId: deleteDoctypeId });
      setDeleteDoctypeId(null);
      toast({ title: "Удалено" });
      // Если страница опустела, currentPage сам схлопнется к последней.
      await refetch();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      toast({
        variant: "destructive",
        title: "Ошибка удаления",
        description:
          err?.response?.data?.detail || "Не удалось удалить тип документа",
      });
    }
  };

  // ✅ Правило №17: Подсветка через useEffect с автосбросом
  useEffect(() => {
    if (
      highlightedDoctypeId &&
      items.some((item) => item.id === highlightedDoctypeId)
    ) {
      const timer = setTimeout(() => setHighlightedDoctypeId(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [items, highlightedDoctypeId]);

  const openEdit = (item: DoctypeResponseSchema) => {
    setEditingDoctype(item);
    setIsModalOpen(true);
  };

  const isFirstPage: boolean = currentPage <= 1;
  const isLastPage: boolean = currentPage >= totalPages;

  return (
    <div className="container mx-auto px-4 py-3">
      {/* ✅ Правило №11: Компактный заголовок */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 mb-2">
        <div>
          <h1 className="text-xl font-bold">Типы документов</h1>
          <p className="text-xs text-muted-foreground mt-0.5 tabular-nums">
            Всего: {total}
          </p>
        </div>
        <Button
          onClick={() => {
            setEditingDoctype(null);
            setIsModalOpen(true);
          }}
        >
          <Plus className="mr-2 h-4 w-4" /> Создать
        </Button>
      </div>

      {/* ✅ Правило №12: Поиск через form */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setSearch(searchInput);
          setPage(1);
        }}
        className="flex gap-2 mb-2"
      >
        <div className="relative flex-1 max-w-sm">
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Поиск по имени или коду..."
            className="pl-9"
          />
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        </div>
        <Button type="submit" variant="secondary">
          Найти
        </Button>
      </form>

      {/* ✅ Правила №13, №14, №29: Таблица */}
      <div className="rounded-md border bg-card">
        <div className="flex justify-end p-2 border-b">
          <Button
            variant="ghost"
            size="sm"
            onClick={resetWidths}
            className="text-xs"
          >
            Сбросить ширину
          </Button>
        </div>

        <Table className="table-fixed w-full">
          <TableHeader className="sticky top-0 bg-background z-10 shadow-sm">
            <TableRow className="h-10 hover:bg-transparent">
              <TableHead className="relative" style={{ width: widths.doctype }}>
                Код
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("doctype", e)}
                />
              </TableHead>
              <TableHead
                className="relative"
                style={{ width: widths.doctype_name }}
              >
                Название
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("doctype_name", e)}
                />
              </TableHead>
              <TableHead className="relative" style={{ width: widths.domain }}>
                Домен
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("domain", e)}
                />
              </TableHead>
              <TableHead
                className="relative"
                style={{ width: widths.is_active }}
              >
                Активен
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("is_active", e)}
                />
              </TableHead>
              <TableHead
                className="relative"
                style={{ width: widths.apply_or_tags }}
              >
                Разреш.тэги
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("apply_or_tags", e)}
                />
              </TableHead>
              <TableHead
                className="relative"
                style={{ width: widths.apply_and_tags }}
              >
                Обяз.тэги
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("apply_and_tags", e)}
                />
              </TableHead>
              <TableHead className="relative" style={{ width: widths.tenants }}>
                Организации
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("tenants", e)}
                />
              </TableHead>
              <TableHead style={{ width: widths.actions }} />
            </TableRow>
          </TableHeader>

          <TableBody
            className={
              isFetching && !isLoading
                ? "opacity-60 transition-opacity duration-200"
                : "transition-opacity duration-200"
            }
          >
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={8} className="text-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                </TableCell>
              </TableRow>
            ) : items.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={8}
                  className="text-center text-muted-foreground py-8"
                >
                  Не найдено
                </TableCell>
              </TableRow>
            ) : (
              items.map((item) => (
                <TableRow
                  key={item.id}
                  className={
                    highlightedDoctypeId === item.id
                      ? "bg-yellow-100 dark:bg-yellow-900/30 transition-colors duration-300"
                      : ""
                  }
                >
                  <TableCell
                    className="py-1 align-top overflow-hidden"
                    style={{ width: widths.doctype }}
                  >
                    <button
                      type="button"
                      onClick={() => openEdit(item)}
                      title={item.doctype}
                      className="block w-full text-left text-link hover:text-link-hover hover:underline cursor-pointer font-medium truncate"
                    >
                      {item.doctype}
                    </button>
                  </TableCell>
                  <TableCell
                    className="py-1 align-top overflow-hidden"
                    style={{ width: widths.doctype_name }}
                  >
                    <div
                      title={item.doctype_name}
                      className="block w-full truncate"
                    >
                      {item.doctype_name}
                    </div>
                  </TableCell>
                  <TableCell
                    className="py-1 align-top overflow-hidden"
                    style={{ width: widths.domain }}
                  >
                    <div
                      title={item.domain_name || " "}
                      className="block w-full truncate"
                    >
                      {item.domain_name || "—"}
                    </div>
                  </TableCell>
                  <TableCell
                    className="py-1 align-top"
                    style={{ width: widths.is_active }}
                  >
                    {item.is_active ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    ) : (
                      <XCircle className="h-4 w-4 text-muted-foreground" />
                    )}
                  </TableCell>
                  <TableCell
                    className="py-1 align-top"
                    style={{ width: widths.apply_or_tags }}
                  >
                    {item.apply_or_tags ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    ) : (
                      <XCircle className="h-4 w-4 text-muted-foreground" />
                    )}
                  </TableCell>
                  <TableCell
                    className="py-1 align-top"
                    style={{ width: widths.apply_and_tags }}
                  >
                    {item.apply_and_tags ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    ) : (
                      <XCircle className="h-4 w-4 text-muted-foreground" />
                    )}
                  </TableCell>
                  <TableCell
                    className="py-1 align-top overflow-hidden"
                    style={{ width: widths.tenants }}
                  >
                    <span className="text-xs text-muted-foreground tabular-nums">
                      {item.tenant_ids?.length || 0} орг.
                    </span>
                  </TableCell>
                  <TableCell
                    className="py-1 align-top"
                    style={{ width: widths.actions }}
                  >
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-destructive"
                      onClick={() => setDeleteDoctypeId(item.id)}
                      title="Удалить"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>

        {/* ✅ Пагинация: диапазон, размер страницы, навигация, переход */}
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 border-t px-2 py-2">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            {isFetching && (
              <Loader2 className="h-3.5 w-3.5 animate-spin shrink-0" />
            )}
            <span className="tabular-nums">
              {total === 0 ? (
                "Нет записей"
              ) : (
                <>
                  Показано{" "}
                  <span className="font-medium text-foreground">
                    {rangeStart}–{rangeEnd}
                  </span>{" "}
                  из <span className="font-medium text-foreground">{total}</span>
                </>
              )}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <div className="flex items-center gap-2">
              <span className="hidden sm:inline text-xs text-muted-foreground whitespace-nowrap">
                Строк на странице
              </span>
              <Select
                value={String(pageSize)}
                onValueChange={handlePageSizeChange}
              >
                <SelectTrigger
                  className="h-8 w-[72px] text-xs"
                  aria-label="Строк на странице"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent
                  position="popper"
                  sideOffset={4}
                  className="min-w-[72px]"
                >
                  {PAGE_SIZE_OPTIONS.map((option) => (
                    <SelectItem
                      key={option}
                      value={String(option)}
                      className="text-xs"
                    >
                      {option}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <nav
              aria-label="Постраничная навигация"
              className="flex items-center gap-1"
            >
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8"
                onClick={() => goToPage(1)}
                disabled={isFirstPage}
                aria-label="Первая страница"
                title="Первая страница"
              >
                <ChevronsLeft className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8"
                onClick={() => goToPage(currentPage - 1)}
                disabled={isFirstPage}
                aria-label="Предыдущая страница"
                title="Предыдущая страница"
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>

              {pageItems.map((item) =>
                typeof item === "number" ? (
                  <Button
                    key={item}
                    variant={item === currentPage ? "default" : "ghost"}
                    size="icon"
                    className="h-8 min-w-8 px-1.5 text-xs tabular-nums"
                    onClick={() => goToPage(item)}
                    aria-label={`Страница ${item}`}
                    aria-current={item === currentPage ? "page" : undefined}
                  >
                    {item}
                  </Button>
                ) : (
                  <span
                    key={item}
                    aria-hidden="true"
                    className="flex h-8 w-6 items-center justify-center text-xs text-muted-foreground select-none"
                  >
                    …
                  </span>
                ),
              )}

              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8"
                onClick={() => goToPage(currentPage + 1)}
                disabled={isLastPage}
                aria-label="Следующая страница"
                title="Следующая страница"
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
              <Button
                variant="outline"
                size="icon"
                className="h-8 w-8"
                onClick={() => goToPage(totalPages)}
                disabled={isLastPage}
                aria-label="Последняя страница"
                title="Последняя страница"
              >
                <ChevronsRight className="h-4 w-4" />
              </Button>
            </nav>

            <form
              onSubmit={handleJumpSubmit}
              className="hidden lg:flex items-center gap-1.5"
            >
              <label
                htmlFor="doctypes-jump-page"
                className="text-xs text-muted-foreground whitespace-nowrap"
              >
                Перейти
              </label>
              <Input
                id="doctypes-jump-page"
                value={jumpInput}
                onChange={(e) => setJumpInput(e.target.value.replace(/\D/g, ""))}
                inputMode="numeric"
                autoComplete="off"
                placeholder={String(currentPage)}
                disabled={totalPages <= 1}
                className="h-8 w-14 text-center text-xs tabular-nums"
                aria-label={`Номер страницы от 1 до ${totalPages}`}
              />
            </form>
          </div>
        </div>
      </div>

      {/* ✅ Вынесенный компонент модального окна */}
      <EditDoctypeModal
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        initialData={editingDoctype}
        onSaved={handleSaved}
      />

      {/* ✅ Правило №16: AlertDialog для удаления */}
      <AlertDialog
        open={!!deleteDoctypeId}
        onOpenChange={(open) => !open && setDeleteDoctypeId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить тип документа?</AlertDialogTitle>
            <AlertDialogDescription>
              Это действие нельзя отменить. Связанные полномочия могут быть
              затронуты.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Отмена</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground"
            >
              {deleteMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                "Удалить"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};