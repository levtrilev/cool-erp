import { useEffect, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2, CheckCircle2, PauseCircle, Check, X } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
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
  useCreateDomainDomainsPost,
  useUpdateDomainDomainsDomainIdPut,
} from "@/api/generated/domains/domains";
// import type { DomainResponseSchema } from "@/api/generated/domains/domains";
import { useGetDoctypesDoctypesGet } from "@/api/generated/doctypes/doctypes";
// import type { DoctypeResponseSchema } from "@/api/generated/doctypes/doctypes";
import { EditDoctypeModal } from "@/core/doctypes/EditDoctypeModal";
import {
  DoctypeResponseSchema,
  DomainResponseSchema,
} from "@/api/generated/fastAPI.schemas";

// ✅ Правило №41: Zod-схема валидации
const domainFormSchema = z.object({
  name: z.string().min(1, "Название обязательно").max(128),
  description: z.string().optional(),
  prefix: z
    .string()
    .max(16, "Префикс не длиннее 16 символов")
    .regex(/^[a-z0-9_]*$/, "Только латиница в нижнем регистре, цифры и _")
    .optional()
    .or(z.literal("")),
  is_active: z.boolean().optional(),
});
type DomainFormData = z.infer<typeof domainFormSchema>;

// ✅ Правило №20: константа дефолтов вне компонента
const CREATE_DEFAULTS: DomainFormData = {
  name: "",
  description: "",
  prefix: "",
  is_active: true,
};

interface EditDomainModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData: DomainResponseSchema | null;
  onSaved: (id: string, name?: string) => Promise<void>;
}

