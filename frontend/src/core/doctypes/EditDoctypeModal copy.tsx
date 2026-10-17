import { useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { CheckCircle2, PauseCircle, Loader2 } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { useToast } from "@/components/ui/use-toast";

import {
  useCreateDoctypeDoctypesPost,
  useUpdateDoctypeDoctypesDoctypeIdPut,
} from "@/api/generated/doctypes/doctypes";
import { getDomainsDomainsGet } from "@/api/generated/domains/domains";
import type {
  DoctypeResponseSchema,
  DoctypeCreateSchema,
  DoctypeUpdateSchema,
} from "@/api/generated/fastAPI.schemas";

import { ReferenceSelect } from "@/lib/reusable/ReferenceSelect";
import { TenantMultiSelect } from "@/core/tenants/TenantMultiSelect";

const doctypeSchema = z.object({
  domain_id: z.string().uuid("Выберите домен"),
  doctype: z.string().min(2, "Минимум 2 символа (например, invoices)"),
  doctype_name: z.string().min(2, "Минимум 2 символа"),
  description: z.string().optional(),
  is_active: z.boolean().optional(),
  tenant_ids: z.array(z.string().uuid()).optional(),
});

type DoctypeFormData = z.infer<typeof doctypeSchema>;

// ✅ Правило №20: Константа для сброса формы
const CREATE_DEFAULTS: DoctypeFormData = {
  domain_id: "",
  doctype: "",
  doctype_name: "",
  description: "",
  is_active: true,
  tenant_ids: [],
};

interface EditDoctypeModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData: DoctypeResponseSchema | null;
  onSaved: (id: string) => Promise<void>;
}

