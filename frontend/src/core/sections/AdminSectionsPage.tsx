import { useState, useEffect, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Plus, Search, Trash2, Loader2, FolderOpen, ShieldCheck } from "lucide-react";
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
import { useToast } from "@/components/ui/use-toast";
import { Badge } from "@/components/ui/badge";
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

// ✅ Единая модалка для создания и редактирования
import { EditSectionModal } from "./EditSectionModal";

// ✅ Правило №9: Orval-хуки
import {
  useGetSectionsSectionsGet,
  getSectionsSectionsGet,
  useDeleteSectionSectionsSectionIdDelete,
} from "@/api/generated/sections/sections";
import { useGetUserAuthUserGet } from "@/api/generated/authentication/authentication";
import type { SectionResponseSchema } from "@/api/generated/fastAPI.schemas";

import { useResizableColumns } from "@/components/hooks/useResizableColumns";
import {
  SECTION_TYPE_BADGE_CLASSES,
  SECTION_TYPE_LABELS,
} from "./schemas";

// ✅ Правило №29: конфигурация колонок для ресайза
const COLUMNS = [
  { id: "name", initialWidth: 250, minWidth: 150 },
  { id: "section_type", initialWidth: 200, minWidth: 130 },
  { id: "tenant_name", initialWidth: 180, minWidth: 120 },
  { id: "description", initialWidth: 220, minWidth: 140 },
  { id: "updated_at", initialWidth: 160, minWidth: 120 },
  { id: "actions", initialWidth: 100, minWidth: 80 },
];

