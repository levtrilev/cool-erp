import { useState } from "react";
// import { useQuery } from "@tanstack/react-query";
import { Loader2, Tag, Search } from "lucide-react";
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
import { useToast } from "@/components/ui/use-toast";
import { EditUserModal } from "@/core/users/EditUserModal";
import { TagWithUsersResponseSchema } from "@/api/generated/fastAPI.schemas";
import { useGetTagsWithUsersUsersTagsGet } from "@/api/generated/users/users";
import type { UserResponseSchema } from "@/api/generated/fastAPI.schemas";
import type { TagUserResponseSchema } from "@/api/generated/fastAPI.schemas";

export const TagsPage = () => {
  const { toast } = useToast();
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [editUser, setEditUser] = useState<TagUserResponseSchema | null>(null);
  const [editModalOpen, setEditModalOpen] = useState(false);

  const { data, isLoading, isError, refetch } = useGetTagsWithUsersUsersTagsGet(
    {
      query: {
        queryKey: ["tags-with-users"],
      },
    },
  );
  const tags: TagWithUsersResponseSchema[] = data?.data ?? [];

  const filteredTags = tags.filter((t) => {
    if (!search) return true;
    const searchLower = search.toLowerCase();
    return (
      t.tag.toLowerCase().includes(searchLower) ||
      t.users.some(
        (u) =>
          u.name.toLowerCase().includes(searchLower) ||
          u.email.toLowerCase().includes(searchLower),
      )
    );
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput);
  };

  const handleUserSaved = async () => {
    await refetch();
    toast({ title: "Пользователь обновлён" });
    setEditModalOpen(false);
    setEditUser(null);
  };

  return (
    <div className="container mx-auto px-4 py-3">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 mb-2">
        <div>
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Tag className="h-5 w-5 text-primary" />
            Теги доступа
          </h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Всего тегов: {tags.length} · Пользователей с тегами:{" "}
            {new Set(tags.flatMap((t) => t.users.map((u) => u.id))).size}
          </p>
        </div>

        <form onSubmit={handleSearch} className="flex gap-2 w-full md:w-auto">
          <Input
            placeholder="Поиск по тегу или пользователю..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="w-full md:w-64"
          />
          <Button type="submit" variant="secondary">
            <Search className="h-4 w-4 mr-2" /> Найти
          </Button>
        </form>
      </div>

      <div className="rounded-md border bg-card">
        <Table className="table-fixed w-full">
          <TableHeader>
            <TableRow className="h-10 hover:bg-transparent">
              <TableHead style={{ width: "30%" }}>Тег</TableHead>
              <TableHead>Пользователи (кликните для редактирования)</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableRow>
                <TableCell colSpan={2} className="text-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin mx-auto" />
                </TableCell>
              </TableRow>
            ) : isError ? (
              <TableRow>
                <TableCell
                  colSpan={2}
                  className="text-center text-destructive py-8"
                >
                  Ошибка загрузки
                </TableCell>
              </TableRow>
            ) : filteredTags.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={2}
                  className="text-center text-muted-foreground py-8"
                >
                  {search ? "Теги не найдены" : "Нет тегов в системе"}
                </TableCell>
              </TableRow>
            ) : (
              filteredTags.map((tagItem) => (
                <TableRow key={tagItem.tag} className="align-top">
                  <TableCell className="py-2 font-mono text-sm">
                    <Badge variant="outline" className="font-mono">
                      {tagItem.tag}
                    </Badge>
                  </TableCell>
                  <TableCell className="py-2">
                    <div className="flex flex-wrap gap-1.5">
                      {tagItem.users.length > 0 ? (
                        tagItem.users.map((user) => (
                          <button
                            key={user.id}
                            type="button"
                            onClick={() => {
                              setEditUser(user);
                              setEditModalOpen(true);
                            }}
                            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-secondary text-secondary-foreground hover:bg-secondary/80 transition-colors cursor-pointer"
                            title={`${user.name} (${user.email}) · ${user.tenant_name || ""}`}
                          >
                            <span className="font-medium">{user.name}</span>
                            {user.tenant_name && (
                              <span className="text-muted-foreground text-[10px]">
                                · {user.tenant_name}
                              </span>
                            )}
                          </button>
                        ))
                      ) : (
                        <span className="text-xs text-muted-foreground">
                          Нет пользователей
                        </span>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {editUser && (
        <EditUserModal
          key={editUser.id}
          open={editModalOpen}
          onOpenChange={(open) => {
            setEditModalOpen(open);
            if (!open) setEditUser(null);
          }}
          user={editUser as unknown as UserResponseSchema}
          onUserUpdated={handleUserSaved}
        />
      )}
    </div>
  );
};
