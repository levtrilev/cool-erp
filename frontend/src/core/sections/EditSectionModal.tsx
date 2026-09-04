import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/use-toast";
import { useUpdateSectionSectionsSectionIdPut } from "@/api/generated/sections/sections";
import type { SectionResponseSchema } from "@/api/generated/fastAPI.schemas";
// import { Textarea } from "@/components/ui/textarea";

const sectionSchema = z.object({
  name: z.string().min(1, "Название обязательно").max(128),
});

type SectionFormData = z.infer<typeof sectionSchema>;

interface EditSectionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  section: SectionResponseSchema;
  onSectionUpdated: (sectionId: string, sectionName: string) => void;
}

export function EditSectionModal({
  open,
  onOpenChange,
  section,
  onSectionUpdated,
}: EditSectionModalProps) {
  const { toast } = useToast();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<SectionFormData>({
    resolver: zodResolver(sectionSchema),
    defaultValues: {
      name: section.name,
    },
  });

  useEffect(() => {
    reset({
      name: section.name,
    });
  }, [section.id, section.name, reset]);

  const updateMutation = useUpdateSectionSectionsSectionIdPut();

  const onSubmit = (data: SectionFormData) => {
    updateMutation.mutate(
      { sectionId: section.id, data },
      {
        onSuccess: async () => {
          onOpenChange(false);
          await onSectionUpdated(section.id, data.name);
        },
        onError: (error: unknown) => {
          toast({
            title: "Ошибка",
            description:
              error && typeof error === "object" && "message" in error
                ? (error.message as string)
                : "Ошибка обновления раздела",
            variant: "destructive",
          });
        },
      },
    );
  };

  //   useEffect(() => {
  //     reset({
  //       name: section.name,
  //     //   tenant_id: section.tenant_id,
  //     });
  //   }, [section.id, section.name, section.tenant_id, reset]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Редактировать раздел</DialogTitle>
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
            <span className="text-muted-foreground">
              Предприятие: {section.tenant_name}
            </span>
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
