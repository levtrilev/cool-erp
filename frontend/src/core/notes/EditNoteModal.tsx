import { useEffect } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2, AlertCircle } from "lucide-react";
import { Lock as LockIcon } from "lucide-react";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { useToast } from "@/components/ui/use-toast";

import {
  useCreateNoteNotesPost,
  useUpdateNoteNotesNoteIdPut,
} from "@/api/generated/notes/notes";
import { getSectionsSectionsGet } from "@/api/generated/sections/sections";
import {
  NoteResponseSchema,
  // NoteCreateSchema,
  NoteCreateSchemaDocStatus,
  NoteUpdateSchemaDocStatus,
} from "@/api/generated/coolERP.schemas";

import { ReferenceSelect } from "@/lib/reusable/ReferenceSelect";
import {
  noteFormSchema,
  CREATE_DEFAULTS,
  DOC_STATUS_LABELS,
  type NoteFormData,
} from "./schemas";

interface EditNoteModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData: NoteResponseSchema | null;
  onSaved: (id: string, title?: string) => Promise<void>;
  readOnly?: boolean;
  readOnlyReason?: string;
  copyFromNote?: NoteResponseSchema | null;
}

// type StatusType = "draft" | "pending" | "approved" | "active" | "archived";
/**
 * Безопасный маппинг статуса из Update-контракта в Create-контракт.
 * Оба enum'а содержат идентичный набор строковых значений (контракт DocStatus),
 * но являются разными номинальными типами после генерации Orval 8.x.
 * Сопоставление по значениям через String() исключает приведения типов (Правило №44)
 * и не зависит от регистра имён членов enum'а.
 */
const mapDocStatusToCreate = (
  value: NoteUpdateSchemaDocStatus,
): NoteCreateSchemaDocStatus => {
  const target = Object.values(NoteCreateSchemaDocStatus).find(
    (candidate) => String(candidate) === String(value),
  );
  if (target === undefined) {
    throw new Error(
      `Статус документа "${String(value)}" отсутствует в схеме создания`,
    );
  }
  return target;
};


