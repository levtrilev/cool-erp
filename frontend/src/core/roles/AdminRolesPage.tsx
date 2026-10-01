import { useState, useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  Search,
  Plus,
  Trash2,
  Loader2,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
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

// Orval хуки и типы (предполагаем, что сгенерированы)
import {
  useGetRolesRolesGet,
  useDeleteRoleRolesRoleIdDelete,
  getRolesRolesGet,
} from "@/api/generated/roles/roles";
import type { RoleResponseSchema } from "@/api/generated/fastAPI.schemas";

import { EditRoleModal } from "@/core/roles/EditRoleModal";

export function AdminRolesPage() {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // --- Состояния (Правило №22) ---
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [limit] = useState(10);

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editingRole, setEditingRole] = useState<RoleResponseSchema | null>(
    null,
  );
  const [deleteRoleId, setDeleteRoleId] = useState<string | null>(null);

  const [highlightedRoleId, setHighlightedRoleId] = useState<string | null>(
    null,
  );

  // --- Orval хуки ---
  const { data, isLoading, isError, refetch } = useGetRolesRolesGet({
    skip: (page - 1) * limit,
    limit,
    search: search || undefined,
  });

  const deleteMutation = useDeleteRoleRolesRoleIdDelete();

  const roles = data?.data?.items ?? [];
  const total = data?.data?.total ?? 0;
  const totalPages = Math.ceil(total / limit);

  // --- Автосброс подсветки (Правило №17) ---
  useEffect(() => {
    if (highlightedRoleId) {
      const timer = setTimeout(() => setHighlightedRoleId(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [highlightedRoleId]);

  // --- Обработчики ---
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setSearch(searchInput);
  };

  const handleEdit = (role: RoleResponseSchema) => {
    setEditingRole(role);
    setEditModalOpen(true);
  };

  const handleCreate = () => {
    setEditingRole(null);
    setIsCreateOpen(true);
  };

  // Умная навигация после создания/обновления (Правило №18, 23)
  const handleRoleSaved = async (newId: string, newName: string) => {
    const result = await refetch();
    const currentItems = result.data?.data?.items || [];

    const itemExists = currentItems.some((i) => i.id === newId);
    if (itemExists) {
      setHighlightedRoleId(newId);
      toast({ title: "Сохранено", description: `Роль "${newName}" обновлена` });
      return;
    }

    try {
      const allData = await getRolesRolesGet({ limit: 1000, skip: 0 });
      const allItems = allData?.data?.items ?? [];
      const itemIndex = allItems.findIndex((i) => i.id === newId);
      const targetPage = Math.floor(itemIndex / limit) + 1;

      toast({
        title: "Сохранено",
        description: `Роль "${newName}" находится на странице ${targetPage}`,
        action: (
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setPage(targetPage);
              setTimeout(() => setHighlightedRoleId(newId), 500);
            }}
          >
            Перейти
          </Button>
        ),
      });
    } catch (error) {
      console.error("Ошибка поиска записи:", error);
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: "Не удалось найти роль",
      });
    }
  };

  const handleDelete = () => {
    if (!deleteRoleId) return;
    deleteMutation.mutate(
      { roleId: deleteRoleId },
      {
        onSuccess: async () => {
          toast({ title: "Удалено", description: "Роль успешно удалена" });
          queryClient.invalidateQueries({ queryKey: ["roles"] });
          await refetch(); // Правило №25
          setDeleteRoleId(null);
        },
        onError: () => {
          toast({
            variant: "destructive",
            title: "Ошибка",
            description: "Не удалось удалить роль",
          });
        },
      },
    );
  };

  if (isError)
    return <div className="p-4 text-destructive">Ошибка загрузки данных</div>;

  return (
    <div className="container mx-auto px-4 py-3">
      {/* Заголовок (Правило №11) */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 mb-2">
        <div>
          <h1 className="text-xl font-bold">Роли</h1>
          <p className="text-xs text-muted-foreground mt-0.5">Всего: {total}</p>
        </div>
        <div className="flex gap-2 w-full md:w-auto">
          <form
            onSubmit={handleSearch}
            className="flex gap-2 flex-1 md:flex-initial"
          >
            <Input
              placeholder="Поиск роли..."
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
        <Table>
          <TableHeader>
            <TableRow className="h-10 py-2 hover:bg-transparent">
              <TableHead>Название</TableHead>
              <TableHead>Описание</TableHead>
              <TableHead>Разделы</TableHead>
              <TableHead className="w-[50px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                </TableCell>
              </TableRow>
            ) : roles.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={4}
                  className="text-center text-muted-foreground py-8"
                >
                  Роли не найдены
                </TableCell>
              </TableRow>
            ) : (
              roles.map((role) => (
                <TableRow
                  key={role.id}
                  className={
                    highlightedRoleId === role.id
                      ? "bg-yellow-100 dark:bg-yellow-900/30 transition-colors duration-300"
                      : ""
                  }
                >
                  {/* Первая колонка как ссылка (Правило №14) */}
                  <TableCell className="py-1">
                    <button
                      type="button"
                      onClick={() => handleEdit(role)}
                      className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer text-left font-medium"
                    >
                      {role.name}
                    </button>
                  </TableCell>
                  <TableCell className="py-1 text-muted-foreground">
                    {role.description || "—"}
                  </TableCell>
                  <TableCell className="py-1">
                    <div className="flex flex-wrap gap-1">
                      {role.section_names && role.section_names.length > 0 ? (
                        role.section_names.map((name, idx) => (
                          <Badge
                            key={idx}
                            variant="secondary"
                            className="text-xs"
                          >
                            {name}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-muted-foreground text-xs">
                          Не назначены
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="py-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="text-destructive hover:text-destructive hover:bg-destructive/10"
                      onClick={() => setDeleteRoleId(role.id)}
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

      {/* Пагинация (Правило №15) */}
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
            let pageNum = i + 1;
            if (totalPages > 5 && page > 3) pageNum = page - 2 + i;
            if (pageNum > totalPages) return null;
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

      {/* Модалка создания/редактирования (Правило №20) */}
      {isCreateOpen && (
        <EditRoleModal
          open={isCreateOpen}
          onOpenChange={setIsCreateOpen}
          role={null} // ✅ Явно передаём null для режима создания
          onRoleSaved={handleRoleSaved}
        />
      )}
      {editingRole && (
        <EditRoleModal
          key={editingRole.id}
          open={editModalOpen}
          onOpenChange={setEditModalOpen}
          role={editingRole}
          onRoleSaved={handleRoleSaved}
        />
      )}

      {/* AlertDialog для удаления (Правило №16) */}
      <AlertDialog
        open={!!deleteRoleId}
        onOpenChange={(open) => !open && setDeleteRoleId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить роль?</AlertDialogTitle>
            <AlertDialogDescription>
              Это действие нельзя отменить. Все пользователи, которым назначена
              эта роль, потеряют к ней доступ.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Отмена</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Удалить
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
