import { useEffect } from "react";
import { useForm, Controller, type FieldErrors } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2, Check, AlertCircle } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

// ✅ Orval-хуки (Правило №9). Имена зависят от конфигурации orval.config.ts.
// После перегенерации (npm run generate:api) уточните фактические имена.
import {
  useCreateWarehouseInventoryWarehousesPost,
  useUpdateWarehouseInventoryWarehousesWarehouseIdPut,
} from "@/api/generated/inventory-warehouses/inventory-warehouses";
import { getSectionsSectionsGet } from "@/api/generated/sections/sections";
import { useGetUserAuthUserGet } from "@/api/generated/authentication/authentication";
import type { InvWarehouseResponseSchema } from "@/api/generated/fastAPI.schemas";
import {
  ReferenceSelect,
  type ReferenceItem,
} from "@/lib/reusable/ReferenceSelect";

// ✅ Правило №41: Zod-схема валидации
const warehouseFormSchema = z.object({
  name: z.string().min(1, "Название обязательно").max(255),
  description: z.string().optional(),
  section_id: z.string().min(1, "Выберите раздел"),
  doc_number: z.string().max(64).optional(),
  doc_date: z.string().optional(),
});

type WarehouseFormData = z.infer<typeof warehouseFormSchema>;

// ✅ Правило №20: Константа для сброса формы
const CREATE_DEFAULTS: WarehouseFormData = {
  name: "",
  description: "",
  section_id: "",
  doc_number: "",
  doc_date: "",
};

interface EditWarehouseModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData: InvWarehouseResponseSchema | null;
  onSaved: (id: string, name: string) => Promise<void>;
  /** ✅ Правило №39: режим только для чтения при блокировке */
  readOnly?: boolean;
}

