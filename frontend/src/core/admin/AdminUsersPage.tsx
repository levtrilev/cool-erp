import { useState, useEffect } from "react";
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
import { useToast } from "@/components/ui/use-toast";
import { Trash2, Search, Loader2, Shield, User } from "lucide-react";
import {
  useReadUsersAuthGet,
  useDeleteUserAuthUserIdDelete,
  readUsersAuthGet,
} from "@/api/generated/authentication/authentication";
import { EditUserModal } from "@/core/admin/EditUserModal";
import { z } from "zod";
import { readUsersAuthGetResponse } from "@/api/generated/zod/authentication/authentication.schema";

type UserResponseSchema = z.infer<
  typeof readUsersAuthGetResponse
>["items"][number];

export const AdminUsersPage = () => {
  const { toast } = useToast();

  const [page, setPage] = useState(1);
  const [limit] = useState(10);
  const [search, setSearch] = useState("");
  const [deleteUserId, setDeleteUserId] = useState<string | null>(null);

  const [editUser, setEditUser] = useState<UserResponseSchema | null>(null);
  const [editModalOpen, setEditModalOpen] = useState(false);

  // ✅ Единственное состояние для подсветки
  const [highlightedUserId, setHighlightedUserId] = useState<string | null>(
    null,
  );

  const skip = (page - 1) * limit;

  const { data, isLoading, isError, refetch } = useReadUsersAuthGet({
    skip,
    limit,
    search: search || undefined,
  });

  const deleteUserMutation = useDeleteUserAuthUserIdDelete();

  // ✅ Автоматически убираем подсветку через 3 секунды
  useEffect(() => {
    if (highlightedUserId) {
      const timer = setTimeout(() => {
        setHighlightedUserId(null);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [highlightedUserId]);

  // ✅ Основная логика: обработка после обновления
  const handleUserUpdated = async (userId: string, userName: string) => {
    // 1. Перезапрашиваем данные текущей страницы
    const result = await refetch();
    const updatedItems = result.data?.items || [];

    // 2. Проверяем, есть ли пользователь на текущей странице
    const userExists = updatedItems.some((u) => u.id === userId);

    if (userExists) {
      // ✅ Пользователь на текущей странице — просто подсвечиваем
      setHighlightedUserId(userId);
      return;
    }

    // 3. Пользователь переместился на другую страницу — ищем его через Orval-функцию
    // try {
    //   const searchData = await readUsersAuthGet({
    //     search: userName, // Ищем по новому имени
    //     limit: 1000, // Берем с запасом, чтобы найти позицию
    //     skip: 0,
    //   });

    //   if (searchData?.items) {
    //     const userIndex = searchData.items.findIndex(
    //       (u: UserResponseSchema) => u.id === userId,
    //     );

    //     if (userIndex !== -1) {
    //       // Вычисляем номер страницы (индекс / лимит + 1)
    //       const targetPage = Math.floor(userIndex / limit) + 1;

    //       // ✅ Показываем Toast с кнопкой перехода
    //       toast({
    //         title: "Пользователь обновлен",
    //         description: `Запись "${userName}" переместилась на страницу ${targetPage}`,
    //         action: (
    //           <Button
    //             variant="outline"
    //             size="sm"
    //             onClick={() => {
    //               setPage(targetPage);
    //               // После смены страницы подсветим пользователя
    //               setTimeout(() => {
    //                 setHighlightedUserId(userId);
    //               }, 500);
    //             }}
    //           >
    //             Перейти
    //           </Button>
    //         ),
    //       });
    //       return;
    //     }
    //   }

    //   // Если вдруг не нашли (например, изменили имя на то, что не попадает в поиск)
    //   toast({
    //     title: "Пользователь обновлен",
    //     description: "Запись переместилась на другую страницу",
    //   });
    // }
    // 3. Пользователь переместился на другую страницу — ищем его по ID
    try {
      // ✅ Запрашиваем все записи без фильтрации, чтобы найти точную позицию
      const allUsersData = await readUsersAuthGet({
        limit: 1000, // Берем с запасом
        skip: 0,
      });

      if (allUsersData?.items) {
        const userIndex = allUsersData.items.findIndex(
          (u: UserResponseSchema) => u.id === userId,
        );

        if (userIndex !== -1) {
          const targetPage = Math.floor(userIndex / limit) + 1;

          toast({
            title: "Пользователь обновлен",
            description: `Запись "${userName}" переместилась на страницу ${targetPage}`,
            action: (
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setPage(targetPage);
                  setTimeout(() => {
                    setHighlightedUserId(userId);
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
        title: "Пользователь обновлен",
        description: "Запись переместилась на другую страницу",
      });
    } catch (error) {
      console.error("Ошибка поиска пользователя:", error);
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: "Не удалось определить новое местоположение записи",
      });
    }
    // catch (error) {
    //   console.error("Ошибка поиска пользователя:", error);
    //   toast({
    //     variant: "destructive",
    //     title: "Ошибка",
    //     description: "Не удалось определить новое местоположение записи",
    //   });
    // }
  };

  const handleDelete = async (userId: string) => {
    deleteUserMutation.mutate(
      { userId },
      {
        onSuccess: async () => {
          toast({
            title: "Пользователь удален",
            description: "Запись успешно удалена из базы данных",
          });
          await refetch();
          setDeleteUserId(null);
        },
        onError: () => {
          toast({
            variant: "destructive",
            title: "Ошибка",
            description: "Не удалось удалить пользователя",
          });
        },
      },
    );
  };

  const handleEdit = (user: UserResponseSchema) => {
    setEditUser(user);
    setEditModalOpen(true);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="text-center text-destructive py-8">
        Не удалось загрузить список пользователей
      </div>
    );
  }

  const users = data.items || [];
  const total = data.total || 0;
  const totalPages = Math.ceil(total / limit);

  return (
    <div className="container mx-auto px-4 py-3">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-4">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <User className="h-6 w-6 text-primary" />
            Управление пользователями
          </h1>
          <p className="text-muted-foreground mt-1">
            Всего пользователей: {total}
          </p>
        </div>

        <form onSubmit={handleSearch} className="flex gap-2 w-full md:w-auto">
          <Input
            placeholder="Поиск по имени или email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full md:w-64"
          />
          <Button type="submit" variant="secondary">
            <Search className="h-4 w-4 mr-2" />
            Найти
          </Button>
        </form>
      </div>

      <div className="rounded-md border bg-card">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="h-10 py-2">Имя</TableHead>
              <TableHead className="h-10 py-2">Email</TableHead>
              <TableHead className="h-10 py-2">Роль</TableHead>
              <TableHead className="h-10 py-2 text-right">Действия</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={4}
                  className="text-center text-muted-foreground py-8"
                >
                  Пользователи не найдены
                </TableCell>
              </TableRow>
            ) : (
              users.map((user) => (
                <TableRow
                  key={user.id}
                  className={
                    highlightedUserId === user.id
                      ? "bg-yellow-100 dark:bg-yellow-900/30 transition-colors duration-300"
                      : ""
                  }
                >
                  <TableCell className="py-1">
                    <button
                      type="button"
                      onClick={() => handleEdit(user)}
                      className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer text-left font-medium"
                    >
                      {user.name}
                    </button>
                  </TableCell>
                  <TableCell className="py-1">{user.email}</TableCell>
                  <TableCell className="py-1">
                    <div className="flex items-center gap-2">
                      {user.is_superadmin ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                          <Shield className="h-3 w-3 mr-1" /> Супер-админ
                        </span>
                      ) : user.is_admin ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                          <Shield className="h-3 w-3 mr-1" /> Админ
                        </span>
                      ) : (
                        <span className="text-muted-foreground text-sm">
                          Пользователь
                        </span>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="py-1 text-right">
                    <div className="flex justify-end gap-2">
                      <AlertDialog
                        open={deleteUserId === user.id}
                        onOpenChange={(open) => !open && setDeleteUserId(null)}
                      >
                        <AlertDialogTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-destructive hover:text-destructive hover:bg-destructive/10"
                            onClick={() => setDeleteUserId(user.id)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Вы уверены?</AlertDialogTitle>
                            <AlertDialogDescription>
                              Это действие нельзя отменить. Пользователь{" "}
                              <strong>{user.name}</strong> будет безвозвратно
                              удален из системы.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Отмена</AlertDialogCancel>
                            <AlertDialogAction
                              onClick={() => handleDelete(user.id)}
                              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                              disabled={deleteUserMutation.isPending}
                            >
                              {deleteUserMutation.isPending
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

      <EditUserModal
        open={editModalOpen}
        onOpenChange={setEditModalOpen}
        user={editUser}
        onUserUpdated={handleUserUpdated}
      />
    </div>
  );
};