export const EditNoteModal = ({
  open,
  onOpenChange,
  initialData,
  onSaved,
  readOnly = false,
  readOnlyReason,
  copyFromNote = null,
}: EditNoteModalProps) => {
  // ✅ Режимы
  const isEdit = !!initialData;
  const isCopy = !!copyFromNote && !isEdit;
  const sourceNote = copyFromNote ?? initialData ?? null;
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<NoteFormData>({
    resolver: zodResolver(noteFormSchema),
    defaultValues: CREATE_DEFAULTS,
  });

  const createMutation = useCreateNoteNotesPost();
  const updateMutation = useUpdateNoteNotesNoteIdPut();

  useEffect(() => {
    if (open) {
      if (sourceNote) {
        reset({
          title: isCopy ? `${sourceNote.title} (копия)` : sourceNote.title,
          content: sourceNote.content ?? "",
          section_id: sourceNote.section_id,
          doc_number: isCopy ? undefined : (sourceNote.doc_number as string), // Копия — без номера
          doc_date: isCopy ? undefined : (sourceNote.doc_date as string),
          doc_status: isCopy ? NoteUpdateSchemaDocStatus.draft : (sourceNote.doc_status as NoteUpdateSchemaDocStatus),
          // doc_status: isCopy ? draft_status : sourceNote.doc_status,
          or_tags: sourceNote.or_tags ?? [],
          and_tags: sourceNote.and_tags ?? [],
        });
      } else {
        reset(CREATE_DEFAULTS);
      }
    }
  }, [open, sourceNote, isCopy, reset]);

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      reset(CREATE_DEFAULTS);
    }
    onOpenChange(newOpen);
  };

  const onSubmit = async (formData: NoteFormData) => {
    if (readOnly) return; // ✅ Защита от сохранения в режиме только чтения

    try {
      if (initialData) {
        if (!initialData.version) {
          toast({
            variant: "destructive",
            title: "Ошибка",
            description: "Отсутствует версия документа",
          });
          return;
        }

        const note = await updateMutation.mutateAsync({
          noteId: initialData.id,
          data: {
            title: formData.title,
            content: formData.content || null,
            section_id: formData.section_id,
            doc_status: formData.doc_status,
            doc_number: formData.doc_number || null,
            doc_date: formData.doc_date || null,
            or_tags: formData.or_tags ?? null,
            and_tags: formData.and_tags ?? null,
            version: initialData.version,
          },
        });

        await queryClient.invalidateQueries({ queryKey: ["notes"] });
        handleOpenChange(false);
        await onSaved(note.data!.id, note.data!.title);
      } else {
        const note = await createMutation.mutateAsync({
          data: {
            title: formData.title,
            content: formData.content || null,
            section_id: formData.section_id,
            // ✅ Приведение типа через indexed access type
            doc_status: mapDocStatusToCreate(formData.doc_status),
            doc_number: formData.doc_number || null,
            doc_date: formData.doc_date || null,
            or_tags: formData.or_tags ?? null,
            and_tags: formData.and_tags ?? null,
          },
        });

        await queryClient.invalidateQueries({ queryKey: ["notes"] });
        handleOpenChange(false);
        await onSaved(note.data!.id, note.data!.title);
      }
    } catch (error: unknown) {
      let message = "Не удалось сохранить заметку";
      const err = error as {
        response?: { data?: { detail?: string }; status?: number };
      };
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;

      if (status === 409) {
        message =
          "Документ был изменён другим пользователем. Обновите страницу и попробуйте снова.";
      } else if (status === 423) {
        message =
          "Документ сейчас редактируется другим пользователем. Попробуйте позже.";
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

  const parseTags = (value: string): string[] => {
    return value
      .split(/[,\n]/)
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
  };

  const joinTags = (tags: string[] | undefined): string => {
    return (tags ?? []).join(", ");
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent
        // className="max-w-2xl max-h-[90vh] overflow-y-auto"
        className="max-h-[90vh] items-start pt-8"
        style={{
          width: "500px",
          maxWidth: "500px",
          minHeight: "600px",
          height: "auto",
        }}
      >
        <DialogHeader>
          <DialogTitle>
            {readOnly
              ? "Просмотр заметки (только чтение)"
              : initialData
                ? "Редактировать заметку"
                : "Новая заметка"}
          </DialogTitle>
        </DialogHeader>

        {/* ✅ Предупреждение в режиме только чтения */}
        {readOnly && (
          <Alert
            variant="destructive"
            className="flex items-center gap-3 py-2.5"
          >
            {readOnlyReason?.includes("редактируется другим пользователем") && (
              <LockIcon className="h-4 w-4 shrink-0" />
            )}{" "}
            {readOnlyReason?.includes("нет прав на изменение") && (
              <AlertCircle className="h-4 w-4shrink-0" />
            )}{" "}
            {/* shrink-0 не дает иконке сжиматься */}
            <div className="flex flex-wrap items-baseline gap-x-2 text-sm">
              <AlertTitle className="font-semibold mb-0">
                Только чтение:
              </AlertTitle>
              <AlertDescription className="text-muted-foreground inline">
                {readOnlyReason || "Документ недоступен для редактирования."}
              </AlertDescription>
            </div>
          </Alert>
        )}

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-4"
          id="note-form"
        >
          <div className="space-y-2">
            <Label htmlFor="title">
              Название <span className="text-destructive">*</span>
            </Label>
            <Controller
              name="title"
              control={control}
              render={({ field }) => (
                <Input
                  id="title"
                  {...field}
                  placeholder="Введите название заметки"
                  disabled={readOnly}
                />
              )}
            />
            {errors.title && (
              <p className="text-xs text-destructive">{errors.title.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="content">Содержимое</Label>
            <Controller
              name="content"
              control={control}
              render={({ field }) => (
                <Textarea
                  id="content"
                  {...field}
                  value={field.value ?? ""}
                  rows={6}
                  placeholder="Текст заметки..."
                  disabled={readOnly}
                />
              )}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>
                Раздел <span className="text-destructive">*</span>
              </Label>
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
                      });
                      const items = (response?.data?.items ?? []).map(
                        (item) => ({
                          id: item.id,
                          name: item.name,
                        }),
                      );
                      return { items, total: response?.data?.total ?? 0 };
                    }}
                    queryKey={["sections", "active"]}
                    value={field.value}
                    onValueChange={field.onChange}
                    placeholder="Выберите раздел..."
                    selectedLabel={
                      (
                        initialData as
                          | (NoteResponseSchema & { section_name?: string })
                          | null
                      )?.section_name ?? "Выберите раздел..."
                    }
                    heading="Разделы"
                    limit={50}
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
            <div className="space-y-2">
              <Label htmlFor="doc_status">
                Статус <span className="text-destructive">*</span>
              </Label>
              <Controller
                name="doc_status"
                control={control}
                render={({ field }) => (
                  <Select
                    value={field.value}
                    onValueChange={field.onChange}
                    disabled={readOnly}
                  >
                    <SelectTrigger id="doc_status" className="w-full">
                      {" "}
                      {/* Добавлена явная ширина */}
                      <SelectValue placeholder="Выберите статус" />
                    </SelectTrigger>

                    {/* position="popper" принудительно заставляет окно вести себя как дропдаун (снизу) */}
                    <SelectContent
                      position="popper"
                      sideOffset={4}
                      className="w-[var(--radix-select-trigger-width)] max-h-60"
                      // w-[var(--radix-select-trigger-width)] делает ширину списка точно такой же, как у самого поля
                    >
                      {Object.entries(DOC_STATUS_LABELS).map(
                        ([value, label]) => (
                          <SelectItem key={value} value={value}>
                            {label}
                          </SelectItem>
                        ),
                      )}
                    </SelectContent>
                  </Select>
                )}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="doc_number">Номер документа</Label>
              <Controller
                name="doc_number"
                control={control}
                render={({ field }) => (
                  <Input
                    id="doc_number"
                    {...field}
                    value={field.value ?? ""}
                    placeholder="Например: Н-001"
                    maxLength={64}
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
            <div className="space-y-2">
              <Label htmlFor="doc_date">Дата документа</Label>
              <Controller
                name="doc_date"
                control={control}
                render={({ field }) => (
                  <Input
                    id="doc_date"
                    type="date"
                    {...field}
                    value={field.value ?? ""}
                    disabled={readOnly}
                  />
                )}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="or_tags">
              OR-теги{" "}
              <span className="text-xs text-muted-foreground">
                (через запятую, формат: пространство:значение)
              </span>
            </Label>
            <Controller
              name="or_tags"
              control={control}
              render={({ field }) => (
                <Input
                  id="or_tags"
                  value={joinTags(field.value)}
                  onChange={(e) => field.onChange(parseTags(e.target.value))}
                  placeholder="регион:сибирь, отдел:продажи"
                  disabled={readOnly}
                />
              )}
            />
            {errors.or_tags && (
              <p className="text-xs text-destructive">
                {errors.or_tags.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="and_tags">
              AND-теги{" "}
              <span className="text-xs text-muted-foreground">
                (обязательный допуск, через запятую)
              </span>
            </Label>
            <Controller
              name="and_tags"
              control={control}
              render={({ field }) => (
                <Input
                  id="and_tags"
                  value={joinTags(field.value)}
                  onChange={(e) => field.onChange(parseTags(e.target.value))}
                  placeholder="гриф:секретно"
                  disabled={readOnly}
                />
              )}
            />
            {errors.and_tags && (
              <p className="text-xs text-destructive">
                {errors.and_tags.message}
              </p>
            )}
          </div>

          {initialData && (
            <p className="text-xs text-muted-foreground">
              Версия: {initialData.version}
              {initialData.is_editing_locked &&
                " · 🔒 Заблокировано для редактирования"}
            </p>
          )}
        </form>

        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => handleOpenChange(false)}
          >
            {readOnly ? "Закрыть" : "Отмена"}
          </Button>
          {/* ✅ Кнопка Сохранить не рендерится в режиме только чтения */}
          {!readOnly && (
            <Button
              type="submit"
              form="note-form"
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
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