export function EditWarehouseModal({
  open,
  onOpenChange,
  initialData,
  onSaved,
  readOnly = false,
}: EditWarehouseModalProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { data: userData } = useGetUserAuthUserGet();
  const currentTenantId = userData?.data?.tenant_id;
  const isEdit = !!initialData;

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<WarehouseFormData>({
    resolver: zodResolver(warehouseFormSchema),
    defaultValues: CREATE_DEFAULTS,
  });

  const createMutation = useCreateWarehouseInventoryWarehousesPost();
  const updateMutation = useUpdateWarehouseInventoryWarehousesWarehouseIdPut();

  // ✅ Правило №37: Синхронизация формы при открытии
  useEffect(() => {
    if (open) {
      if (initialData) {
        reset({
          name: initialData.name,
          description: initialData.description || "",
          section_id: initialData.section_id,
          doc_number: initialData.doc_number || "",
          // ✅ Дата в формате YYYY-MM-DD для Input type="date"
          doc_date: initialData.doc_date
            ? new Date(initialData.doc_date).toISOString().split("T")[0]
            : "",
        });
      } else {
        reset(CREATE_DEFAULTS);
      }
    }
  }, [open, initialData, reset]);

  // ✅ Правило №20: при закрытии сброс формы
  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      reset(CREATE_DEFAULTS);
    }
    onOpenChange(newOpen);
  };

  // ✅ Правило №39: защита от сохранения в режиме только чтения
  const onSubmit = async (data: WarehouseFormData) => {
    if (readOnly) return;

    if (!currentTenantId) {
      toast({
        variant: "destructive",
        title: "Ошибка",
        description: "Не определена текущая организация",
      });
      return;
    }

    try {
      if (isEdit && initialData) {
        // ✅ Обновление с оптимистической блокировкой (Правило №40, часть 2.1)
        await updateMutation.mutateAsync({
          warehouseId: initialData.id,
          data: {
            name: data.name,
            description: data.description || null,
            section_id: data.section_id,
            doc_number: data.doc_number || null,
            doc_date: data.doc_date || null,
            // ✅ Обязательная ожидаемая версия для оптимистической блокировки
            version: initialData.version,
          },
        });

        // ✅ Правило №24: строгий порядок действий
        await queryClient.invalidateQueries({ queryKey: ["inventory-warehouses"] });
        onOpenChange(false);
        reset(CREATE_DEFAULTS);
        await onSaved(initialData.id, data.name);
      } else {
        // ✅ Создание
        const res = await createMutation.mutateAsync({
          data: {
            name: data.name,
            description: data.description || null,
            tenant_id: currentTenantId,
            section_id: data.section_id,
            doc_number: data.doc_number || null,
            doc_date: data.doc_date || null,
          },
        });

        await queryClient.invalidateQueries({ queryKey: ["inventory-warehouses"] });
        onOpenChange(false);
        reset(CREATE_DEFAULTS);
        const newId = res.data?.id || "";
        await onSaved(newId, data.name);
      }
    } catch (error: unknown) {
      // ✅ Правило №36: безопасная обработка ошибок
      // ✅ Правило №39: обработка 409 и 423
      let message = "Не удалось сохранить склад";
      const err = error as {
        response?: { status?: number; data?: { detail?: string } };
      };
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;

      if (status === 409) {
        message =
          "Склад был изменён другим пользователем. Обновите страницу и попробуйте снова.";
      } else if (status === 423) {
        message =
          "Склад сейчас редактируется другим пользователем. Попробуйте позже.";
      } else if (detail) {
        message = detail;
      }

      toast({
        variant: "destructive",
        title: "Ошибка сохранения",
        description: message,
      });
    }
  };

  const onInvalid = (formErrors: FieldErrors<WarehouseFormData>) => {
    console.warn("Ошибки валидации формы:", formErrors);
    toast({
      variant: "destructive",
      title: "Ошибка заполнения формы",
      description:
        "Пожалуйста, проверьте правильность заполнения полей. Название и раздел обязательны.",
    });
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {/* ✅ Правило №39: заголовок зависит от режима */}
            {readOnly
              ? "Просмотр склада (только чтение)"
              : isEdit
                ? `Редактирование склада: ${initialData?.name}`
                : "Новый склад"}
          </DialogTitle>
        </DialogHeader>

        {/* ✅ Правило №39: предупреждение в режиме только чтения */}
        {readOnly && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Склад заблокирован</AlertTitle>
            <AlertDescription>
              Склад редактируется другим пользователем. Вы можете только
              просматривать данные.
            </AlertDescription>
          </Alert>
        )}

        <form
          onSubmit={handleSubmit(onSubmit, onInvalid)}
          className="space-y-4"
          id="warehouse-form"
        >
          {/* Название */}
          <div className="space-y-2">
            <label className="text-sm font-medium">
              Название <span className="text-destructive">*</span>
            </label>
            <Controller
              name="name"
              control={control}
              render={({ field }) => (
                <Input
                  {...field}
                  placeholder="Например: Центральный склад"
                  disabled={readOnly}
                />
              )}
            />
            {errors.name && (
              <p className="text-xs text-destructive">{errors.name.message}</p>
            )}
          </div>

          {/* Описание */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Описание</label>
            <Controller
              name="description"
              control={control}
              render={({ field }) => (
                <Textarea
                  {...field}
                  placeholder="Описание склада..."
                  rows={3}
                  disabled={readOnly}
                />
              )}
            />
            {errors.description && (
              <p className="text-xs text-destructive">
                {errors.description.message}
              </p>
            )}
          </div>

          {/* ✅ Раздел через ReferenceSelect (Правило №27, №42) */}
          <div className="space-y-2">
            <label className="text-sm font-medium">
              Раздел <span className="text-destructive">*</span>
            </label>
            <Controller
              name="section_id"
              control={control}
              render={({ field }) => (
                <ReferenceSelect
                  fetchFn={async (params) => {
                    const response = await getSectionsSectionsGet({
                      skip: params.skip,
                      limit: params.limit,
                      search: params.search,
                      target_tenant_id: currentTenantId,
                    });
                    const items: ReferenceItem[] = (
                      response?.data?.items ?? []
                    ).map((item: unknown) => {
                      const typedItem = item as {
                        id: string;
                        name: string;
                        description?: string | null;
                      };
                      return {
                        id: typedItem.id,
                        name: typedItem.name,
                        description: typedItem.description,
                      };
                    });
                    return { items, total: response?.data?.total ?? 0 };
                  }}
                  queryKey={["sections", "warehouses", currentTenantId || ""]}
                  value={field.value}
                  onValueChange={field.onChange}
                  placeholder="Выберите раздел..."
                  // ✅ Правило №27 + №42: мгновенное отображение при редактировании
                  selectedLabel={initialData?.section_name ?? "Выберите раздел..."}
                  heading="Разделы доступа"
                  limit={50}
                  columns={[{ column: "description", label: "Описание" }]}
                  disabled={readOnly}
                />
              )}
            />
            {errors.section_id && (
              <p className="text-xs text-destructive">
                {errors.section_id.message}
              </p>
            )}
          </div>

          {/* Номер документа */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Номер документа</label>
            <Controller
              name="doc_number"
              control={control}
              render={({ field }) => (
                <Input
                  {...field}
                  placeholder="Например: СКЛ-001"
                  disabled={readOnly}
                />
              )}
            />
            {errors.doc_number && (
              <p className="text-xs text-destructive">
                {errors.doc_number.message}
              </p>
            )}
          </div>

          {/* Дата документа */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Дата документа</label>
            <Controller
              name="doc_date"
              control={control}
              render={({ field }) => (
                <Input {...field} type="date" disabled={readOnly} />
              )}
            />
            {errors.doc_date && (
              <p className="text-xs text-destructive">
                {errors.doc_date.message}
              </p>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
            >
              {/* ✅ Правило №39: текст кнопки зависит от режима */}
              {readOnly ? "Закрыть" : "Отмена"}
            </Button>

            {/* ✅ Правило №39: Кнопка Сохранить не рендерится в режиме только чтения */}
            {!readOnly && (
              <Button
                type="submit"
                form="warehouse-form"
                disabled={
                  isSubmitting ||
                  createMutation.isPending ||
                  updateMutation.isPending
                }
              >
                {(isSubmitting ||
                  createMutation.isPending ||
                  updateMutation.isPending) && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                <Check className="mr-2 h-4 w-4" />
                {isEdit ? "Сохранить" : "Создать"}
              </Button>
            )}
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}