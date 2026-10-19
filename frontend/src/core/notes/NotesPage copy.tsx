import { useState, useEffect, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Plus,
  Pencil,
  Trash2,
  Search,
  Loader2,
  Lock,
  // Unlock,
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
  useGetNotesNotesGet,
  useDeleteNoteNotesNoteIdDelete,
  getNotesNotesGet,
} from "@/api/generated/notes/notes";
import type { NoteResponseSchema } from "@/api/generated/fastAPI.schemas";

import { EditNoteModal } from "./EditNoteModal";
import { useResizableColumns } from "@/components/hooks/useResizableColumns";
import { DOC_STATUS_LABELS } from "./schemas";

const COLUMNS = [
  { id: "title", initialWidth: 250, minWidth: 150 },
  { id: "doc_number", initialWidth: 120, minWidth: 80 },
  { id: "doc_date", initialWidth: 120, minWidth: 80 },
  { id: "doc_status", initialWidth: 130, minWidth: 100 },
  { id: "section_name", initialWidth: 150, minWidth: 100 },
  { id: "updated_at", initialWidth: 160, minWidth: 120 },
  { id: "actions", initialWidth: 140, minWidth: 120 },
];

export const NotesPage = () => {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Состояния
  const [page, setPage] = useState(1);
  const [limit] = useState(15);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingNote, setEditingNote] =
    useState<NoteResponseSchema | null>(null);
  const [deleteNoteId, setDeleteNoteId] = useState<string | null>(null);
  const [highlightedNoteId, setHighlightedNoteId] = useState<
    string | null
  >(null);

  const { widths, handleMouseDown, resetWidths } = useResizableColumns(
    COLUMNS,
    "notes-table-widths"
  );

  // Orval-хук для списка (Правило №9)
  const { data, isLoading, refetch } = useGetNotesNotesGet({
    skip: (page - 1) * limit,
    limit,
    search: search || undefined,
  });

  const deleteMutation = useDeleteNoteNotesNoteIdDelete();

  const items = data?.data?.items ?? [];
  const total = data?.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  // Обработка сохранения (Правило №18: Умная навигация + Правило №23)
  const handleSaved = useCallback(
    async (id: string, title?: string) => {
      await queryClient.invalidateQueries({ queryKey: ["notes"] });
      await refetch();

      const currentItems = data?.data?.items ?? [];
      if (currentItems.some((item) => item.id === id)) {
        setHighlightedNoteId(id);
        setTimeout(() => setHighlightedNoteId(null), 3000);
        toast({ title: "Успешно сохранено" });
      } else {
        try {
          const fullList = await getNotesNotesGet({
            limit: 1000,
            skip: 0,
            search: search || undefined,
          });
          const foundIndex = (fullList?.data?.items ?? []).findIndex(
            (item) => item.id === id
          );
          if (foundIndex !== -1) {
            const targetPage = Math.ceil((foundIndex + 1) / limit);
            setPage(targetPage);
            setHighlightedNoteId(id);
            setTimeout(() => setHighlightedNoteId(null), 3000);
            toast({
              title: "Сохранено",
              description: `Запись «${title ?? ""}» на странице ${targetPage}`,
            });
          }
        } catch (error: unknown) {
          const err = error as {
            response?: { data?: { detail?: string } };
          };
          toast({
            variant: "destructive",
            title: "Ошибка навигации",
            description:
              err?.response?.data?.detail || "Не удалось найти запись",
          });
        }
      }
    },
    [data, limit, search, toast, refetch, queryClient]
  );

  // Удаление (Правило №16 + Правило №25)
  const handleDelete = async () => {
    if (!deleteNoteId) return;
    try {
      await deleteMutation.mutateAsync({ noteId: deleteNoteId });
      await refetch();
      setDeleteNoteId(null);
      toast({ title: "Заметка удалена" });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      toast({
        variant: "destructive",
        title: "Ошибка удаления",
        description: err?.response?.data?.detail || "Не удалось удалить",
      });
    }
  };

  // Подсветка строки (Правило №17/23)
  useEffect(() => {
    if (
      highlightedNoteId &&
      data?.data?.items?.some((i) => i.id === highlightedNoteId)
    ) {
      const timer = setTimeout(
        () => setHighlightedNoteId(null),
        3000
      );
      return () => clearTimeout(timer);
    }
  }, [data, highlightedNoteId]);

  const openCreate = () => {
    setEditingNote(null);
    setIsModalOpen(true);
  };

  const openEdit = (item: NoteResponseSchema) => {
    setEditingNote(item);
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

  const formatDocDate = (iso: string | null | undefined): string => {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("ru-RU");
  };

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Заметки</h1>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={resetWidths}>
            Сбросить ширину
          </Button>
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4 mr-2" />
            Создать заметку
          </Button>
        </div>
      </div>

      {/* Поиск через form (Правило №12/22) */}
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
          placeholder="Поиск по названию и содержимому..."
          className="max-w-md"
        />
        <Button type="submit">
          <Search className="h-4 w-4 mr-2" />
          Найти
        </Button>
      </form>

      {/* Таблица (Правила №11/13/14/29) */}
      {isLoading ? (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="h-6 w-6 animate-spin" />
        </div>
      ) : (
        <div className="rounded-md border overflow-auto max-h-[calc(100vh-260px)]">
          <Table className="table-fixed w-full">
            <TableHeader className="sticky top-0 bg-background z-10 shadow-sm">
              <TableRow className="h-10 hover:bg-transparent">
                <TableHead
                  style={{ width: widths.title }}
                  className="relative"
                >
                  Название
                  <div
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                    onMouseDown={(e) => handleMouseDown("title", e)}
                  />
                </TableHead>
                <TableHead
                  style={{ width: widths.doc_number }}
                  className="relative"
                >
                  Номер
                  <div
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                    onMouseDown={(e) => handleMouseDown("doc_number", e)}
                  />
                </TableHead>
                <TableHead
                  style={{ width: widths.doc_date }}
                  className="relative"
                >
                  Дата
                  <div
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                    onMouseDown={(e) => handleMouseDown("doc_date", e)}
                  />
                </TableHead>
                <TableHead
                  style={{ width: widths.doc_status }}
                  className="relative"
                >
                  Статус
                  <div
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                    onMouseDown={(e) => handleMouseDown("doc_status", e)}
                  />
                </TableHead>
                <TableHead
                  style={{ width: widths.section_name }}
                  className="relative"
                >
                  Раздел
                  <div
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                    onMouseDown={(e) =>
                      handleMouseDown("section_name", e)
                    }
                  />
                </TableHead>
                <TableHead
                  style={{ width: widths.updated_at }}
                  className="relative"
                >
                  Обновлено
                  <div
                    className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                    onMouseDown={(e) => handleMouseDown("updated_at", e)}
                  />
                </TableHead>
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
                    Заметки не найдены
                  </TableCell>
                </TableRow>
              ) : (
                items.map((item) => (
                  <TableRow
                    key={item.id}
                    className={
                      highlightedNoteId === item.id
                        ? "bg-yellow-100 dark:bg-yellow-900/30 transition-colors duration-300"
                        : ""
                    }
                  >
                    <TableCell
                      style={{ width: widths.title }}
                      className="py-1 align-top overflow-hidden"
                    >
                      <div
                        title={item.title}
                        className="block w-full truncate font-medium"
                      >
                        {item.is_editing_locked && (
                          <Lock className="inline h-3 w-3 mr-1 text-amber-500" />
                        )}
                        {item.title}
                      </div>
                    </TableCell>
                    <TableCell
                      style={{ width: widths.doc_number }}
                      className="py-1 align-top overflow-hidden"
                    >
                      <div className="truncate">
                        {item.doc_number ?? "—"}
                      </div>
                    </TableCell>
                    <TableCell
                      style={{ width: widths.doc_date }}
                      className="py-1 align-top"
                    >
                      {formatDocDate(item.doc_date)}
                    </TableCell>
                    <TableCell
                      style={{ width: widths.doc_status }}
                      className="py-1 align-top"
                    >
                      <Badge variant="secondary">
                        {DOC_STATUS_LABELS[item.doc_status] ??
                          item.doc_status}
                      </Badge>
                    </TableCell>
                    <TableCell
                      style={{ width: widths.section_name }}
                      className="py-1 align-top overflow-hidden"
                    >
                      <div className="truncate">
                        {(item as NoteResponseSchema & { section_name?: string }).section_name ?? "—"}
                      </div>
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
                          onClick={() => openEdit(item)}
                          title="Редактировать"
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
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
                ))
              )}
            </TableBody>
          </Table>
        </div>
      )}

      {/* Пагинация */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            Всего: {total}. Страница {page} из {totalPages}
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page === 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Назад
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page === totalPages}
              onClick={() =>
                setPage((p) => Math.min(totalPages, p + 1))
              }
            >
              Вперёд
            </Button>
          </div>
        </div>
      )}

      {/* Модалка (Правило №35) */}
      <EditNoteModal
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        initialData={editingNote}
        onSaved={handleSaved}
      />

      {/* AlertDialog удаления (Правило №16) */}
      <AlertDialog
        open={!!deleteNoteId}
        onOpenChange={(open) => !open && setDeleteNoteId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить заметку?</AlertDialogTitle>
            <AlertDialogDescription>
              Заметка будет помечена как удалённая (мягкое удаление).
              Запись останется в БД для аудита, но перестанет отображаться
              в списках.
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