export const EditDomainModal = ({
  open,
  onOpenChange,
  initialData,
  onSaved,
}: EditDomainModalProps) => {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<DomainFormData>({
    resolver: zodResolver(domainFormSchema),
    defaultValues: CREATE_DEFAULTS,
  });

  const createMutation = useCreateDomainDomainsPost();
  const updateMutation = useUpdateDomainDomainsDomainIdPut();

  // ✅ Правило №37: синхронизация формы при открытии
  useEffect(() => {
    if (open) {
      if (initialData) {
        reset({
          name: initialData.name,
          description: initialData.description ?? "",
          prefix: initialData.prefix ?? "",
          is_active: initialData.is_active,
        });
      } else {
        reset(CREATE_DEFAULTS);
      }
    }
  }, [open, initialData, reset]);

  // ================================================================
  // ВКЛАДКА «ТИПЫ ДОКУМЕНТОВ»: серверная загрузка по domain_id
  // ================================================================
  const { data: doctypesData, isLoading: isDoctypesLoading } =
    useGetDoctypesDoctypesGet(
      { domain_id: initialData?.id, skip: 0, limit: 1000 },
      { query: { enabled: open && !!initialData?.id } },
    );

  const doctypes: DoctypeResponseSchema[] = doctypesData?.data?.items ?? [];

  // Состояние вложенной модалки редактирования типа документа
  const [editingDoctype, setEditingDoctype] =
    useState<DoctypeResponseSchema | null>(null);
  const [isDoctypeModalOpen, setIsDoctypeModalOpen] = useState(false);

  const openDoctypeEdit = (item: DoctypeResponseSchema) => {
    setEditingDoctype(item);
    setIsDoctypeModalOpen(true);
  };

  // ✅ После сохранения типа документа: инвалидация + подсветка не нужны,
  // достаточно обновить список вкладки
  const handleDoctypeSaved = async () => {
    await queryClient.invalidateQueries({ queryKey: ["doctypes"] });
  };

  // ================================================================
  // СОХРАНЕНИЕ ДОМЕНА (Правило №24: invalidate → close → reset → onSaved)
  // ================================================================
  const onSubmit = async (formData: DomainFormData) => {
    try {
      const payload = {
        name: formData.name,
        description: formData.description || null,
        prefix: formData.prefix || null,
        is_active: formData.is_active ?? true,
      };

      let savedId: string;
      let savedName: string;

      if (initialData) {
        const res = await updateMutation.mutateAsync({
          domainId: initialData.id,
          data: payload,
        });
        savedId = res.data ? res.data.id : "";
        savedName = res.data ? res.data.name : "";
      } else {
        const res = await createMutation.mutateAsync({ data: payload });
        savedId = res.data ? res.data.id : "";
        savedName = res.data ? res.data.name : "";
      }

      // 1. Инвалидация ДО закрытия
      await queryClient.invalidateQueries({ queryKey: ["domains"] });
      // 2. Закрытие
      onOpenChange(false);
      // 3. Сброс формы
      reset(CREATE_DEFAULTS);
      // 4. Callback родителя
      await onSaved(savedId, savedName);
    } catch (error: unknown) {
      // ✅ Правило №36: безопасная обработка ошибок
      const err = error as { response?: { data?: { detail?: string } } };
      toast({
        variant: "destructive",
        title: "Ошибка сохранения",
        description:
          err?.response?.data?.detail || "Не удалось сохранить домен",
      });
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      reset(CREATE_DEFAULTS); // ✅ Правило №20
    }
    onOpenChange(newOpen);
  };

  return (
    <>
      <Dialog open={open} onOpenChange={handleOpenChange}>
        <DialogContent
          // className="max-w-3xl max-h-[90vh] overflow-y-auto"
          className="max-h-[90vh] items-start pt-8"
          style={{
            width: "900px",
            maxWidth: "900px",
            minHeight: "600px",
            height: "auto",
          }}
        >
          <DialogHeader>
            <DialogTitle>
              {initialData
                ? `Редактирование домена: ${initialData.name}`
                : "Создание домена"}
            </DialogTitle>
          </DialogHeader>

          <Tabs defaultValue="main">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="main">Основное</TabsTrigger>
              <TabsTrigger value="doctypes" disabled={!initialData}>
                Типы документов ({initialData ? doctypes.length : 0})
              </TabsTrigger>
            </TabsList>

            {/* ═══════════════ ВКЛАДКА 1: ОСНОВНОЕ ═══════════════ */}
            <TabsContent value="main" className="space-y-4 pt-4">
              <form
                onSubmit={handleSubmit(onSubmit)}
                className="space-y-4"
                id="domain-form"
              >
                <div className="space-y-2">
                  <Label htmlFor="domain-name">
                    Название <span className="text-destructive">*</span>
                  </Label>
                  <Controller
                    name="name"
                    control={control}
                    render={({ field }) => (
                      <Input
                        id="domain-name"
                        {...field}
                        placeholder="Например: Бизнес-партнёры"
                      />
                    )}
                  />
                  {errors.name && (
                    <p className="text-xs text-destructive">
                      {errors.name.message}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="domain-prefix">Префикс</Label>
                  <Controller
                    name="prefix"
                    control={control}
                    render={({ field }) => (
                      <Input
                        id="domain-prefix"
                        {...field}
                        value={field.value ?? ""}
                        placeholder="Например: bp"
                      />
                    )}
                  />
                  {errors.prefix && (
                    <p className="text-xs text-destructive">
                      {errors.prefix.message}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="domain-description">Описание</Label>
                  <Controller
                    name="description"
                    control={control}
                    render={({ field }) => (
                      <Input
                        id="domain-description"
                        {...field}
                        value={field.value ?? ""}
                        placeholder="Описание домена"
                      />
                    )}
                  />
                  {errors.description && (
                    <p className="text-xs text-destructive">
                      {errors.description.message}
                    </p>
                  )}
                </div>

                {/* ✅ Правило №34: Switch с визуальной обратной связью */}
                <div className="flex items-center gap-3">
                  <Controller
                    name="is_active"
                    control={control}
                    render={({ field }) => (
                      <>
                        <Switch
                          id="domain-is-active"
                          checked={field.value ?? true}
                          onCheckedChange={field.onChange}
                        />
                        <Label
                          htmlFor="domain-is-active"
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
                              Приостановлен
                            </>
                          )}
                        </Label>
                      </>
                    )}
                  />
                </div>
              </form>
            </TabsContent>

            {/* ═══════════════ ВКЛАДКА 2: ТИПЫ ДОКУМЕНТОВ ═══════════════ */}
            <TabsContent value="doctypes" className="pt-4">
              {isDoctypesLoading ? (
                // ✅ Правило №38: спиннер вместо пустой таблицы
                <div className="flex items-center justify-center h-40">
                  <Loader2 className="h-6 w-6 animate-spin" />
                </div>
              ) : (
                <Table className="table-fixed w-full">
                  <TableHeader className="sticky top-0 bg-background z-10 shadow-sm">
                    <TableRow className="h-10 hover:bg-transparent">
                      <TableHead style={{ width: 160 }}>Код</TableHead>
                      <TableHead style={{ width: 200 }}>Название</TableHead>
                      <TableHead style={{ width: 90 }}>Активен</TableHead>
                      <TableHead style={{ width: 110 }}>Разреш. теги</TableHead>
                      <TableHead style={{ width: 110 }}>Обяз. теги</TableHead>
                      <TableHead style={{ width: 120 }}>Организации</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {doctypes.length === 0 ? (
                      <TableRow>
                        <TableCell
                          colSpan={6}
                          className="py-6 text-center text-muted-foreground"
                        >
                          В домене нет типов документов
                        </TableCell>
                      </TableRow>
                    ) : (
                      doctypes.map((item) => (
                        <TableRow key={item.id}>
                          {/* ✅ Код — ссылка, открывает EditDoctypeModal */}
                          <TableCell className="py-1 align-top overflow-hidden">
                            <button
                              type="button"
                              onClick={() => openDoctypeEdit(item)}
                              className="text-left text-blue-600 hover:text-blue-800 hover:underline underline-offset-2 font-medium cursor-pointer w-full truncate block focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 rounded-sm transition-colors"
                              title={item.doctype}
                            >
                              {item.doctype}
                            </button>
                          </TableCell>
                          <TableCell className="py-1 align-top overflow-hidden">
                            <div
                              title={item.doctype_name}
                              className="block w-full truncate"
                            >
                              {item.doctype_name}
                            </div>
                          </TableCell>
                          <TableCell className="py-1 align-top">
                            {item.is_active ? (
                              <Check className="h-4 w-4 text-green-600" />
                            ) : (
                              <X className="h-4 w-4 text-red-500" />
                            )}
                          </TableCell>
                          <TableCell className="py-1 align-top">
                            {item.apply_or_tags ? (
                              <Check className="h-4 w-4 text-green-600" />
                            ) : (
                              <X className="h-4 w-4 text-muted-foreground" />
                            )}
                          </TableCell>
                          <TableCell className="py-1 align-top">
                            {item.apply_and_tags ? (
                              <Check className="h-4 w-4 text-green-600" />
                            ) : (
                              <X className="h-4 w-4 text-muted-foreground" />
                            )}
                          </TableCell>
                          <TableCell className="py-1 align-top">
                            {item.tenant_ids?.length ?? 0}
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              )}
              <p className="text-xs text-muted-foreground mt-2">
                Добавление и удаление типов документов выполняется на странице
                «Типы документов». Здесь — только просмотр и редактирование.
              </p>
            </TabsContent>
          </Tabs>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
            >
              Отмена
            </Button>
            <Button
              type="submit"
              form="domain-form"
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

      {/* ✅ Вложенная модалка типа документа — рендерится рядом, не внутри Dialog */}
      <EditDoctypeModal
        open={isDoctypeModalOpen}
        onOpenChange={setIsDoctypeModalOpen}
        initialData={editingDoctype}
        onSaved={handleDoctypeSaved}
      />
    </>
  );
};