export const EditDoctypeModal = ({
  open,
  onOpenChange,
  initialData,
  onSaved,
}: EditDoctypeModalProps) => {
  const queryClient = useQueryClient();

  // ✅ Принудительная установка домена в кэш React Query при открытии модалки
  // Это гарантирует, что ReferenceSelect мгновенно отобразит label
  useEffect(() => {
    if (open && initialData?.domain_id && initialData?.domain_name) {
      // ✅ Явная типизация данных кэша
      const currentData = queryClient.getQueryData(["domains"]) as
        | {
            items?: Array<{ id: string; name?: string; description?: string }>;
            total?: number;
          }
        | undefined;

      if (currentData && Array.isArray(currentData.items)) {
        const exists = currentData.items.some(
          (item) => item.id === initialData.domain_id,
        );

        if (!exists) {
          queryClient.setQueryData(["domains"], {
            ...currentData,
            items: [
              {
                id: initialData.domain_id,
                name: initialData.domain_name,
                description: "",
              },
              ...currentData.items,
            ],
          });
        }
      } else {
        // Если кэш пустой, создаём его с нашим доменом
        queryClient.setQueryData(["domains"], {
          items: [
            {
              id: initialData.domain_id,
              name: initialData.domain_name,
              description: "",
            },
          ],
          total: 1,
        });
      }
    }
  }, [open, initialData, queryClient]);

  const { toast } = useToast();

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<DoctypeFormData>({
    resolver: zodResolver(doctypeSchema),
    defaultValues: CREATE_DEFAULTS,
  });

  const createMutation = useCreateDoctypeDoctypesPost();
  const updateMutation = useUpdateDoctypeDoctypesDoctypeIdPut();

  // ✅ Синхронизация формы при открытии модалки или смене initialData
  useEffect(() => {
    if (open) {
      if (initialData) {
        reset({
          domain_id: initialData.domain_id,
          doctype: initialData.doctype,
          doctype_name: initialData.doctype_name,
          description: initialData.description || "",
          is_active: initialData.is_active ?? true,
          tenant_ids: initialData.tenant_ids ?? [],
        });
      } else {
        reset(CREATE_DEFAULTS);
      }
    }
  }, [open, initialData, reset]);

  const onSubmit = async (formData: DoctypeFormData) => {
    try {
      if (initialData) {
        // Режим редактирования
        await updateMutation.mutateAsync({
          doctypeId: initialData.id,
          data: formData as DoctypeUpdateSchema,
        });
        // ✅ Правило №24: invalidateQueries ДО закрытия модалки
        await queryClient.invalidateQueries({ queryKey: ["doctypes"] });
        onOpenChange(false);
        await onSaved(initialData.id);
      } else {
        // Режим создания
        const res = await createMutation.mutateAsync({
          data: formData as DoctypeCreateSchema,
        });
        await queryClient.invalidateQueries({ queryKey: ["doctypes"] });
        onOpenChange(false);
        if (res.data?.id) {
          await onSaved(res.data.id);
        }
      }
      // ✅ Правило №20: Сброс формы после успешного сохранения
      reset(CREATE_DEFAULTS);
    } catch (error: unknown) {
      // ✅ Безопасное извлечение ошибки (без any)
      const err = error as { response?: { data?: { detail?: string } } };
      toast({
        variant: "destructive",
        title: "Ошибка",
        description:
          err?.response?.data?.detail || "Не удалось сохранить тип документа",
      });
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      reset(CREATE_DEFAULTS); // ✅ Правило №20: Сброс при закрытии
    }
    onOpenChange(newOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {initialData ? "Редактирование" : "Создание"} типа документа
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Код (системное имя)</label>
              <Input
                {...control.register("doctype")}
                disabled={!!initialData}
                placeholder="например, invoices"
              />
              {errors.doctype && (
                <p className="text-xs text-destructive">
                  {errors.doctype.message}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Название</label>
              <Input
                {...control.register("doctype_name")}
                placeholder="например, Счета-фактуры"
              />
              {errors.doctype_name && (
                <p className="text-xs text-destructive">
                  {errors.doctype_name.message}
                </p>
              )}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4 items-end">
            <div className="space-y-2">
              <label className="text-sm font-medium">Домен</label>
              <Controller
                name="domain_id"
                control={control}
                render={({ field }) => (
                  <ReferenceSelect
                    fetchFn={async (params) => {
                      const response = await getDomainsDomainsGet(params);
                      return {
                        items: response?.data?.items ?? [],
                        total: response?.data?.total ?? 0,
                      };
                    }}
                    queryKey={["domains"]}
                    value={field.value}
                    onValueChange={field.onChange}
                    placeholder="Выберите домен..."
                    // ✅ ДОБАВЛЕНО: Явное указание label для мгновенного отображения при открытии
                    selectedLabel={
                      initialData?.domain_name ?? "Выберите домен..."
                    }
                    limit={50}
                    heading="Домены"
                    columns={[{ column: "description", label: "Описание" }]}
                  />
                )}
              />
              {errors.domain_id && (
                <p className="text-xs text-destructive">
                  {errors.domain_id.message}
                </p>
              )}
            </div>

            {/* ✅ Правило №34: Switch в формах */}
            <div className="mt-0">
              <Controller
                name="is_active"
                control={control}
                render={({ field }) => (
                  <>
                    <Switch
                      id="is_active"
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                    <Label
                      htmlFor="is_active"
                      className={`flex items-center gap-2 cursor-pointer font-medium transition-colors ${
                        field.value
                          ? "text-green-600 dark:text-green-400"
                          : "text-red-500 dark:text-red-400"
                      }`}
                    >
                      {field.value ? (
                        <>
                          <CheckCircle2 className="h-4 w-4" />
                          Активен
                        </>
                      ) : (
                        <>
                          <PauseCircle className="h-4 w-4" />
                          Неактивен
                        </>
                      )}
                    </Label>
                  </>
                )}
              />
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">Описание</label>
            <Input {...control.register("description")} />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium">
              Доступно организациям (Tenant)
            </label>
            <Controller
              name="tenant_ids"
              control={control}
              render={({ field }) => (
                <TenantMultiSelect
                  value={field.value ?? []}
                  onChange={field.onChange}
                />
              )}
            />
          </div>

          <DialogFooter>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : null}
              Сохранить
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
