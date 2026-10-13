import { useMemo, useState } from "react";
import { Trash2, Undo2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ReferenceSelect } from "@/lib/reusable/ReferenceSelect";
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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useToast } from "@/components/ui/use-toast";
import type { UserResponseSchema } from "@/api/generated/fastAPI.schemas";

/**
 * Черновик пользователя (edit-состояние).
 */
export interface UserDraft {
  id: string;
  name: string;
  email?: string;
  markedForDeletion?: boolean;
}

interface UsersTabProps {
  /** Текущий черновик пользователей (поднят в родителя) */
  users: UserDraft[];
  /** Callback для обновления черновика */
  onUsersChange: (users: UserDraft[]) => void;
  /** Полный справочник пользователей для выбора */
  allUsers: UserResponseSchema[];
  /** ID пользователей, которые были в исходном состоянии (для пометки "новый") */
  initialUserIds: string[];
}

export const UsersTab = ({
  users,
  onUsersChange,
  allUsers,
  initialUserIds,
}: UsersTabProps) => {
  const { toast } = useToast();
  const [userToToggle, setUserToToggle] = useState<UserDraft | null>(null);
  const [selectKey, setSelectKey] = useState(0);

  const handleAddUser = (userId: string) => {
    const userToAdd = allUsers.find((u) => u.id === userId);
    if (!userToAdd) return;

    const existingIndex = users.findIndex((u) => u.id === userId);

    let newUsers: UserDraft[];
    if (existingIndex !== -1) {
      newUsers = users.map((u, idx) =>
        idx === existingIndex ? { ...u, markedForDeletion: false } : u,
      );
    } else {
      const newUser: UserDraft = {
        id: userToAdd.id,
        name: userToAdd.name,
        email: userToAdd.email || undefined,
        markedForDeletion: false,
      };
      newUsers = [...users, newUser];
    }

    onUsersChange(newUsers);
    setSelectKey((prev) => prev + 1);
  };

  const handleToggleDeletion = () => {
    if (!userToToggle) return;

    const newUsers = users.map((u) =>
      u.id === userToToggle.id
        ? { ...u, markedForDeletion: !u.markedForDeletion }
        : u,
    );

    onUsersChange(newUsers);
    setUserToToggle(null);

    const action = userToToggle.markedForDeletion
      ? "восстановлен"
      : "помечен на удаление";
    toast({ title: `Пользователь ${action}` });
  };

  const excludeIds = useMemo(() => {
    return users.filter((u) => !u.markedForDeletion).map((u) => u.id);
  }, [users]);

  const initialIdsSet = useMemo(
    () => new Set(initialUserIds),
    [initialUserIds],
  );

  return (
    <div className="space-y-4">
      <div className="flex gap-2 items-end p-3 border rounded-md bg-muted/30">
        <div className="flex-1 space-y-1">
          <label className="text-sm font-medium">Добавить пользователя</label>
          <ReferenceSelect
            key={selectKey}
            fetchFn={async (params) => {
              const filtered = allUsers.filter((u) => {
                const isExcluded = excludeIds.includes(u.id);
                if (isExcluded) return false;
                if (params.search) {
                  const search = params.search.toLowerCase();
                  return (
                    u.name.toLowerCase().includes(search) ||
                    u.email?.toLowerCase().includes(search)
                  );
                }
                return true;
              });

              const items = filtered
                .slice(params.skip, params.skip + (params.limit || 50))
                .map((u) => ({
                  id: u.id,
                  name: u.name,
                  email: u.email,
                }));

              return {
                items,
                total: filtered.length,
              };
            }}
            queryKey={["users-for-role-select"]}
            value=""
            onValueChange={handleAddUser}
            placeholder="Выберите пользователя..."
            limit={50}
            heading="Доступные пользователи"
            columns={[{ column: "email", label: "Email" }]}
          />
        </div>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow className="h-10 hover:bg-transparent">
              <TableHead className="py-1">Имя</TableHead>
              <TableHead className="py-1">Email</TableHead>
              <TableHead className="py-1 w-16"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={3}
                  className="py-6 text-center text-muted-foreground text-sm"
                >
                  Пользователи не назначены. Выберите пользователя выше.
                </TableCell>
              </TableRow>
            ) : (
              users.map((user) => {
                const isMarkedForDeletion = user.markedForDeletion === true;
                const isNew = !initialIdsSet.has(user.id);

                return (
                  <TableRow
                    key={user.id}
                    className={`align-top ${
                      isMarkedForDeletion
                        ? "bg-red-50 dark:bg-red-900/10 opacity-60"
                        : isNew
                          ? "bg-green-50 dark:bg-green-900/10"
                          : ""
                    }`}
                  >
                    <TableCell className="py-1">
                      <div
                        className={`font-medium text-sm ${
                          isMarkedForDeletion
                            ? "line-through text-red-600 dark:text-red-400"
                            : ""
                        }`}
                      >
                        {user.name}
                        {isNew && !isMarkedForDeletion && (
                          <span className="ml-2 text-xs text-green-600 dark:text-green-400 font-normal">
                            (новый)
                          </span>
                        )}
                        {isMarkedForDeletion && (
                          <span className="ml-2 text-xs text-red-600 dark:text-red-400 font-normal">
                            (будет удалён)
                          </span>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="py-1 text-muted-foreground text-sm">
                      {user.email}
                    </TableCell>
                    <TableCell className="py-1 text-right">
                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className={`h-7 w-7 ${
                          isMarkedForDeletion
                            ? "text-green-600 hover:text-green-700 hover:bg-green-100 dark:hover:bg-green-900/20"
                            : "text-destructive hover:text-destructive hover:bg-destructive/10"
                        }`}
                        onClick={() => setUserToToggle(user)}
                        title={
                          isMarkedForDeletion
                            ? "Восстановить"
                            : "Пометить на удаление"
                        }
                      >
                        {isMarkedForDeletion ? (
                          <Undo2 className="h-4 w-4" />
                        ) : (
                          <Trash2 className="h-4 w-4" />
                        )}
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      <AlertDialog
        open={!!userToToggle}
        onOpenChange={(open) => !open && setUserToToggle(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {userToToggle?.markedForDeletion
                ? "Восстановить пользователя?"
                : "Пометить пользователя на удаление?"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {userToToggle?.markedForDeletion ? (
                <>
                  Пользователь <strong>{userToToggle?.name}</strong> будет
                  восстановлен.
                </>
              ) : (
                <>
                  Пользователь <strong>{userToToggle?.name}</strong> будет
                  помечен на удаление. Вы сможете восстановить его до сохранения.
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Отмена</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleToggleDeletion}
              className={
                userToToggle?.markedForDeletion
                  ? "bg-green-600 text-white hover:bg-green-700"
                  : "bg-destructive text-destructive-foreground hover:bg-destructive/90"
              }
            >
              {userToToggle?.markedForDeletion
                ? "Восстановить"
                : "Пометить на удаление"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};