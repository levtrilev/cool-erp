import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/components/ui/use-toast";
import { useCreateSectionSectionsPost } from "@/api/generated/sections/sections";

const sectionSchema = z.object({
  name: z.string().min(1, "Название обязательно").max(128),
});

type SectionFormData = z.infer<typeof sectionSchema>;

interface CreateSectionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSectionCreated: (newId: string) => void;
}

export function CreateSectionModal({
  open,
  onOpenChange,
  onSectionCreated,
}: CreateSectionModalProps) {
  const { toast } = useToast();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<SectionFormData>({
    resolver: zodResolver(sectionSchema),
    defaultValues: {
      name: "",
    },
  });

  const createMutation = useCreateSectionSectionsPost();

  const onSubmit = (data: SectionFormData) => {
    createMutation.mutate(
      { data },
      {
        onSuccess: async (response) => {
          reset();
          onOpenChange(false);
          if (response.data?.id) {
            await onSectionCreated(response.data.id);
          } else {
            toast({ title: "Раздел создан" });
          }
        //   await onSectionCreated(response.data.id);
        },
        onError: (error: unknown) => {
          toast({
            title: "Ошибка",
            description:
              error && typeof error === "object" && "message" in error
                ? (error.message as string)
                : "Ошибка создания раздела",
            variant: "destructive",
          });
        },
      }
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Создать раздел</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <Label htmlFor="name">Название *</Label>
            <Input id="name" {...register("name")} />
            {errors.name && (
              <p className="text-sm text-red-500 mt-1">{errors.name.message}</p>
            )}
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