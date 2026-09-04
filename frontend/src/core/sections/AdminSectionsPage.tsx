import { useState, useEffect } from "react";
import { Plus, Search, Trash2, Loader2, FolderOpen } from "lucide-react";
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
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { CreateSectionModal } from "./CreateSectionModal";
import { EditSectionModal } from "./EditSectionModal";
import {
  useGetSectionsSectionsGet,
  getSectionsSectionsGet,
  useDeleteSectionSectionsSectionIdDelete,
} from "@/api/generated/sections/sections";
import type { SectionResponseSchema } from "@/api/generated/fastAPI.schemas";

export function AdminSectionsPage() {
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [limit] = useState(10);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingSection, setEditingSection] =
    useState<SectionResponseSchema | null>(null);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [deleteSectionId, setDeleteSectionId] = useState<string | null>(null);
  const [highlightedSectionId, setHighlightedSectionId] = useState<
    string | null
  >(null);

  const { toast } = useToast();

  const skip = (page - 1) * limit;

  // Получение списка разделов
  const {
    data: sectionsData,
    isLoading,
    isError,
    refetch,
  } = useGetSectionsSectionsGet({
    skip,
    limit,
    search: search || undefined,
  });

  // Удаление раздела
  const deleteMutation = useDeleteSectionSectionsSectionIdDelete();

  // Автосброс подсветки через 3 секунды
  useEffect(() => {
    if (highlightedSectionId) {
      const timer = setTimeout(() => {
        setHighlightedSectionId(null);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [highlightedSectionId]);

  // ✅ Обработка обновления раздела (из EditSectionModal)
  // Полная логика проверки, на какой странице оказалась запись
  const handleSectionUpdated = async (
    sectionId: string,
    sectionName: string,
  ) => {
    // Сначала обновляем данные текущей страницы
    const result = await refetch();
    const updatedItems = result.data?.data?.items || [];

    // Проверяем, есть ли запись на текущей странице
    const sectionExists = updatedItems.some((s) => s.id === sectionId);

    if (sectionExists) {
      // Запись на текущей странице - подсвечиваем
      setHighlightedSectionId(sectionId);
      toast({
        title: "Раздел обновлен",
        description: "Запись обновлена и выделена в списке",
      });
      return;
    }

    // Записи нет на текущей странице - ищем её в полном списке
    try {
      const allSectionsData = await getSectionsSectionsGet({
        limit: 1000,
        skip: 0,
      });

      if (allSectionsData?.data?.items) {
        const sectionIndex = allSectionsData.data.items.findIndex(
          (s: SectionResponseSchema) => s.id === sectionId,
        );

        if (sectionIndex !== -1) {
          const targetPage = Math.floor(sectionIndex / limit) + 1;
          toast({
            title: "Раздел обновлен",
            description: `Запись "${sectionName}" переместилась на страницу ${targetPage}`,
            action: (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setPage(targetPage);
                  setTimeout(() => {
                    setHighlightedSectionId(sectionId);
                  }, 500);
                }}
              >
                Перейти
              </Button>
            ),
          });
          return;
        }
      }

      toast({
        title: "Раздел обновлен",
        description: "Запись переместилась на другую страницу",
      });
    } catch (error) {
      console.error("Ошибка поиска раздела:", error);
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: "Не удалось определить новое местоположение записи",
      });
    }
  };

  // ✅ Обработка создания раздела (из CreateSectionModal)
  const handleSectionCreated = async (newId: string) => {
    // Сначала обновляем данные текущей страницы
    const result = await refetch();
    const currentItems = result.data?.data?.items || [];

    // Проверяем, есть ли новая запись на текущей странице
    const sectionExists = currentItems.some((s) => s.id === newId);

    if (sectionExists) {
      // Запись на текущей странице - подсвечиваем
      setHighlightedSectionId(newId);
      toast({
        title: "Создано",
        description: "Запись добавлена и выделена в списке",
      });
      return;
    }

    // Записи нет на текущей странице - ищем её в полном списке
    try {
      const allSectionsData = await getSectionsSectionsGet({
        limit: 1000,
        skip: 0,
      });

      if (allSectionsData?.data?.items) {
        const itemIndex = allSectionsData.data.items.findIndex(
          (s: SectionResponseSchema) => s.id === newId,
        );

        if (itemIndex !== -1) {
          const targetPage = Math.floor(itemIndex / limit) + 1;
          toast({
            title: "Создано",
            description: `Запись переместилась на страницу ${targetPage}`,
            action: (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setPage(targetPage);
                  setTimeout(() => {
                    setHighlightedSectionId(newId);
                  }, 500);
                }}
              >
                Перейти
              </Button>
            ),
          });
          return;
        }
      }

      toast({
        title: "Создано",
        description: "Запись успешно добавлена в систему",
      });
    } catch (error) {
      console.error("Ошибка поиска раздела:", error);
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: "Не удалось определить местоположение записи",
      });
    }
  };

  // Удаление
  const handleDelete = (sectionId: string) => {
    deleteMutation.mutate(
      { sectionId },
      {
        onSuccess: async () => {
          toast({
            title: "Раздел удален",
            description: "Запись успешно удалена из базы данных",
          });
          await refetch();
          setDeleteSectionId(null);
        },
        onError: () => {
          toast({
            variant: "destructive",
            title: "Ошибка",
            description: "Не удалось удалить раздел",
          });
        },
      },
    );
  };

  const handleEdit = (section: SectionResponseSchema) => {
    setEditingSection(section);
    setEditModalOpen(true);
  };

  // Поиск через form
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput);
    setPage(1);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (isError || !sectionsData) {
    return (
      <div className="text-center text-destructive py-8">
        Не удалось загрузить список разделов
      </div>
    );
  }

  const sections = sectionsData.data?.items || [];
  const total = sectionsData.data?.total || 0;
  const totalPages = Math.ceil(total / limit);

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
          <Button onClick={() => setIsCreateOpen(true)}>
            <Plus className="h-4 w-4 mr-2" />
            Создать
          </Button>

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

      <div className="rounded-md border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="h-10 py-2">Название</TableHead>
              <TableHead className="h-10 py-2">Организация</TableHead>
              <TableHead className="h-10 py-2 text-right">Действия</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sections.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={2}
                  className="text-center text-muted-foreground py-8"
                >
                  Разделы не найдены
                </TableCell>
              </TableRow>
            ) : (
              sections.map((section) => (
                <TableRow
                  key={section.id}
                  className={
                    highlightedSectionId === section.id
                      ? "bg-yellow-100 dark:bg-yellow-900/30 transition-colors duration-300"
                      : ""
                  }
                >
                  <TableCell className="py-1">
                    <button
                      type="button"
                      onClick={() => handleEdit(section)}
                      className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer text-left font-medium"
                    >
                      {section.name}
                    </button>
                  </TableCell>
                  <TableCell className="py-1">{section.tenant_name}</TableCell>
                  <TableCell className="py-1 text-right">
                    <div className="flex justify-end gap-2">
                      <AlertDialog
                        open={deleteSectionId === section.id}
                        onOpenChange={(open) =>
                          !open && setDeleteSectionId(null)
                        }
                      >
                        <AlertDialogTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-destructive hover:text-destructive hover:bg-destructive/10"
                            onClick={() => setDeleteSectionId(section.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Вы уверены?</AlertDialogTitle>
                            <AlertDialogDescription>
                              Это действие нельзя отменить. Раздел{" "}
                              <strong>{section.name}</strong> будет безвозвратно
                              удалён из системы.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Отмена</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={() => handleDelete(section.id)}
                              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                              disabled={deleteMutation.isPending}
                            >
                              {deleteMutation.isPending
                                ? "Удаление..."
                                : "Удалить"}
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {totalPages > 1 && (
        <div className="mt-6 flex justify-center">
          <Pagination>
            <PaginationContent>
              <PaginationItem>
                <PaginationPrevious
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className={
                    page === 1
                      ? "pointer-events-none opacity-50"
                      : "cursor-pointer"
                  }
                />
              </PaginationItem>

              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                let pageNum = i + 1;
                if (totalPages > 5 && page > 3) {
                  pageNum = page - 2 + i;
                }
                if (pageNum > totalPages) return null;
                return (
                  <PaginationItem key={pageNum}>
                    <PaginationLink
                      isActive={page === pageNum}
                      onClick={() => setPage(pageNum)}
                      className="cursor-pointer"
                    >
                      {pageNum}
                    </PaginationLink>
                  </PaginationItem>
                );
              })}

              <PaginationItem>
                <PaginationNext
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  className={
                    page === totalPages
                      ? "pointer-events-none opacity-50"
                      : "cursor-pointer"
                  }
                />
              </PaginationItem>
            </PaginationContent>
          </Pagination>
        </div>
      )}

      <CreateSectionModal
        open={isCreateOpen}
        onOpenChange={setIsCreateOpen}
        onSectionCreated={handleSectionCreated}
      />

      {editingSection && (
        <EditSectionModal
          key={editingSection.id}
          open={editModalOpen}
          onOpenChange={setEditModalOpen}
          section={editingSection}
          onSectionUpdated={handleSectionUpdated}
        />
      )}
    </div>
  );
}
