import { useState, useMemo } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Loader2, CheckCircle2, PauseCircle } from "lucide-react";

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

import {
  createPermissionPermissionsPost,
  deletePermissionPermissionsPermissionIdDelete,
} from "@/api/generated/permissions/permissions";

import { getDoctypesDoctypesGet } from "@/api/generated/doctypes/doctypes";
import type { DoctypeResponseSchema } from "@/api/generated/fastAPI.schemas";
import type {
  RoleResponseSchema,
  PermissionResponseSchema,
} from "@/api/generated/fastAPI.schemas";

interface PermissionsTabProps {
  role: RoleResponseSchema;
}

export const PermissionsTab = ({ role }: PermissionsTabProps) => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [selectedDoctype, setSelectedDoctype] = useState<string>("");
  const [isAdding, setIsAdding] = useState(false);
  const [permissionToDelete, setPermissionToDelete] =
    useState<PermissionResponseSchema | null>(null);
  const [isRemoving, setIsRemoving] = useState(false);

  // ✅ Исправление 1: Стабильная зависимость для useMemo (зависим от role.permissions, а не от новой ссылки [])
  const existingDoctypes = useMemo(
    () => new Set((role.permissions || []).map((p) => p.doctype)),
    [role.permissions],
  );

  const permissions = role.permissions || [];

  const handleAddPermission = async () => {
    if (!selectedDoctype) {
      toast({ variant: "destructive", title: "Выберите тип документа" });
      return;
    }

    setIsAdding(true);
    try {
      // ✅ Исправление 2: Передаем объект напрямую, без обертки { data: ... }
      await createPermissionPermissionsPost({
        role_id: role.id,
        tenant_id: role.tenant_id,
        doctype: selectedDoctype,
        doctype_name: selectedDoctype,
        role_name: role.name,
        tenant_name: "",
        full_access: false,
        author: false,
        reader: true,
        editor: false,
        can_delete: false,
        access_by_tags: false,
      });

      await queryClient.invalidateQueries({ queryKey: ["roles"] });
      await queryClient.invalidateQueries({ queryKey: ["role", role.id] });

      setSelectedDoctype("");
      toast({ title: "Полномочие добавлено" });
    } catch (error: unknown) {
      // ✅ Исправление 3: Замена 'any' на 'unknown' с безопасным приведением типа
      const err = error as { response?: { data?: { detail?: string } } };
      toast({
        variant: "destructive",
        title: "Ошибка",
        description:
          err?.response?.data?.detail || "Не удалось добавить полномочие",
      });
    } finally {
      setIsAdding(false);
    }
  };

  const handleRemovePermission = async () => {
    if (!permissionToDelete) return;

    setIsRemoving(true);
    try {
      // ✅ Исправление 4: Передаем строку напрямую, а не объект { permission_id: ... }
      await deletePermissionPermissionsPermissionIdDelete(
        permissionToDelete.id,
      );

      await queryClient.invalidateQueries({ queryKey: ["roles"] });
      await queryClient.invalidateQueries({ queryKey: ["role", role.id] });

      setPermissionToDelete(null);
      toast({ title: "Полномочие удалено" });
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      toast({
        variant: "destructive",
        title: "Ошибка",
        description:
          err?.response?.data?.detail || "Не удалось удалить полномочие",
      });
    } finally {
      setIsRemoving(false);
    }
  };

  const renderFlag = (
    value: boolean | null | undefined,
    colorClass: string,
  ) => {
    return value ? (
      <CheckCircle2 className={`h-4 w-4 ${colorClass}`} />
    ) : (
      <PauseCircle className="h-4 w-4 text-gray-300 dark:text-gray-600" />
    );
  };

  return (
    <div className="space-y-4">
      {/* Блок добавления */}
      <div className="flex gap-2 items-end p-3 border rounded-md bg-muted/30">
        <div className="flex-1 space-y-1">
          <label className="text-sm font-medium">Добавить тип документа</label>
          <ReferenceSelect
            fetchFn={async (params) => {
              const response = await getDoctypesDoctypesGet({
                ...params,
                available_for_tenant_id: role.tenant_id,
              });

              // ✅ Явная типизация item. Перезапись id строкой doctype теперь типобезопасна.
              const items = (response?.data?.items ?? []).map(
                (item: DoctypeResponseSchema) => ({
                  ...item,
                  id: item.doctype, // Правило №27: Строка вместо UUID
                  name: item.doctype_name || item.doctype, // ✅ Добавлено для удовлетворения типа ReferenceItem
                }),
              );

              return {
                items,
                total: response?.data?.total ?? 0,
              };
            }}
            queryKey={["doctypes-for-role", role.tenant_id]}
            value={selectedDoctype}
            onValueChange={setSelectedDoctype}
            placeholder="Выберите тип документа..."
            limit={50}
            heading="Доступные типы документов"
            columns={[
              { column: "doctype_name", label: "Название" },
              { column: "description", label: "Описание" },
            ]}
          />
        </div>
        <Button
          onClick={handleAddPermission}
          disabled={
            !selectedDoctype ||
            isAdding ||
            existingDoctypes.has(selectedDoctype)
          }
          className="h-10"
        >
          {isAdding ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Plus className="h-4 w-4 mr-1" />
          )}
          Добавить
        </Button>
      </div>

      {/* Подсказка о дубликате */}
      {selectedDoctype && existingDoctypes.has(selectedDoctype) && (
        <p className="text-xs text-amber-600 dark:text-amber-400">
          ⚠ Полномочие для этого типа документа уже существует
        </p>
      )}

      {/* Правило №11: Компактные таблицы */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="py-1">Тип документа</TableHead>
              <TableHead className="py-1 text-center w-20">Полный</TableHead>
              <TableHead className="py-1 text-center w-20">Автор</TableHead>
              <TableHead className="py-1 text-center w-20">Чтение</TableHead>
              <TableHead className="py-1 text-center w-20">Редактор</TableHead>
              <TableHead className="py-1 text-center w-20">Удаление</TableHead>
              <TableHead className="py-1 w-16"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {permissions.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={7}
                  className="py-6 text-center text-muted-foreground text-sm"
                >
                  Полномочия не добавлены. Выберите тип документа выше.
                </TableCell>
              </TableRow>
            ) : (
              permissions.map((perm) => (
                <TableRow key={perm.id} className="align-top">
                  <TableCell className="py-1">
                    <div className="font-medium text-sm">
                      {perm.doctype_name || perm.doctype}
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Код: {perm.doctype}
                    </div>
                  </TableCell>
                  <TableCell className="py-1 text-center">
                    {renderFlag(perm.full_access, "text-purple-600")}
                  </TableCell>
                  <TableCell className="py-1 text-center">
                    {renderFlag(perm.author, "text-blue-600")}
                  </TableCell>
                  <TableCell className="py-1 text-center">
                    {renderFlag(perm.reader, "text-green-600")}
                  </TableCell>
                  <TableCell className="py-1 text-center">
                    {renderFlag(perm.editor, "text-yellow-600")}
                  </TableCell>
                  <TableCell className="py-1 text-center">
                    {renderFlag(perm.can_delete, "text-red-600")}
                  </TableCell>
                  <TableCell className="py-1 text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 text-destructive hover:text-destructive hover:bg-destructive/10"
                      onClick={() => setPermissionToDelete(perm)}
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

      {/* Правило №16: Удаление через AlertDialog */}
      <AlertDialog
        open={!!permissionToDelete}
        onOpenChange={(open) => !open && setPermissionToDelete(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Удалить полномочие?</AlertDialogTitle>
            <AlertDialogDescription>
              Роль потеряет доступ к типу документа{" "}
              <strong>
                {permissionToDelete?.doctype_name ||
                  permissionToDelete?.doctype}
              </strong>
              . Это действие нельзя отменить.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Отмена</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRemovePermission}
              disabled={isRemoving}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isRemoving ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                "Удалить"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
