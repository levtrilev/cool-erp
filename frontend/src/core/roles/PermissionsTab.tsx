import { useState, useMemo } from "react";
import { Trash2, Undo2, CheckCircle2, PauseCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
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
import { getDoctypesDoctypesGet } from "@/api/generated/doctypes/doctypes";
import type { DoctypeResponseSchema } from "@/api/generated/fastAPI.schemas";

/**
 * Черновик permission (edit-состояние).
 * id отсутствует у новых записей (будет создан на бэкенде).
 * id присутствует у существующих записей (для обновления).
 * markedForDeletion — флаг для мягкого удаления (визуальная пометка).
 */
export interface PermissionDraft {
  id?: string;
  doctype: string;
  doctype_name?: string | null;
  role_name?: string | null;
  tenant_name?: string | null;
  full_access: boolean;
  author: boolean;
  reader: boolean;
  editor: boolean;
  can_delete: boolean;
  access_by_tags: boolean;
  markedForDeletion?: boolean;
}

interface PermissionsTabProps {
  permissions: PermissionDraft[];
  onPermissionsChange: (permissions: PermissionDraft[]) => void;
  tenantId: string;
  roleName: string;
}

export const PermissionsTab = ({
  permissions,
  onPermissionsChange,
  tenantId,
  roleName,
}: PermissionsTabProps) => {
  const { toast } = useToast();
  // const [selectedDoctype, setSelectedDoctype] = useState<string>("");
  const [permissionToToggle, setPermissionToToggle] =
    useState<PermissionDraft | null>(null);

  // ✅ Множество существующих doctype (исключаем помеченные на удаление)
  const existingDoctypes = useMemo(
    () =>
      new Set(
        permissions.filter((p) => !p.markedForDeletion).map((p) => p.doctype),
      ),
    [permissions],
  );

  // const handleAddPermission = (doctype: string, doctype_name: string): void => {
  const handleAddPermission = (doctype: string): void => {
    if (!doctype) return;

    // ✅ Защита от дубликата (вместо блокировки кнопки)
    if (existingDoctypes.has(doctype)) {
      toast({
        variant: "destructive",
        title: "Полномочие уже существует",
        description: `Тип документа "${doctype}" уже добавлен в черновик.`,
      });
      return;
    }

    const newPermission: PermissionDraft = {
      doctype,
      doctype_name: doctype,
      role_name: roleName,
      tenant_name: "",
      full_access: false,
      author: false,
      reader: true,
      editor: false,
      can_delete: false,
      access_by_tags: false,
      markedForDeletion: false,
    };

    onPermissionsChange([...permissions, newPermission]);
    // setSelectedDoctype("");
    toast({ title: "Полномочие добавлено в черновик" });
  };

  // ✅ Мягкое удаление/восстановление
  const handleToggleDeletion = () => {
    if (!permissionToToggle) return;

    const updated = permissions.map((p) => {
      if (p.doctype === permissionToToggle.doctype) {
        return {
          ...p,
          markedForDeletion: !p.markedForDeletion,
        };
      }
      return p;
    });

    onPermissionsChange(updated);
    setPermissionToToggle(null);

    const action = permissionToToggle.markedForDeletion
      ? "восстановлено"
      : "помечено на удаление";
    toast({ title: `Полномочие ${action}` });
  };

  const handleToggleFlag = (
    index: number,
    flag: keyof Pick<
      PermissionDraft,
      "full_access" | "author" | "reader" | "editor" | "can_delete"
    >,
  ) => {
    const updated = [...permissions];
    updated[index] = {
      ...updated[index],
      [flag]: !updated[index][flag],
    };
    onPermissionsChange(updated);
  };

  const renderFlagIcon = (
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
                available_for_tenant_id: tenantId,
              });

              const items = (response?.data?.items ?? []).map(
                (item: DoctypeResponseSchema) => ({
                  ...item,
                  id: item.doctype,
                  name: item.doctype_name || item.doctype,
                }),
              );

              return { items, total: response?.data?.total ?? 0 };
            }}
            queryKey={["doctypes-for-role", tenantId]}
            // ✅ value всегда пустое — ReferenceSelect работает как триггер
            value=""
            // ✅ Выбор сразу добавляет полномочие (аналогично UsersTab)
            onValueChange={handleAddPermission}
            placeholder="Выберите тип документа..."
            limit={50}
            heading="Доступные типы документов"
            columns={[
              { column: "doctype_name", label: "Название" },
              { column: "description", label: "Описание" },
            ]}
          />
        </div>
        {/* <Button
          type="button"
          onClick={handleAddPermission}
          disabled={!selectedDoctype || existingDoctypes.has(selectedDoctype)}
          className="h-10"
        >
          <Plus className="h-4 w-4 mr-1" />
          Добавить
        </Button> */}
      </div>

      {/* Подсказка о дубликате */}
      {/* {selectedDoctype && existingDoctypes.has(selectedDoctype) && (
        <p className="text-xs text-amber-600 dark:text-amber-400">
          ⚠ Полномочие для этого типа документа уже существует в черновике
        </p>
      )} */}

      {/* Таблица полномочий */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow className="h-10 hover:bg-transparent">
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
              permissions.map((perm, index) => {
                const isMarkedForDeletion = perm.markedForDeletion === true;
                const isNew = !perm.id;

                return (
                  <TableRow
                    key={perm.id || perm.doctype}
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
                        {perm.doctype_name || perm.doctype}
                        {isNew && !isMarkedForDeletion && (
                          <span className="ml-2 text-xs text-green-600 dark:text-green-400 font-normal">
                            (новый)
                          </span>
                        )}
                        {isMarkedForDeletion && (
                          <span className="ml-2 text-xs text-red-600 dark:text-red-400 font-normal">
                            (будет удалено)
                          </span>
                        )}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Код: {perm.doctype}
                      </div>
                    </TableCell>
                    <TableCell className="py-1 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <Checkbox
                          checked={perm.full_access || false}
                          onCheckedChange={() =>
                            handleToggleFlag(index, "full_access")
                          }
                          disabled={isMarkedForDeletion}
                        />
                        {renderFlagIcon(perm.full_access, "text-purple-600")}
                      </div>
                    </TableCell>
                    <TableCell className="py-1 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <Checkbox
                          checked={perm.author || false}
                          onCheckedChange={() =>
                            handleToggleFlag(index, "author")
                          }
                          disabled={isMarkedForDeletion}
                        />
                        {renderFlagIcon(perm.author, "text-blue-600")}
                      </div>
                    </TableCell>
                    <TableCell className="py-1 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <Checkbox
                          checked={perm.reader || false}
                          onCheckedChange={() =>
                            handleToggleFlag(index, "reader")
                          }
                          disabled={isMarkedForDeletion}
                        />
                        {renderFlagIcon(perm.reader, "text-green-600")}
                      </div>
                    </TableCell>
                    <TableCell className="py-1 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <Checkbox
                          checked={perm.editor || false}
                          onCheckedChange={() =>
                            handleToggleFlag(index, "editor")
                          }
                          disabled={isMarkedForDeletion}
                        />
                        {renderFlagIcon(perm.editor, "text-yellow-600")}
                      </div>
                    </TableCell>
                    <TableCell className="py-1 text-center">
                      <div className="flex items-center justify-center gap-1">
                        <Checkbox
                          checked={perm.can_delete || false}
                          onCheckedChange={() =>
                            handleToggleFlag(index, "can_delete")
                          }
                          disabled={isMarkedForDeletion}
                        />
                        {renderFlagIcon(perm.can_delete, "text-red-600")}
                      </div>
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
                        onClick={() => setPermissionToToggle(perm)}
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

      {/* Диалог подтверждения удаления/восстановления */}
      <AlertDialog
        open={!!permissionToToggle}
        onOpenChange={(open) => !open && setPermissionToToggle(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {permissionToToggle?.markedForDeletion
                ? "Восстановить полномочие?"
                : "Пометить полномочие на удаление?"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {permissionToToggle?.markedForDeletion ? (
                <>
                  Полномочие для типа документа{" "}
                  <strong>
                    {permissionToToggle?.doctype_name ||
                      permissionToToggle?.doctype}
                  </strong>{" "}
                  будет восстановлено.
                </>
              ) : (
                <>
                  Полномочие для типа документа{" "}
                  <strong>
                    {permissionToToggle?.doctype_name ||
                      permissionToToggle?.doctype}
                  </strong>{" "}
                  будет помечено на удаление. Вы сможете восстановить его до
                  нажатия кнопки "Сохранить".
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Отмена</AlertDialogCancel>
            <AlertDialogAction
              type="button"
              onClick={handleToggleDeletion}
              className={
                permissionToToggle?.markedForDeletion
                  ? "bg-green-600 text-white hover:bg-green-700"
                  : "bg-destructive text-destructive-foreground hover:bg-destructive/90"
              }
            >
              {permissionToToggle?.markedForDeletion
                ? "Восстановить"
                : "Пометить на удаление"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
