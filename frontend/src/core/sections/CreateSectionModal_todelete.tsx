// import { useForm, Controller } from "react-hook-form";
// import { zodResolver } from "@hookform/resolvers/zod";
// import { z } from "zod";
// import { Loader2 } from "lucide-react";
// import { useQueryClient } from "@tanstack/react-query";
// import {
//   Dialog,
//   DialogContent,
//   DialogHeader,
//   DialogTitle,
// } from "@/components/ui/dialog";
// import { Button } from "@/components/ui/button";
// import { Input } from "@/components/ui/input";
// import { Label } from "@/components/ui/label";
// import { Textarea } from "@/components/ui/textarea";
// import { useToast } from "@/components/ui/use-toast";
// import { useCreateSectionSectionsPost } from "@/api/generated/sections/sections";
// import { sectionFormSchema, CREATE_DEFAULTS, type SectionFormData } from "./schemas";

// interface CreateSectionModalProps {
//   open: boolean;
//   onOpenChange: (open: boolean) => void;
//   onSectionCreated: (id: string, name?: string) => Promise<void>;
// }

// export function CreateSectionModal({
//   open,
//   onOpenChange,
//   onSectionCreated,
// }: CreateSectionModalProps) {
//   const { toast } = useToast();
//   const queryClient = useQueryClient();

//   // ✅ Правило №41: управление формой через useForm + zodResolver
//   const {
//     control,
//     handleSubmit,
//     reset,
//     formState: { errors, isSubmitting },
//   } = useForm<SectionFormData>({
//     resolver: zodResolver(sectionFormSchema),
//     defaultValues: CREATE_DEFAULTS,
//   });

//   const createMutation = useCreateSectionSectionsPost();

//   // ✅ Правило №20: сброс формы при закрытии
//   const handleOpenChange = (newOpen: boolean) => {
//     if (!newOpen) {
//       reset(CREATE_DEFAULTS);
//     }
//     onOpenChange(newOpen);
//   };

//   const onSubmit = async (formData: SectionFormData) => {
//     try {
//       const section = await createMutation.mutateAsync({
//         data: {
//           name: formData.name,
//           description: formData.description || null,
//         },
//       });

//       // ✅ Правило №24: строгий порядок
//       // 1. Инвалидация кэша
//       await queryClient.invalidateQueries({ queryKey: ["sections"] });
//       // 2. Сброс формы
//       reset(CREATE_DEFAULTS);
//       // 3. Закрытие модалки
//       onOpenChange(false);
//       // 4. Callback родителя для подсветки
//       await onSectionCreated(section.data!.id, section.data!.name);
//     } catch (error: unknown) {
//       // ✅ Правило №36: безопасная обработка ошибок
//       let message = "Не удалось создать раздел";
//       const err = error as {
//         response?: { data?: { detail?: string }; status?: number };
//       };
//       const status = err?.response?.status;
//       const detail = err?.response?.data?.detail;

//       if (status === 403) {
//         message = detail || "Недостаточно прав для создания раздела";
//       } else if (status === 409) {
//         message = detail || "Раздел с таким названием уже существует";
//       } else if (detail) {
//         message = detail;
//       }

//       toast({
//         variant: "destructive",
//         title: "Ошибка создания",
//         description: message,
//       });
//     }
//   };

//   return (
//     <Dialog open={open} onOpenChange={handleOpenChange}>
//       <DialogContent className="max-w-lg">
//         <DialogHeader>
//           <DialogTitle>Создать раздел</DialogTitle>
//         </DialogHeader>

//         <form
//           onSubmit={handleSubmit(onSubmit)}
//           className="space-y-4"
//           id="section-create-form"
//         >
//           {/* ✅ Правило №41: поле через Controller */}
//           <div className="space-y-2">
//             <Label htmlFor="name">
//               Название <span className="text-destructive">*</span>
//             </Label>
//             <Controller
//               name="name"
//               control={control}
//               render={({ field }) => (
//                 <Input
//                   id="name"
//                   {...field}
//                   placeholder="Введите название раздела"
//                 />
//               )}
//             />
//             {/* ✅ Правило №41: ошибка валидации под полем */}
//             {errors.name && (
//               <p className="text-xs text-destructive">{errors.name.message}</p>
//             )}
//           </div>

//           <div className="space-y-2">
//             <Label htmlFor="description">Описание</Label>
//             <Controller
//               name="description"
//               control={control}
//               render={({ field }) => (
//                 <Textarea
//                   id="description"
//                   {...field}
//                   value={field.value ?? ""}
//                   rows={3}
//                   placeholder="Введите описание раздела..."
//                 />
//               )}
//             />
//           </div>
//         </form>

//         <div className="flex gap-2 justify-end">
//           <Button
//             type="button"
//             variant="outline"
//             onClick={() => handleOpenChange(false)}
//           >
//             Отмена
//           </Button>
//           {/* ✅ Правило №41: блокировка кнопки во время отправки */}
//           <Button
//             type="submit"
//             form="section-create-form"
//             disabled={isSubmitting || createMutation.isPending}
//           >
//             {(isSubmitting || createMutation.isPending) && (
//               <Loader2 className="mr-2 h-4 w-4 animate-spin" />
//             )}
//             {isSubmitting || createMutation.isPending ? "Создание..." : "Создать"}
//           </Button>
//         </div>
//       </DialogContent>
//     </Dialog>
//   );
// }