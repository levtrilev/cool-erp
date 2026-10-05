import { useState } from "react";
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

// Orval хуки и типы
// ⚠️ Убедитесь, что вы перегенерировали Orval после добавления эндпоинта /save и поля permissions в RoleResponseSchema
import { useSaveRoleRolesSavePost } from "@/api/generated/roles/roles";
// import { useReadSectionsSectionsGet } from "@/api/generated/sections/sections";
// import { useUpdateRoleRolesRoleIdPut } from "@/api/generated/roles/roles";
import { useGetSectionsSectionsGet } from "@/api/generated/sections/sections";
import { useReadUsersUsersGet } from "@/api/generated/users/users";
import type {
  RoleResponseSchema,
  PermissionCreateSchema,
} from "@/api/generated/fastAPI.schemas";
import { useGetUserAuthUserGet } from "@/api/generated/authentication/authentication";

// Схема валидации
const roleSchema = z.object({
  name: z.string().min(1, "Название обязательно"),
  description: z.string().optional(),
});
type RoleFormData = z.infer<typeof roleSchema>;

// Заглушка для типов документов (в будущем можно получать с бэкенда через GET /doctypes)
// const AVAILABLE_DOCTYPES = [
//   { doctype: "invoices", doctype_name: "Счета-фактуры" },
//   { doctype: "orders", doctype_name: "Заказы" },
//   { doctype: "contracts", doctype_name: "Договоры" },
//   { doctype: "payments", doctype_name: "Платежи" },
// ];
const AVAILABLE_DOCTYPES = [] as { doctype: string; doctype_name: string }[];
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
  // ✅ Получаем данные текущего пользователя для tenant_id
  const { data: userData } = useGetUserAuthUserGet();
  const currentTenantId = userData?.data?.tenant_id;

  const isEdit = !!role; // Режим редактирования или создания

  // ✅ Инициализация формы с данными существующей роли
  const { control, handleSubmit } = useForm<RoleFormData>({
    resolver: zodResolver(roleSchema),
    defaultValues: {
      name: role?.name || "",
      description: role?.description || "",
    },
  });

  // ✅ Инициализация состояний на основе пропса `role`
  const [selectedSectionIds, setSelectedSectionIds] = useState<string[]>(
    role?.section_ids || [],
  );

  // В будущем здесь можно парсить role.user_ids, если добавим это поле в RoleResponseSchema
  const [selectedUserIds, setSelectedUserIds] = useState<string[]>([]);

  const [permissions, setPermissions] = useState<PermissionCreateSchema[]>(
    role?.permissions && role.permissions.length > 0
      ? role.permissions.map((p) => ({
          id: p.id, // ✅ Передаём id существующей записи
          doctype: p.doctype,
          doctype_name: p.doctype_name || "",
          role_id: p.role_id,
          tenant_id: p.tenant_id,
          full_access: p.full_access ?? false,
          author: p.author ?? false,
          reader: p.reader ?? false,
          editor: p.editor ?? false,
          can_delete: p.can_delete ?? false,
          access_by_tags: p.access_by_tags ?? false,
          or_tags: p.or_tags,
          and_tags: p.and_tags,
          no_tags: p.no_tags,
        }))
      : AVAILABLE_DOCTYPES.map((d) => ({
          doctype: d.doctype,
          doctype_name: d.doctype_name,
          // ✅ При создании role_id не передаём (undefined)
          // role_id: role?.id || "", // ✅ Пустой при создании
          tenant_id: role?.tenant_id || currentTenantId || "", // ✅ Берём из сессии
          full_access: false,
          author: false,
          reader: false,
          editor: false,
          can_delete: false,
        })),
  );

  // Загрузка данных для вкладок (справочники)
  const { data: sectionsData } = useGetSectionsSectionsGet({
    limit: 1000,
    skip: 0,
  });
  const { data: usersData } = useReadUsersUsersGet({ limit: 1000, skip: 0 });

  const sections = sectionsData?.data?.items ?? [];
  const users = usersData?.items ?? [];

  // ✅ Используем агрегирующий эндпоинт сохранения, а не стандартный PUT
  const saveMutation = useSaveRoleRolesSavePost();

  const onSubmit = async (data: RoleFormData) => {
    // ✅ Проверка tenant_id
    if (!currentTenantId) {
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: "Не удалось определить организацию",
      });
      return;
    }

    // ✅ Заполняем tenant_id для каждого разрешения
    // const permissionsWithIds = permissions.map((perm) => ({
    //   ...perm,
    //   role_id: role?.id || "", // ✅ Пустой при создании (бэкенд заполнит)
    //   tenant_id: currentTenantId,

    // }));

    const permissionsWithIds = permissions.map((perm) => {
      const item: PermissionCreateSchema = {
        ...perm,
        tenant_id: currentTenantId,
      };

      // ✅ Добавляем role_id только если он есть
      if (role?.id) {
        item.role_id = role.id;
      }

      return item;
    });

    const sectionNames = sections
      .filter((s) => selectedSectionIds.includes(s.id))
      .map((s) => s.name);

    const payload = {
      name: data.name,
      description: data.description,
      tenant_id: currentTenantId, // ✅ Всегда из сессии
      section_ids: selectedSectionIds,
      section_names: sectionNames,
      permissions: permissionsWithIds,
      user_ids: selectedUserIds,
    };

    // ✅ Формируем параметры мутации в зависимости от режима
    const mutationParams = isEdit
      ? { data: payload, params: { role_id: role.id } }
      : { data: payload }; // ✅ При создании role_id не передаём

    saveMutation.mutate(
      // ⚠️ Проверьте имя хука в сгенерированном Orval файле.
      // Обычно это { data: payload, roleId: role.id } или { data: payload, queryParams: { role_id: role.id } }
      mutationParams,
      {
        onSuccess: async (res) => {
          if (res.data) {
            const savedRole = res.data;

            // ✅ Правило №24: Строгий порядок
            // 1. Инвалидируем кэш
            queryClient.invalidateQueries({ queryKey: ["roles"] });
            // 2. Закрываем модалку
            onOpenChange(false);
            // 3. Вызываем callback родителя для умной навигации и подсветки
            await onRoleSaved(savedRole.id, savedRole.name);
          }
        },
        onError: () => {
          toast({
            variant: "destructive",
            title: "Ошибка",
            description: "Не удалось сохранить роль",
          });
        },
      },
    );
  };

  const togglePermission = (
    doctype: string,
    field: keyof PermissionCreateSchema,
  ) => {
    setPermissions((prev) =>
      prev.map((p) =>
        p.doctype === doctype ? { ...p, [field]: !p[field] } : p,
      ),
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      {/* <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto"> */}
      {/* <DialogContent className="w-[2100px] max-h-[90vh] overflow-y-auto"> */}
      <DialogContent
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
              <TabsTrigger value="permissions">Полномочия</TabsTrigger>
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
                              setSelectedSectionIds((prev) =>
                                checked
                                  ? [...prev, section.id]
                                  : prev.filter((id) => id !== section.id),
                              );
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
              <div className="rounded-md border max-h-[400px] overflow-y-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="h-10 hover:bg-transparent sticky top-0 bg-background z-10 shadow-sm">
                      <TableHead className="whitespace-nowrap w-[250px]">
                        Тип документа
                      </TableHead>
                      <TableHead className="text-center whitespace-nowrap w-[150px]">
                        Полный доступ
                      </TableHead>
                      <TableHead className="text-center whitespace-nowrap w-[150px]">
                        Редактор
                      </TableHead>
                      <TableHead className="text-center whitespace-nowrap w-[150px]">
                        Автор
                      </TableHead>
                      <TableHead className="text-center whitespace-nowrap w-[150px]">
                        Читатель
                      </TableHead>
                      <TableHead className="text-center whitespace-nowrap w-[150px]">
                        Удаление
                      </TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {permissions.map((perm) => (
                      <TableRow key={perm.doctype} className="py-1">
                        <TableCell className="py-1 font-medium whitespace-nowrap">
                          {perm.doctype_name || perm.doctype}
                        </TableCell>
                        <TableCell className="text-center py-1">
                          <Checkbox
                            checked={perm.full_access}
                            onCheckedChange={() =>
                              togglePermission(perm.doctype, "full_access")
                            }
                          />
                        </TableCell>
                        <TableCell className="text-center py-1">
                          <Checkbox
                            checked={perm.editor}
                            onCheckedChange={() =>
                              togglePermission(perm.doctype, "editor")
                            }
                          />
                        </TableCell>
                        <TableCell className="text-center py-1">
                          <Checkbox
                            checked={perm.author}
                            onCheckedChange={() =>
                              togglePermission(perm.doctype, "author")
                            }
                          />
                        </TableCell>
                        <TableCell className="text-center py-1">
                          <Checkbox
                            checked={perm.reader}
                            onCheckedChange={() =>
                              togglePermission(perm.doctype, "reader")
                            }
                          />
                        </TableCell>
                        <TableCell className="text-center py-1">
                          <Checkbox
                            checked={perm.can_delete}
                            onCheckedChange={() =>
                              togglePermission(perm.doctype, "can_delete")
                            }
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
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
                              setSelectedUserIds((prev) =>
                                checked
                                  ? [...prev, user.id]
                                  : prev.filter((id) => id !== user.id),
                              );
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
