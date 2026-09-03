import { useQueryClient } from "@tanstack/react-query"; // useMutation, 
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { useToast } from "@/components/ui/use-toast";
import {
  useCreateTenantTenantsPost,
} from "@/api/generated/tenants/tenants";
// import type { TenantCreateSchema } from "@/api/generated/fastAPI.schemas";

const tenantSchema = z.object({
  name: z.string().min(1, "Название обязательно").max(128),
  description: z.string().max(255).optional(),
  active: z.boolean(),
});

type TenantFormData = z.infer<typeof tenantSchema>;

interface CreateTenantModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTenantCreated: (newId: string) => void;
}

export function CreateTenantModal({ open, onOpenChange, onTenantCreated }: CreateTenantModalProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<TenantFormData>({
    resolver: zodResolver(tenantSchema),
    defaultValues: {
      name: "",
      description: "",
      active: true,
    },
  });

  const createMutation = useCreateTenantTenantsPost();

  const onSubmit = (data: TenantFormData) => {
    createMutation.mutate(
      { data },
      {
        onSuccess: async (response) => {
          queryClient.invalidateQueries({ queryKey: ["tenants"] });
          onOpenChange(false);
          reset();

          if (response?.id) {
            await onTenantCreated(response.id);
          } else {
            toast({ title: "Организация создана" });
          }
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
              description: "Ошибка создания организации!",
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
          <DialogTitle>Создать организацию</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <Label htmlFor="name">Название *</Label>
            <Input id="name" {...register("name")} />
            {errors.name && <p className="text-sm text-red-500 mt-1">{errors.name.message}</p>}
          </div>
          <div>
            <Label htmlFor="description">Описание</Label>
            <Textarea id="description" {...register("description")} />
          </div>
          <div className="flex items-center space-x-2">
            <Switch id="active" {...register("active")} />
            <Label htmlFor="active">Активна</Label>
          </div>
          <div className="flex gap-2">
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? "Создание..." : "Создать"}
            </Button>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Отмена
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}