export function AdminSectionsPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Состояния (Правило №22: разделение состояний поиска)
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [limit] = useState(15);
  // ✅ ЕДИНАЯ модалка: для создания — initialData = null
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSection, setEditingSection] =
    useState<SectionResponseSchema | null>(null);
  const [deleteSectionId, setDeleteSectionId] = useState<string | null>(null);
  const [highlightedSectionId, setHighlightedSectionId] = useState<
    string | null
  >(null);

  // ✅ Текущий пользователь для проверки прав
  const { data: currentUser } = useGetUserAuthUserGet();
  const canManageSections: boolean =
    currentUser?.data?.is_admin === true ||
    currentUser?.data?.is_superadmin === true;

  // ✅ Правило №29: ресайз колонок
  // const { widths, handleMouseDown, resetWidths } = useResizableColumns(
  const { widths, handleMouseDown } = useResizableColumns(
    COLUMNS,
    "sections-table-widths"
  );

  // ✅ Правило №9: Orval-хук для списка
  const {
    data: sectionsData,
    isLoading,
    refetch,
  } = useGetSectionsSectionsGet({
    skip: (page - 1) * limit,
    limit,
    search: search || undefined,
  });

  const deleteMutation = useDeleteSectionSectionsSectionIdDelete();

  const items = sectionsData?.data?.items ?? [];
  const total = sectionsData?.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / limit));

  // ✅ Правило №18: Умная навигация + Правило №23: Подсветка
  const handleSaved = useCallback(
    async (id: string, name?: string) => {
      await queryClient.invalidateQueries({ queryKey: ["sections"] });
      await refetch();

      const currentItems = sectionsData?.data?.items ?? [];
      if (currentItems.some((item) => item.id === id)) {
        setHighlightedSectionId(id);
        setTimeout(() => setHighlightedSectionId(null), 3000);
        toast({ title: "Успешно сохранено" });
      } else {
        try {
          const fullList = await getSectionsSectionsGet({
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
            setHighlightedSectionId(id);
            setTimeout(() => setHighlightedSectionId(null), 3000);
            toast({
              title: "Сохранено",
              description: `Запись «${name ?? ""}» на странице ${targetPage}`,
            });
          }
        } catch (error: unknown) {
          // ✅ Правило №36: безопасная обработка ошибок (без console.error)
          const err = error as { response?: { data?: { detail?: string } } };
          toast({
            variant: "destructive",
            title: "Ошибка навигации",
            description:
              err?.response?.data?.detail || "Не удалось найти запись",
          });
        }
      }
    },
    [sectionsData, limit, search, toast, refetch, queryClient]
  );

  // ✅ Правило №16: Удаление через AlertDialog
  // ✅ Правило №25: refetch после удаления
  // ✅ Правило №36: безопасная обработка ошибок (без console.error)
  const handleDelete = async () => {
    if (!deleteSectionId) return;
    try {
      await deleteMutation.mutateAsync({ sectionId: deleteSectionId });
      await refetch();
      setDeleteSectionId(null);
      toast({ title: "Раздел удалён" });
    } catch (error: unknown) {
      const err = error as {
        response?: { data?: { detail?: string }; status?: number };
      };
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;

      let message = "Не удалось удалить раздел";
      if (status === 403) {
        message = detail || "Раздел защищён от удаления";
      } else if (status === 409) {
        message = detail || "Раздел содержит документы и не может быть удалён";
      } else if (detail) {
        message = detail;
      }

      toast({
        variant: "destructive",
        title: "Ошибка удаления",
        description: message,
      });
    }
  };

  // ✅ Открытие модалки создания (Правило №35: одна модалка на два режима)
  const openCreate = () => {
    setEditingSection(null); // ✅ initialData = null → режим создания
    setIsModalOpen(true);
  };

  // ✅ Открытие модалки редактирования
  const openEdit = (section: SectionResponseSchema) => {
    setEditingSection(section); // ✅ initialData = section → режим редактирования
    setIsModalOpen(true);
  };

  // ✅ Правило №12: Поиск через form
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput);
    setPage(1);
  };

  // ✅ Правило №17: Автосброс подсветки через 3 секунды
  useEffect(() => {
    if (
      highlightedSectionId &&
      sectionsData?.data?.items?.some((i) => i.id === highlightedSectionId)
    ) {
      const timer = setTimeout(() => setHighlightedSectionId(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [sectionsData, highlightedSectionId]);

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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-3">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 mb-2">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <FolderOpen className="h-5 w-5 text-primary" />
            Разделы
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">Всего: {total}</p>
        </div>

        <div className="flex gap-2 w-full md:w-auto">
          {/* ✅ Кнопка создания только для админа/суперадмина (ТЗ §9) */}
          {canManageSections && (
            <Button onClick={openCreate}>
              <Plus className="h-4 w-4 mr-2" />
              Создать
            </Button>
          )}
          <form
            onSubmit={handleSearch}
            className="flex gap-2 flex-1 md:flex-initial"
          >
            <Input
              placeholder="Поиск по названию..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="w-full md:w-64"
            />
            <Button type="submit" variant="secondary">
              <Search className="h-4 w-4 mr-2" />
              Найти
            </Button>
          </form>
        </div>
      </div>

      {/* ✅ Правила №13/14: Фиксированная ширина + Sticky-заголовки */}
      <div className="rounded-md border bg-card overflow-auto max-h-[calc(100vh-260px)]">
        <Table className="table-fixed w-full">
          <TableHeader className="sticky top-0 bg-background z-10 shadow-sm">
            <TableRow className="h-10 hover:bg-transparent">
              <TableHead style={{ width: widths.name }} className="relative">
                Название
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("name", e)}
                />
              </TableHead>
              <TableHead
                style={{ width: widths.section_type }}
                className="relative"
              >
                Тип раздела
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("section_type", e)}
                />
              </TableHead>
              <TableHead
                style={{ width: widths.tenant_name }}
                className="relative"
              >
                Организация
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("tenant_name", e)}
                />
              </TableHead>
              <TableHead
                style={{ width: widths.description }}
                className="relative"
              >
                Описание
                <div
                  className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/20"
                  onMouseDown={(e) => handleMouseDown("description", e)}
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
              <TableHead style={{ width: widths.actions }} className="relative">
                Действия
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="text-center text-muted-foreground py-8"
                >
                  Разделы не найдены
                </TableCell>
              </TableRow>
            ) : (
              items.map((section) => (
                <TableRow
                  key={section.id}
                  className={
                    highlightedSectionId === section.id
                      ? "bg-yellow-100 dark:bg-yellow-900/30 transition-colors duration-300"
                      : ""
                  }
                >
                  {/* ✅ Правило №11: Компактная ячейка */}
                  <TableCell
                    style={{ width: widths.name }}
                    className="py-1 align-top overflow-hidden"
                  >
                    {/* ✅ Название как кликабельная ссылка для редактирования */}
                    {section.is_protected || !canManageSections ? (
                      <div
                        title={section.name}
                        className="block w-full truncate font-medium"
                      >
                        {section.name}
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => openEdit(section)}
                        className="text-left text-blue-600 hover:text-blue-800 hover:underline cursor-pointer font-medium w-full truncate block"
                        title={section.name}
                      >
                        {section.name}
                      </button>
                    )}
                  </TableCell>

                  {/* ✅ Тип раздела с бейджем */}
                  <TableCell
                    style={{ width: widths.section_type }}
                    className="py-1 align-top"
                  >
                    <Badge
                      variant="secondary"
                      className={
                        SECTION_TYPE_BADGE_CLASSES[section.section_type] ?? ""
                      }
                    >
                      {section.section_type_label ||
                        SECTION_TYPE_LABELS[section.section_type] ||
                        section.section_type}
                    </Badge>
                  </TableCell>

                  {/* ✅ Правило №42: денормализованное имя организации */}
                  <TableCell
                    style={{ width: widths.tenant_name }}
                    className="py-1 align-top overflow-hidden"
                  >
                    <div className="truncate">
                      {(section as SectionResponseSchema & { tenant_name?: string }).tenant_name ?? "—"}
                    </div>
                  </TableCell>

                  <TableCell
                    style={{ width: widths.description }}
                    className="py-1 align-top overflow-hidden"
                  >
                    <div className="truncate">
                      {section.description ?? "—"}
                    </div>
                  </TableCell>

                  <TableCell
                    style={{ width: widths.updated_at }}
                    className="py-1 align-top text-xs text-muted-foreground"
                  >
                    {formatDate(section.updated_at)}
                  </TableCell>

                  {/* ✅ Колонка Действия */}
                  <TableCell
                    style={{ width: widths.actions }}
                    className="py-1 align-top"
                  >
                    {section.is_protected ? (
                      // ✅ Защищённые разделы: только иконка защиты
                      <div
                        className="flex items-center gap-1 text-muted-foreground"
                        title="Защищённый раздел: редактирование и удаление запрещены"
                      >
                        <ShieldCheck className="h-4 w-4 text-blue-500" />
                        <span className="text-xs">Защищён</span>
                      </div>
                    ) : canManageSections ? (
                      // ✅ Произвольные разделы: только удаление
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10"
                          onClick={() => setDeleteSectionId(section.id)}
                          title="Удалить"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ) : (
                      <span className="text-xs text-muted-foreground">
                        Только просмотр
                      </span>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Пагинация */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <span className="text-sm text-muted-foreground">
            Страница {page} из {totalPages}
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
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            >
              Вперёд
            </Button>
          </div>
        </div>
      )}

      {/* ✅ Правило №35: ЕДИНАЯ модалка для создания и редактирования */}
      <EditSectionModal
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        initialData={editingSection}
        onSaved={handleSaved}
      />

      {/* ✅ Правило №16: Удаление через AlertDialog */}
      <AlertDialog
        open={!!deleteSectionId}
        onOpenChange={(open) => !open && setDeleteSectionId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить раздел?</AlertDialogTitle>
            <AlertDialogDescription>
              Раздел будет удалён безвозвратно. Если в разделе есть документы,
              удаление будет отклонено. Это действие нельзя отменить.
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
}