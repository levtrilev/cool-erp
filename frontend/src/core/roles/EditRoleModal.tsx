import { useState, useMemo } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2, Check } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useSaveRoleRolesSavePost } from "@/api/generated/roles/roles";
import { useGetSectionsSectionsGet } from "@/api/generated/sections/sections";
import { useReadUsersUsersGet } from "@/api/generated/users/users";
import { useGetUserAuthUserGet } from "@/api/generated/authentication/authentication";
import type { RoleResponseSchema } from "@/api/generated/fastAPI.schemas";
import { PermissionsTab, type PermissionDraft } from "./PermissionsTab";

// ✅ Правило №20: Константа для сброса формы
const CREATE_DEFAULTS: RoleFormData = {
  name: "",
  description: "",
};

const roleSchema = z.object({
  name: z.string().min(1, "Название обязательно"),
  description: z.string().optional(),
});

type RoleFormData = z.infer<typeof roleSchema>;

interface EditRoleModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  role?: RoleResponseSchema | null;
  onRoleSaved: (id: string, name: string) => void;
}

export function EditRoleModal({
  open,
  onOpenChange,
  role,
  onRoleSaved,
}: EditRoleModalProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { data: userData } = useGetUserAuthUserGet();
  const currentTenantId = userData?.data?.tenant_id;
  const isEdit = !!role;

  // ✅ Динамические defaultValues для useForm.
  // Благодаря паттерну с `key` ниже, useForm пересоздается с правильными значениями.
  const formDefaultValues: RoleFormData = isEdit
    ? {
        name: role.name || "",
        description: role.description || "",
      }
    : CREATE_DEFAULTS;

  const { control, handleSubmit } = useForm<RoleFormData>({
    resolver: zodResolver(roleSchema),
    defaultValues: formDefaultValues,
  });

  // ✅ Инициализация состояний напрямую.
  // При смене `key` компонент монтируется заново, и эти значения становятся актуальными.
  const [selectedSectionIds, setSelectedSectionIds] = useState<string[]>(
    role?.section_ids || [],
  );
  const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);

  // ✅ Преобразование null в undefined для строгой типизации (TypeScript)
  const initialPerms: PermissionDraft[] = role?.permissions
    ? role.permissions.map((p) => ({
        id: p.id,
        doctype: p.doctype,
        doctype_name: p.doctype_name ?? undefined,
        role_name: p.role_name ?? undefined,
        tenant_name: p.tenant_name ?? undefined,
        full_access: p.full_access ?? false,
        author: p.author ?? false,
        reader: p.reader ?? false,
        editor: p.editor ?? false,
        can_delete: p.can_delete ?? false,
        access_by_tags: p.access_by_tags ?? false,
      }))
    : [];

  const [permissions, setPermissions] =
    useState<PermissionDraft[]>(initialPerms);
  const [initialPermissionsSnapshot] = useState<string>(
    JSON.stringify(initialPerms),
  );

  // ✅ Вычисляем наличие несохранённых изменений
  const hasUnsavedChanges = useMemo(() => {
    return JSON.stringify(permissions) !== initialPermissionsSnapshot;
  }, [permissions, initialPermissionsSnapshot]);

  // Загрузка данных для вкладок
  const { data: sectionsData } = useGetSectionsSectionsGet({
    limit: 1000,
    skip: 0,
  });
  const { data: usersData } = useReadUsersUsersGet({ limit: 1000, skip: 0 });

  const sections = sectionsData?.data?.items ?? [];
  const users = usersData?.items ?? [];

  const saveMutation = useSaveRoleRolesSavePost();

  const onSubmit = async (data: RoleFormData) => {
    if (!currentTenantId) {
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: "Не удалось определить организацию",
      });
      return;
    }

    // ✅ Формируем payload, включая permissions из локального edit-состояния
    // const payload = {
    //   name: data.name,
    //   description: data.description || "",
    //   tenant_id: currentTenantId,
    //   section_ids: selectedSectionIds,
    //   section_names: sections
    //     .filter((s) => selectedSectionIds.includes(s.id))
    //     .map((s) => s.name),
    //   permissions: permissions.map((p) => ({
    //     doctype: p.doctype,
    //     doctype_name: p.doctype_name || p.doctype,
    //     role_name: p.role_name || data.name,
    //     tenant_name: "",
    //     tenant_id: currentTenantId, // ✅ Обязательно для PermissionCreateSchema
    //     full_access: p.full_access,
    //     author: p.author,
    //     reader: p.reader,
    //     editor: p.editor,
    //     can_delete: p.can_delete,
    //     access_by_tags: p.access_by_tags,
    //     ...(p.id ? { id: p.id } : {}), // ✅ ID только для существующих записей
    //   })),
    //   user_ids: selectedUserIds,
    // };
    // ✅ ФИЛЬТРАЦИЯ: Исключаем permissions, помеченные на удаление
    const permissionsToSend = permissions.filter((p) => !p.markedForDeletion);

    const payload = {
      name: data.name,
      description: data.description || "",
      tenant_id: currentTenantId,
      section_ids: selectedSectionIds,
      section_names: sections
        .filter((s) => selectedSectionIds.includes(s.id))
        .map((s) => s.name),
      // ✅ Отправляем только НЕ помеченные на удаление
      permissions: permissionsToSend.map((p) => ({
        doctype: p.doctype,
        doctype_name: p.doctype_name || p.doctype,
        role_name: p.role_name || data.name,
        tenant_name: "",
        tenant_id: currentTenantId,
        full_access: p.full_access,
        author: p.author,
        reader: p.reader,
        editor: p.editor,
        can_delete: p.can_delete,
        access_by_tags: p.access_by_tags,
        ...(p.id ? { id: p.id } : {}),
      })),
      user_ids: selectedUserIds,
    };
    const mutationParams =
      isEdit && role?.id
        ? { data: payload, params: { role_id: role.id } }
        : { data: payload };

    saveMutation.mutate(mutationParams, {
      onSuccess: async (res) => {
        if (res.data) {
          const savedRole = res.data;

          // ✅ Правило №24: Строгий порядок действий
          await queryClient.invalidateQueries({ queryKey: ["roles"] });
          if (isEdit && role?.id) {
            await queryClient.invalidateQueries({
              queryKey: ["role", role.id],
            });
          }

          onOpenChange(false);
          await onRoleSaved(savedRole.id, savedRole.name);
          toast({ title: "Роль сохранена" });
        }
      },
      onError: (error: unknown) => {
        // ✅ Правило №36: Безопасная обработка ошибок
        const err = error as { response?: { data?: { detail?: string } } };
        toast({
          variant: "destructive",
          title: "Ошибка сохранения",
          description:
            err?.response?.data?.detail || "Не удалось сохранить роль",
        });
      },
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {/* ✅ Правило №37: Паттерн с `key`. 
            При закрытии (open=false) или смене роли компонент полностью пересоздается.
            Это автоматически сбрасывает все useState в исходные значения без useEffect. */}
      <DialogContent
        key={open ? (isEdit ? `edit-${role.id}` : "create") : "closed"}
        className="max-h-[90vh] items-start pt-8"
        style={{
          width: "800px",
          maxWidth: "800px",
          minHeight: "600px",
          height: "auto",
        }}
      >
        <DialogHeader>
          <DialogTitle>
            {isEdit
              ? `Редактирование роли: ${role.name}`
              : "Создание новой роли"}
          </DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Tabs defaultValue="main" className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="main">Основное</TabsTrigger>
              <TabsTrigger value="sections">Разделы</TabsTrigger>
              <TabsTrigger value="permissions" className="relative">
                Полномочия
                {hasUnsavedChanges && (
                  <span className="absolute -top-1 -right-1 text-amber-500 text-xl font-bold leading-none">
                    *
                  </span>
                )}
              </TabsTrigger>
              <TabsTrigger value="users">Пользователи</TabsTrigger>
            </TabsList>

            {/* Вкладка 1: Основное */}
            <TabsContent value="main" className="space-y-4 mt-0 min-h-[400px]">
              <div className="space-y-2">
                <label className="text-sm font-medium">Название роли</label>
                <Controller
                  name="name"
                  control={control}
                  render={({ field, fieldState }) => (
                    <>
                      <Input {...field} placeholder="Например: Бухгалтер" />
                      {fieldState.error && (
                        <p className="text-xs text-destructive">
                          {fieldState.error.message}
                        </p>
                      )}
                    </>
                  )}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium">Описание</label>
                <Controller
                  name="description"
                  control={control}
                  render={({ field }) => (
                    <Textarea
                      {...field}
                      placeholder="Описание роли..."
                      rows={3}
                    />
                  )}
                />
              </div>
            </TabsContent>

            {/* Вкладка 2: Разделы */}
            <TabsContent
              value="sections"
              className="space-y-4 mt-0 min-h-[400px]"
            >
              <div className="rounded-md border max-h-[400px] overflow-y-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="h-10 hover:bg-transparent sticky top-0 bg-background z-10 shadow-sm">
                      <TableHead className="w-[50px]"></TableHead>
                      <TableHead>Название раздела</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sections.map((section) => (
                      <TableRow key={section.id} className="py-1">
                        <TableCell>
                          <Checkbox
                            checked={selectedSectionIds.includes(section.id)}
                            onCheckedChange={(checked) => {
                              const current = selectedSectionIds;
                              const next = checked
                                ? [...current, section.id]
                                : current.filter((id) => id !== section.id);
                              setSelectedSectionIds(next);
                            }}
                          />
                        </TableCell>
                        <TableCell className="py-1 font-medium">
                          {section.name}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>

            {/* Вкладка 3: Полномочия */}
            <TabsContent
              value="permissions"
              className="space-y-4 mt-0 min-h-[400px]"
            >
              <PermissionsTab
                permissions={permissions}
                onPermissionsChange={setPermissions}
                tenantId={currentTenantId || ""}
                roleName={role?.name || ""}
              />
            </TabsContent>

            {/* Вкладка 4: Пользователи */}
            <TabsContent value="users" className="space-y-4 mt-0 min-h-[400px]">
              <div className="rounded-md border max-h-[400px] overflow-y-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="h-10 hover:bg-transparent sticky top-0 bg-background z-10 shadow-sm">
                      <TableHead className="w-[50px]"></TableHead>
                      <TableHead>Имя</TableHead>
                      <TableHead>Email</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {users.map((user) => (
                      <TableRow key={user.id} className="py-1">
                        <TableCell>
                          <Checkbox
                            checked={selectedUserIds.includes(user.id)}
                            onCheckedChange={(checked) => {
                              const current = selectedUserIds;
                              const next = checked
                                ? [...current, user.id]
                                : current.filter((id) => id !== user.id);
                              setSelectedUserIds(next);
                            }}
                          />
                        </TableCell>
                        <TableCell className="py-1 font-medium">
                          {user.name}
                        </TableCell>
                        <TableCell className="py-1 text-muted-foreground">
                          {user.email}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </TabsContent>
          </Tabs>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Отмена
            </Button>
            <Button type="submit" disabled={saveMutation.isPending}>
              {saveMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              <Check className="mr-2 h-4 w-4" />
              Сохранить
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
