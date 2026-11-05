import { useState, useEffect, type FormEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Search,
  Plus,
  Trash2,
  Loader2,
  Lock,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Copy,
} from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
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
import { useResizableColumns } from "@/components/hooks/useResizableColumns";

// ✅ Orval-хуки (Правило №9). Имена уточнить после generate:api.
import {
  useListCompaniesBusinessPartnersCompaniesGet,
  useDeleteCompanyBusinessPartnersCompaniesCompanyIdDelete,
  useAcquireCompanyLockBusinessPartnersCompaniesCompanyIdLockPost,
  useReleaseCompanyLockBusinessPartnersCompaniesCompanyIdLockDelete,
  listCompaniesBusinessPartnersCompaniesGet,
} from "@/api/generated/business-partners-companies/business-partners-companies";
import type { BpCompanyResponseSchema } from "@/api/generated/fastAPI.schemas";
import { EditCompanyModal } from "./EditCompanyModal";

export function CompaniesPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // --- Состояния поиска и пагинации (Правило №22) ---
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [limit] = useState(10);

  // Состояние для копирования
  const [copyFromData, setCopyFromData] =
    useState<BpCompanyResponseSchema | null>(null);
  const [isCopyOpen, setIsCopyOpen] = useState(false);

  // --- Модалка и блокировка (Правило №39) ---
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCompany, setEditingCompany] =
    useState<BpCompanyResponseSchema | null>(null);
  const [readOnly, setReadOnly] = useState(false);

  // --- Удаление (Правило №16) ---
  const [deleteCompanyId, setDeleteCompanyId] = useState<string | null>(null);

  // --- Подсветка строки (Правило №17) ---
  const [highlightedCompanyId, setHighlightedCompanyId] = useState<
    string | null
  >(null);

  // --- Orval-хуки ---
  const { data, isLoading, isError, refetch } =
    useListCompaniesBusinessPartnersCompaniesGet({
      skip: (page - 1) * limit,
      limit,
      search: search || undefined,
    });

  const deleteMutation =
    useDeleteCompanyBusinessPartnersCompaniesCompanyIdDelete();
  const acquireLockMutation =
    useAcquireCompanyLockBusinessPartnersCompaniesCompanyIdLockPost();
  const releaseLockMutation =
    useReleaseCompanyLockBusinessPartnersCompaniesCompanyIdLockDelete();

  const companies: BpCompanyResponseSchema[] = data?.data?.items ?? [];
  const total: number = data?.data?.total ?? 0;
  const totalPages: number = Math.ceil(total / limit);

  // --- Автосброс подсветки (Правило №17) ---
  useEffect(() => {
    if (highlightedCompanyId) {
      const timer = setTimeout(() => setHighlightedCompanyId(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [highlightedCompanyId]);

  // --- Поиск ---
  const handleSearch = (e: FormEvent) => {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput);
  };

  // --- Создание: блокировка не нужна ---
  const handleCreate = () => {
    setEditingCompany(null);
    setReadOnly(false);
    setIsModalOpen(true);
  };

  // Обработчик копирования
  const handleCopy = (item: BpCompanyResponseSchema) => {
    setCopyFromData(item);
    setIsCopyOpen(true);
  };

  // Обработчик закрытия модалки копирования
  const handleCopyModalClose = (open: boolean) => {
    setIsCopyOpen(open);
    if (!open) {
      setCopyFromData(null);
    }
  };

  // ✅ Правило №39: открытие с проверкой и захватом блокировки
  const openEdit = async (item: BpCompanyResponseSchema) => {
    setEditingCompany(item);

    // 1. Уже заблокирован → открываем в режиме только чтения
    if (item.is_editing_locked) {
      setReadOnly(true);
      setIsModalOpen(true);
      toast({
        variant: "destructive",
        title: "Карточка занята",
        description:
          "Компания редактируется другим пользователем. Открыта в режиме только для чтения.",
      });
      return;
    }

    // 2. Свободна → захватываем блокировку
    try {
      await acquireLockMutation.mutateAsync({ companyId: item.id });
      setReadOnly(false);
      setIsModalOpen(true);
    } catch (error: unknown) {
      // ✅ Правило №36
      const err = error as {
        response?: { status?: number; data?: { detail?: string } };
      };

      if (err?.response?.status === 423) {
        setReadOnly(true);
        setIsModalOpen(true);
        toast({
          variant: "destructive",
          title: "Карточка занята",
          description:
            "Компания редактируется другим пользователем. Открыта в режиме только для чтения.",
        });
      } else {
        toast({
          variant: "destructive",
          title: "Ошибка блокировки",
          description:
            err?.response?.data?.detail ||
            "Не удалось открыть карточку компании",
        });
      }
    }
  };

  // ✅ Правило №39: освобождение блокировки при закрытии
  const handleModalClose = async (open: boolean) => {
    if (!open && editingCompany && !readOnly) {
      try {
        await releaseLockMutation.mutateAsync({
          companyId: editingCompany.id,
        });
      } catch {
        // Таймаут 30 минут сам снимет блокировку
      }
    }

    setIsModalOpen(open);
    if (!open) {
      setEditingCompany(null);
      setReadOnly(false);
    }
  };

  // ✅ Умная навигация (Правило №18, №23)
  const handleCompanySaved = async (
    newId: string,
    newName: string,
  ): Promise<void> => {
    const result = await refetch();
    const currentItems: BpCompanyResponseSchema[] =
      result.data?.data?.items ?? [];

    if (currentItems.some((item) => item.id === newId)) {
      setHighlightedCompanyId(newId);
      toast({
        title: "Сохранено",
        description: `Компания "${newName}" обновлена`,
      });
      return;
    }

    try {
      const allData = await listCompaniesBusinessPartnersCompaniesGet({
        limit: 1000,
        skip: 0,
      });
      const allItems: BpCompanyResponseSchema[] = allData?.data?.items ?? [];
      const itemIndex: number = allItems.findIndex((item) => item.id === newId);

      if (itemIndex < 0) {
        toast({
          variant: "destructive",
          title: "Ошибка",
          description: "Не удалось найти сохранённую компанию",
        });
        return;
      }

      const targetPage: number = Math.floor(itemIndex / limit) + 1;
      toast({
        title: "Сохранено",
        description: `Компания "${newName}" на странице ${targetPage}`,
        action: (
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setPage(targetPage);
              setTimeout(() => setHighlightedCompanyId(newId), 500);
            }}
          >
            Перейти
          </Button>
        ),
      });
    } catch {
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: "Не удалось найти сохранённую компанию",
      });
    }
  };

  // ✅ Удаление с обработкой 423 (Правило №16 + №39)
  const handleDelete = () => {
    if (!deleteCompanyId) return;

    deleteMutation.mutate(
      { companyId: deleteCompanyId },
      {
        onSuccess: async () => {
          toast({ title: "Удалено", description: "Компания удалена" });
          queryClient.invalidateQueries({
            queryKey: ["business-partners-companies"],
          });
          await refetch(); // Правило №25
          setDeleteCompanyId(null);
        },
        onError: (error: unknown) => {
          const err = error as {
            response?: { status?: number; data?: { detail?: string } };
          };
          let message: string =
            err?.response?.data?.detail || "Не удалось удалить компанию";

          if (err?.response?.status === 423) {
            message =
              "Компания заблокирована другим пользователем и не может быть удалена";
          }

          toast({
            variant: "destructive",
            title: "Ошибка удаления",
            description: message,
          });
        },
      },
    );
  };

  // ✅ Изменяемая ширина колонок (Правило №29)
  const columns = [
    { id: "name", initialWidth: 220, minWidth: 140 },
    { id: "inn", initialWidth: 130, minWidth: 110 },
    { id: "is_customer", initialWidth: 90, minWidth: 80 },
    { id: "is_supplier", initialWidth: 100, minWidth: 80 },
    { id: "phone", initialWidth: 150, minWidth: 110 },
    { id: "updated_at", initialWidth: 150, minWidth: 120 },
    { id: "actions", initialWidth: 80, minWidth: 60 },
  ];
  const { widths, handleMouseDown, resetWidths } = useResizableColumns(
    columns,
    "companies-table-widths",
  );

  if (isError) {
    return <div className="p-4 text-destructive">Ошибка загрузки данных</div>;
  }

  return (
    <div className="container mx-auto px-4 py-3">
      {/* Заголовок и панель действий */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 mb-2">
        <div>
          <h1 className="text-xl font-bold">Компании</h1>
          <p className="text-xs text-muted-foreground mt-0.5">Всего: {total}</p>
        </div>
        <div className="flex gap-2 w-full md:w-auto">
          <form
            onSubmit={handleSearch}
            className="flex gap-2 flex-1 md:flex-initial"
          >
            <Input
              placeholder="Поиск компании..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="w-full md:w-64"
            />
            <Button type="submit" variant="secondary">
              <Search className="h-4 w-4 mr-2" /> Найти
            </Button>
          </form>
          <Button onClick={handleCreate}>
            <Plus className="h-4 w-4 mr-2" /> Создать
          </Button>
        </div>
      </div>
      {/* Таблица (Правило №13) */}
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
          <TableHeader>
            <TableRow className="h-10 hover:bg-transparent">
              <TableHead
                className="relative"
                style={{ width: `${widths.name}px` }}
              >
                Название
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20 active:bg-primary/40 transition-colors"
                  onMouseDown={(e) => handleMouseDown("name", e)}
                />
              </TableHead>
              <TableHead
                className="relative"
                style={{ width: `${widths.inn}px` }}
              >
                ИНН
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("inn", e)}
                />
              </TableHead>
              <TableHead
                className="relative"
                style={{ width: `${widths.is_customer}px` }}
              >
                Клиент
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("is_customer", e)}
                />
              </TableHead>
              <TableHead
                className="relative"
                style={{ width: `${widths.is_supplier}px` }}
              >
                Поставщик
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("is_supplier", e)}
                />
              </TableHead>
              <TableHead
                className="relative"
                style={{ width: `${widths.phone}px` }}
              >
                Телефон
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("phone", e)}
                />
              </TableHead>
              <TableHead
                className="relative"
                style={{ width: `${widths.updated_at}px` }}
              >
                Обновлено
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("updated_at", e)}
                />
              </TableHead>
              <TableHead style={{ width: `${widths.actions}px` }} />
            </TableRow>
          </TableHeader>

          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                </TableCell>
              </TableRow>
            ) : companies.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={7}
                  className="text-center text-muted-foreground py-8"
                >
                  Компании не найдены
                </TableCell>
              </TableRow>
            ) : (
              companies.map((item) => (
                <TableRow
                  key={item.id}
                  className={
                    highlightedCompanyId === item.id
                      ? "bg-yellow-100 dark:bg-yellow-900/30 transition-colors duration-300"
                      : ""
                  }
                >
                  {/* ✅ Правило №39: название-ссылка + иконка замка */}
                  <TableCell
                    style={{ width: `${widths.name}px` }}
                    className="py-1 align-top overflow-hidden"
                  >
                    <button
                      type="button"
                      onClick={() => openEdit(item)}
                      className="text-left text-blue-600 hover:text-blue-800 hover:underline underline-offset-2 font-medium cursor-pointer w-full truncate block focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 rounded-sm transition-colors"
                      title={item.name}
                    >
                      {item.is_editing_locked && (
                        <Lock className="inline h-3 w-3 mr-1 text-amber-500" />
                      )}
                      {item.name}
                    </button>
                  </TableCell>

                  <TableCell
                    style={{ width: `${widths.inn}px` }}
                    className="py-1 align-top overflow-hidden text-muted-foreground"
                  >
                    <div
                      className="block w-full truncate"
                      title={item.inn || undefined}
                    >
                      {item.inn || "—"}
                    </div>
                  </TableCell>

                  <TableCell
                    style={{ width: `${widths.is_customer}px` }}
                    className="py-1 align-top text-muted-foreground"
                  >
                    {item.is_customer ? "Да" : "—"}
                  </TableCell>

                  <TableCell
                    style={{ width: `${widths.is_supplier}px` }}
                    className="py-1 align-top text-muted-foreground"
                  >
                    {item.is_supplier ? "Да" : "—"}
                  </TableCell>

                  <TableCell
                    style={{ width: `${widths.phone}px` }}
                    className="py-1 align-top overflow-hidden text-muted-foreground"
                  >
                    <div
                      className="block w-full truncate"
                      title={item.phone || undefined}
                    >
                      {item.phone || "—"}
                    </div>
                  </TableCell>

                  <TableCell
                    style={{ width: `${widths.updated_at}px` }}
                    className="py-1 align-top overflow-hidden text-muted-foreground"
                  >
                    <div className="block w-full truncate">
                      {new Date(item.updated_at).toLocaleString("ru-RU", {
                        day: "2-digit",
                        month: "2-digit",
                        year: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </div>
                  </TableCell>

                  {/* ✅ Правило №39: только удаление, без кнопки редактирования */}
                  <TableCell
                    style={{ width: `${widths.actions}px` }}
                    className="py-1 align-top"
                  >
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={() => handleCopy(item)}
                      title="Копировать роль"
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10"
                      onClick={() => setDeleteCompanyId(item.id)}
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
      </div>
      {/* Пагинация */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-1 mt-3">
          <Button
            size="sm"
            variant="outline"
            className="h-8 w-8 p-0"
            disabled={page === 1}
            onClick={() => setPage(1)}
          >
            <ChevronsLeft className="h-4 w-4" />
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="h-8 w-8 p-0"
            disabled={page === 1}
            onClick={() => setPage(page - 1)}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
            let pageNum: number = i + 1;
            if (totalPages > 5 && page > 3) pageNum = page - 2 + i;
            if (pageNum > totalPages || pageNum < 1) return null;
            return (
              <Button
                key={pageNum}
                size="sm"
                variant={page === pageNum ? "default" : "outline"}
                className="h-8 w-8 p-0"
                onClick={() => setPage(pageNum)}
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
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="h-8 w-8 p-0"
            disabled={page === totalPages}
            onClick={() => setPage(totalPages)}
          >
            <ChevronsRight className="h-4 w-4" />
          </Button>
        </div>
      )}
      {/* Модалка (Правило №35, №39) */}
      <EditCompanyModal
        open={isModalOpen}
        onOpenChange={handleModalClose}
        initialData={editingCompany}
        onSaved={handleCompanySaved}
        readOnly={readOnly}
      />
      {/* Рендер модалки копирования */}
      <EditCompanyModal
        open={isCopyOpen}
        onOpenChange={handleCopyModalClose}
        initialData={null} // Режим создания (не редактирования)
        copyFromData={copyFromData} // Данные для копирования
        onSaved={handleCompanySaved}
        readOnly={false} // Копия не блокируется
      />
      {/* Подтверждение удаления (Правило №16) */}
      <AlertDialog
        open={!!deleteCompanyId}
        onOpenChange={(open) => !open && setDeleteCompanyId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить компанию?</AlertDialogTitle>
            <AlertDialogDescription>
              Компания будет удалена. Связанные документы могут быть затронуты.
              Это действие нельзя отменить.
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
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                "Удалить"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
