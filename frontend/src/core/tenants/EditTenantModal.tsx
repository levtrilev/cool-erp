import { useEffect } from "react"; // ← 1. ДОБАВИТЬ
import { useQueryClient } from "@tanstack/react-query";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { CheckCircle2, PauseCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/components/ui/use-toast";
import { useUpdateTenantTenantsTenantIdPut } from "@/api/generated/tenants/tenants";
import type { TenantResponseSchema } from "@/api/generated/fastAPI.schemas";

const tenantSchema = z.object({
  name: z.string().min(1, "Название обязательно").max(128),
  description: z.string().max(255).optional(),
  active: z.boolean(), // ← Требует строго true или false
});

type TenantFormData = z.infer<typeof tenantSchema>;

interface EditTenantModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  tenant: TenantResponseSchema;
  onTenantUpdated: (tenantId: string, tenantName: string) => void;
}

export function EditTenantModal({
  open,
  onOpenChange,
  tenant,
  onTenantUpdated,
}: EditTenantModalProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const {
    register,
    handleSubmit,
    control,
    reset, // ← 2. ДОБАВИТЬ
    formState: { errors },
  } = useForm<TenantFormData>({
    resolver: zodResolver(tenantSchema),
    defaultValues: {
      name: tenant.name,
      description: tenant.description || "",
      active: tenant.active === true, // ← 3. ЖЁСТКОЕ ПРЕОБРАЗОВАНИЕ (защита от строк "true" или null)
    },
  });

  // ← 4. ГАРАНТИРОВАННЫЙ СБРОС ФОРМЫ ПРИ СМЕНЕ TENANT
  // Это спасает, даже если в родительском компоненте забыли добавить key={tenant.id}
  useEffect(() => {
    reset({
      name: tenant.name,
      description: tenant.description || "",
      active: tenant.active === true,
    });
  }, [tenant.id, tenant.active, tenant.name, tenant.description, reset]);

  const updateMutation = useUpdateTenantTenantsTenantIdPut();

  const onSubmit = (data: TenantFormData) => {
    updateMutation.mutate(
      { tenantId: tenant.id, data },
      {
        onSuccess: async () => {
          queryClient.invalidateQueries({ queryKey: ["tenants"] });
          onOpenChange(false);
          await onTenantUpdated(tenant.id, data.name);
        },
        onError: (error: unknown) => {
          if (
            error &&
            typeof error === "object" &&
            "message" in error &&
            typeof error.message === "string"
          ) {
            toast({
              title: "Ошибка",
              description: error.message,
              variant: "destructive",
            });
          } else {
            toast({
              title: "Ошибка",
              description: "Ошибка обновления организации!",
              variant: "destructive",
            });
          }
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Редактировать организацию</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <Label htmlFor="name">Название *</Label>
            <Input id="name" {...register("name")} />
            {errors.name && (
              <p className="text-sm text-red-500 mt-1">{errors.name.message}</p>
            )}
          </div>
          <div>
            <Label htmlFor="description">Описание</Label>
            <Textarea id="description" {...register("description")} />
          </div>

          {/* 🎨 Красивый переключатель статуса */}
          {/* <div className="flex items-center space-x-3 pt-2"> */}
          <div className="mt-0">
            <Controller
              name="active"
              control={control}
              render={({ field }) => (
                <>
                  <Switch
                    id="active"
                    checked={field.value}
                    onCheckedChange={field.onChange}
                  />
                  <Label 
                    htmlFor="active" 
                    className={`flex items-center gap-2 cursor-pointer font-medium transition-colors ${
                      field.value 
                        ? "text-green-600 dark:text-green-400" 
                        : "text-red-500 dark:text-red-400"
                    }`}
                  >
                    {field.value ? (
                      <>
                        <CheckCircle2 className="h-4 w-4" />
                        Организация активна
                      </>
                    ) : (
                      <>
                        <PauseCircle className="h-4 w-4" />
                        Организация приостановлена
                      </>
                    )}
                  </Label>
                </>
              )}
            />
          </div>

          <div className="flex gap-2">
            <Button type="submit" disabled={updateMutation.isPending}>
              {updateMutation.isPending ? "Сохранение..." : "Сохранить"}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Отмена
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
