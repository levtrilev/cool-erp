import { useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/components/ui/use-toast";

// ✅ Правило №9: Orval-хуки
import {
  useCreateSectionSectionsPost,
  useUpdateSectionSectionsSectionIdPut,
} from "@/api/generated/sections/sections";
import { readTenantsTenantsGet } from "@/api/generated/tenants/tenants";
import type { SectionResponseSchema } from "@/api/generated/fastAPI.schemas";

import { ReferenceSelect } from "@/lib/reusable/ReferenceSelect";
import {
  sectionFormSchema,
  CREATE_DEFAULTS,
  type SectionFormData,
} from "./schemas";

// ✅ Правило №35: обязательные пропсы модалки
interface EditSectionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData: SectionResponseSchema | null;
  onSaved: (id: string, name?: string) => Promise<void>;
}

export const EditSectionModal = ({
  open,
  onOpenChange,
  initialData,
  onSaved,
}: EditSectionModalProps) => {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // ✅ Правило №41: управление формой через useForm + zodResolver
  const {
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<SectionFormData>({
    resolver: zodResolver(sectionFormSchema),
    defaultValues: CREATE_DEFAULTS,
  });

  const createMutation = useCreateSectionSectionsPost();
  const updateMutation = useUpdateSectionSectionsSectionIdPut();

  // ✅ Правило №37: синхронизация формы при открытии
  // ✅ Правило №20: сброс при закрытии
  useEffect(() => {
    if (open) {
      if (initialData) {
        reset({
          name: initialData.name,
          description: initialData.description ?? "",
          tenant_id: initialData.tenant_id ?? "",
        });
      } else {
        reset(CREATE_DEFAULTS);
      }
    }
  }, [open, initialData, reset]);

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      reset(CREATE_DEFAULTS);
    }
    onOpenChange(newOpen);
  };

  const onSubmit = async (formData: SectionFormData) => {
    try {
      if (initialData) {
        // UPDATE произвольного раздела
        const section = await updateMutation.mutateAsync({
          sectionId: initialData.id,
          data: {
            name: formData.name,
            description: formData.description || null,
            // ✅ tenant_id НЕ отправляется — тенант раздела изменить нельзя
          },
        });

        // ✅ Правило №24: строгий порядок
        // 1. Инвалидация кэша
        await queryClient.invalidateQueries({ queryKey: ["sections"] });
        // 2. Закрытие модалки
        handleOpenChange(false);
        // 3. Callback родителя для подсветки
        await onSaved(section.data!.id, section.data!.name);
      } else {
        // CREATE произвольного раздела
        const section = await createMutation.mutateAsync({
          data: {
            name: formData.name,
            description: formData.description || null,
            // ✅ tenant_id НЕ отправляется — берётся из сессии
          },
        });

        await queryClient.invalidateQueries({ queryKey: ["sections"] });
        handleOpenChange(false);
        await onSaved(section.data!.id, section.data!.name);
      }
    } catch (error: unknown) {
      // ✅ Правило №36: безопасная обработка ошибок
      let message = "Не удалось сохранить раздел";
      const err = error as {
        response?: { data?: { detail?: string }; status?: number };
      };
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;

      if (status === 403) {
        message = detail || "Недостаточно прав для выполнения операции";
      } else if (status === 409) {
        message = detail || "Раздел с таким названием уже существует";
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

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {initialData ? "Редактировать раздел" : "Новый раздел"}
          </DialogTitle>
        </DialogHeader>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-4"
          id="section-form"
        >
          {/* ✅ Правило №41: поле через Controller */}
          <div className="space-y-2">
            <Label htmlFor="name">
              Название <span className="text-destructive">*</span>
            </Label>
            <Controller
              name="name"
              control={control}
              render={({ field }) => (
                <Input
                  id="name"
                  {...field}
                  placeholder="Введите название раздела"
                />
              )}
            />
            {/* ✅ Правило №41: ошибка валидации под полем */}
            {errors.name && (
              <p className="text-xs text-destructive">{errors.name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Описание</Label>
            <Controller
              name="description"
              control={control}
              render={({ field }) => (
                <Textarea
                  id="description"
                  {...field}
                  value={field.value ?? ""}
                  rows={3}
                  placeholder="Введите описание раздела..."
                />
              )}
            />
          </div>

          {/* ✅ Правило №27 + №42: ReferenceSelect для отображения организации
              Показывается ТОЛЬКО при редактировании (при создании тенант
              берётся из сессии). Поле заблокировано — тенант раздела
              изменить нельзя. */}
          {initialData && (
            <div className="space-y-2">
              <Label>Организация</Label>
              <Controller
                name="tenant_id"
                control={control}
                render={({ field }) => (
                  <ReferenceSelect
                    fetchFn={async (params) => {
                      const response = await readTenantsTenantsGet(params);
                      return {
                        items: response?.items ?? [],
                        total: response?.total ?? 0,
                      };
                    }}
                    queryKey={["tenants", "active"]}
                    value={field.value}
                    onValueChange={field.onChange}
                    placeholder="Выберите организацию..."
                    // ✅ Правило №42: денормализованное имя из ResponseSchema
                    selectedLabel={
                      initialData?.tenant_name ?? "Выберите организацию..."
                    }
                    heading="Организации"
                    limit={50}
                    disabled
                  />
                )}
              />
              <p className="text-xs text-muted-foreground">
                Организацию раздела изменить нельзя
              </p>
            </div>
          )}

          {/* ✅ Информация о типе раздела */}
          {initialData && (
            <p className="text-xs text-muted-foreground">
              Тип раздела:{" "}
              <span className="font-medium">
                {initialData.section_type_label || initialData.section_type}
              </span>
            </p>
          )}
        </form>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => handleOpenChange(false)}
          >
            Отмена
          </Button>
          {/* ✅ Правило №41: блокировка кнопки во время отправки */}
          <Button
            type="submit"
            form="section-form"
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
            {initialData ? "Сохранить" : "Создать"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};