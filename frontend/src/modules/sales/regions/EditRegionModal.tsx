import { useEffect, useMemo } from "react";
import {
  useForm,
  Controller,
  useWatch,
  type FieldErrors,
} from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2, Check, AlertCircle } from "lucide-react";
import { useToast } from "@/components/ui/use-toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

// ✅ Orval-хуки (Правило №9). Имена зависят от orval.config.ts —
// после npm run generate:api сверьте фактические имена.
import {
  useCreateRegionSalesRegionsPost,
  useUpdateRegionSalesRegionsRegionIdPut,
} from "@/api/generated/sales-regions/sales-regions";
import type { SalesRegionResponseSchema } from "@/api/generated/fastAPI.schemas";

// ==================================================================
// ✅ Спецификация: business_rules.fixed_tenant_and_section
// Регионы — глобальный справочник с кросс-организационной видимостью.
// Создаются в организации суперадмина в разделе «Общий» (ТЗ §4.3).
// Эти значения НЕ редактируются пользователем.
// ==================================================================
const SUPERADMIN_TENANT_ID: string = "38d6532a-e1b7-45c5-ab41-11317528d85e";
const COMMON_SECTION_ID: string = "61a895ab-58cd-45d4-beba-f563f395d333"; // «Общий»
const COMMON_SECTION_NAME: string = "Общий";

// ✅ Правило №41: Zod-схема валидации
const regionFormSchema = z.object({
  // Вкладка «Реквизиты»
  name: z.string().min(1, "Название обязательно").max(128),
  capital: z.string().max(128).optional(),
  code: z
    .string()
    .refine((val) => val === "" || val.length <= 8, {
      message: "Не более 8 символов",
    })
    .optional(),
  area: z.string().max(64).optional(),
  // Вкладка «Документ» (контракт)
  doc_number: z.string().max(64).optional(),
  doc_date: z.string().optional(),
});

type RegionFormData = z.infer<typeof regionFormSchema>;

// ✅ Правило №20: Константа для сброса формы
const CREATE_DEFAULTS: RegionFormData = {
  name: "",
  capital: "",
  code: "",
  area: "",
  doc_number: "",
  doc_date: "",
};

interface EditRegionModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData: SalesRegionResponseSchema | null;
  onSaved: (id: string, name: string) => Promise<void>;
  /** ✅ Правило №39: режим только для чтения при блокировке */
  readOnly?: boolean;
  /** ✅ Спецификация: режим копирования */
  copyFromData?: SalesRegionResponseSchema | null;
}

export function EditRegionModal({
  open,
  onOpenChange,
  initialData,
  onSaved,
  readOnly = false,
  copyFromData,
}: EditRegionModalProps) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // ✅ Вычисление режимов работы
  // При копировании: создаём НОВУЮ запись с данными из источника
  const isEdit: boolean = !!initialData && !copyFromData;
  const isCopy: boolean = !!copyFromData && !isEdit;
  const sourceData: SalesRegionResponseSchema | null =
    copyFromData ?? initialData ?? null;

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<RegionFormData>({
    resolver: zodResolver(regionFormSchema),
    defaultValues: CREATE_DEFAULTS,
  });

  const createMutation = useCreateRegionSalesRegionsPost();
  const updateMutation = useUpdateRegionSalesRegionsRegionIdPut();

  // ==========================================
  // ✅ Правило №37: Синхронизация формы при открытии
  // Учитывает режим копирования: суффикс имени, сброс doc_number/doc_date
  // ==========================================
  useEffect(() => {
    if (open) {
      if (sourceData) {
        reset({
          // ✅ Спецификация: name_transform = "{name} (копия)"
          name: isCopy ? `${sourceData.name} (копия)` : sourceData.name,
          // ✅ Спецификация: preserve_fields = [capital, code, area]
          capital: sourceData.capital || "",
          code: sourceData.code || "",
          area: sourceData.area || "",
          // ✅ При копировании doc_number и doc_date сбрасываются
          // (копия — новый документ)
          doc_number: isCopy ? "" : sourceData.doc_number || "",
          doc_date: isCopy
            ? ""
            : sourceData.doc_date
              ? new Date(sourceData.doc_date).toISOString().split("T")[0]
              : "",
        });
      } else {
        reset(CREATE_DEFAULTS);
      }
    }
  }, [open, sourceData, isCopy, reset]);

  // ✅ Правило №20: при закрытии сброс формы
  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      reset(CREATE_DEFAULTS);
    }
    onOpenChange(newOpen);
  };

  // ==========================================
  // ИНДИКАТОРЫ ИЗМЕНЕНИЙ (спецификация: change_indicators)
  // Поимённое сравнение с исходными данными (режим: field_by_field)
  // ==========================================
  const watchedValues = useWatch({ control });

  const hasBasicsChanges = useMemo<boolean>(() => {
    if (!sourceData) return isEdit ? false : true;
    return (
      (watchedValues.name || "") !== (sourceData.name || "") ||
      (watchedValues.capital || "") !== (sourceData.capital || "") ||
      (watchedValues.code || "") !== (sourceData.code || "") ||
      (watchedValues.area || "") !== (sourceData.area || "")
    );
  }, [watchedValues, sourceData, isEdit]);

  const hasDocumentChanges = useMemo<boolean>(() => {
    if (!sourceData) return isEdit ? false : true;
    const sourceDocDate: string = sourceData.doc_date
      ? new Date(sourceData.doc_date).toISOString().split("T")[0]
      : "";
    return (
      (watchedValues.doc_number || "") !== (sourceData.doc_number || "") ||
      (watchedValues.doc_date || "") !== sourceDocDate
    );
  }, [watchedValues, sourceData, isEdit]);

  // ✅ Спецификация: has_any_changes.formula = "basics or document"
  const hasAnyChanges: boolean = hasBasicsChanges || hasDocumentChanges;

  // ==========================================
  // СОХРАНЕНИЕ (спецификация: payload + mutation_params)
  // Режим копирования использует мутацию СОЗДАНИЯ, не обновления
  // ==========================================
  const onSubmit = async (data: RegionFormData) => {
    // ✅ Правило №39: защита от сохранения в режиме только чтения
    if (readOnly) return;

    try {
      if (isEdit && initialData) {
        // ✅ Обновление с оптимистической блокировкой (Бэкенд Правило №40)
        await updateMutation.mutateAsync({
          regionId: initialData.id,
          data: {
            name: data.name,
            capital: data.capital || null,
            code: data.code || null,
            area: data.area || null,
            doc_number: data.doc_number || null,
            doc_date: data.doc_date || null,
            // ✅ Обязательная ожидаемая версия (оптимистическая блокировка)
            // ✅ Спецификация: tenant_id и section_id НЕ передаются
            // (не меняются при редактировании — правило tenant_immutable)
            version: initialData.version,
          },
        });

        // ✅ Правило №24: строгий порядок действий
        await queryClient.invalidateQueries({ queryKey: ["sales-regions"] });
        onOpenChange(false);
        reset(CREATE_DEFAULTS);
        await onSaved(initialData.id, data.name);
      } else {
        // ✅ Создание (включая копирование)
        // Режим копирования использует мутацию СОЗДАНИЯ
        const res = await createMutation.mutateAsync({
          data: {
            name: data.name,
            capital: data.capital || null,
            code: data.code || null,
            area: data.area || null,
            // ✅ Спецификация: фиксированные значения для глобального справочника
            // Передаются ТОЛЬКО при создании (включая копирование)
            tenant_id: SUPERADMIN_TENANT_ID,
            section_id: COMMON_SECTION_ID,
            doc_number: data.doc_number || null,
            doc_date: data.doc_date || null,
            // ✅ version НЕ передаётся — новая запись всегда версия 1
            // ✅ author_id, created_by_user_id заполняет бэкенд из сессии
          },
        });

        await queryClient.invalidateQueries({ queryKey: ["sales-regions"] });
        // ✅ Спецификация: modes.copy.close_after_save = true
        onOpenChange(false);
        reset(CREATE_DEFAULTS);
        const newId: string = res.data?.id || "";
        await onSaved(newId, data.name);
      }
    } catch (error: unknown) {
      // ✅ Правило №36: безопасная обработка ошибок
      // ✅ Правило №39 + спецификация events.on_save_error: обработка 409 и 423
      let message: string = "Не удалось сохранить регион";
      const err = error as {
        response?: { status?: number; data?: { detail?: string } };
      };
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;

      if (status === 409) {
        message = "Регион изменён другим пользователем. Обновите данные.";
      } else if (status === 423) {
        message = "Регион редактируется другим пользователем.";
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

  const onInvalid = (formErrors: FieldErrors<RegionFormData>) => {
    console.warn("Ошибки валидации формы:", formErrors);
    toast({
      variant: "destructive",
      title: "Ошибка заполнения формы",
      description:
        "Пожалуйста, проверьте правильность заполнения полей. Название обязательно.",
    });
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {/* ✅ Спецификация: titles */}
            {readOnly
              ? "Просмотр региона (только чтение)"
              : isEdit
                ? `Редактирование региона: ${sourceData?.name}`
                : isCopy
                  ? `Копирование региона: ${sourceData?.name}`
                  : "Новый регион"}
          </DialogTitle>
        </DialogHeader>

        {/* ✅ Правило №39: предупреждение в режиме только чтения */}
        {readOnly && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>Регион заблокирован</AlertTitle>
            <AlertDescription>
              Регион редактируется другим пользователем. Вы можете только
              просматривать данные.
            </AlertDescription>
          </Alert>
        )}

        <form
          onSubmit={handleSubmit(onSubmit, onInvalid)}
          className="space-y-4"
          id="region-form"
        >
          {/* Организация и раздел: фиксированные значения */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Организация / Раздел</label>
            <div className="px-3 py-2 rounded-md border bg-muted/50 text-sm">
              Раздел «{COMMON_SECTION_NAME}» (кросс-организационная видимость)
            </div>
            <p className="text-xs text-muted-foreground">
              Регионы — глобальный справочник. Создаются в разделе «Общий» и
              видны всем организациям (ТЗ §4.3).
            </p>
          </div>

          <Tabs defaultValue="main" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              {/* Вкладка «Реквизиты» с индикатором изменений */}
              <TabsTrigger value="main" className="relative">
                Реквизиты
                {hasBasicsChanges && (
                  <span className="absolute -top-1 -right-1 text-amber-500 text-xl font-bold leading-none">
                    *
                  </span>
                )}
              </TabsTrigger>
              {/* Вкладка «Документ» (поля контракта) */}
              <TabsTrigger value="document" className="relative">
                Документ
                {hasDocumentChanges && (
                  <span className="absolute -top-1 -right-1 text-amber-500 text-xl font-bold leading-none">
                    *
                  </span>
                )}
              </TabsTrigger>
            </TabsList>

            {/* ═══════════════════════════════════════ */}
            {/* ВКЛАДКА 1: РЕКВИЗИТЫ */}
            {/* ═══════════════════════════════════════ */}
            <TabsContent value="main" className="space-y-4 mt-2">
              {/* Название (обязательное) */}
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Название региона <span className="text-destructive">*</span>
                </label>
                <Controller
                  name="name"
                  control={control}
                  render={({ field }) => (
                    <Input
                      {...field}
                      placeholder="Например: Сибирь"
                      disabled={readOnly}
                    />
                  )}
                />
                {errors.name && (
                  <p className="text-xs text-destructive">{errors.name.message}</p>
                )}
              </div>

              {/* Административный центр */}
              <div className="space-y-2">
                <label className="text-sm font-medium">
                  Административный центр
                </label>
                <Controller
                  name="capital"
                  control={control}
                  render={({ field }) => (
                    <Input
                      {...field}
                      placeholder="Например: Новосибирск"
                      disabled={readOnly}
                    />
                  )}
                />
                {errors.capital && (
                  <p className="text-xs text-destructive">
                    {errors.capital.message}
                  </p>
                )}
              </div>

              {/* Код и Область в две колонки */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Код региона</label>
                  <Controller
                    name="code"
                    control={control}
                    render={({ field }) => (
                      <Input
                        {...field}
                        placeholder="Например: RU-SIB"
                        disabled={readOnly}
                      />
                    )}
                  />
                  {errors.code && (
                    <p className="text-xs text-destructive">
                      {errors.code.message}
                    </p>
                  )}
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Область / округ</label>
                  <Controller
                    name="area"
                    control={control}
                    render={({ field }) => (
                      <Input
                        {...field}
                        placeholder="Например: Сибирский ФО"
                        disabled={readOnly}
                      />
                    )}
                  />
                  {errors.area && (
                    <p className="text-xs text-destructive">
                      {errors.area.message}
                    </p>
                  )}
                </div>
              </div>
            </TabsContent>

            {/* ═══════════════════════════════════════ */}
            {/* ВКЛАДКА 2: ДОКУМЕНТ (поля контракта) */}
            {/* ═══════════════════════════════════════ */}
            <TabsContent value="document" className="space-y-4 mt-2">
              {/* Раздел доступа: только чтение, фиксирован */}
              <div className="space-y-2">
                <label className="text-sm font-medium">Раздел доступа</label>
                <div className="px-3 py-2 rounded-md border bg-muted/50 text-sm">
                  {COMMON_SECTION_NAME}
                </div>
                <p className="text-xs text-muted-foreground">
                  Раздел фиксирован: регионы видны всем организациям (ТЗ §4.3)
                </p>
              </div>

              {/* Номер и дата документа в две колонки */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Номер документа</label>
                  <Controller
                    name="doc_number"
                    control={control}
                    render={({ field }) => (
                      <Input
                        {...field}
                        placeholder="Например: РГН-001"
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
              </div>
            </TabsContent>
          </Tabs>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              className="min-w-24"
              onClick={() => handleOpenChange(false)}
            >
              {/* ✅ Спецификация: actions.cancel.label_rules */}
              {readOnly ? "Закрыть" : "Отмена"}
            </Button>

            {/* ✅ Спецификация: actions.save.hidden_when = read_only */}
            {!readOnly && (
              <Button
                type="submit"
                form="region-form"
                disabled={
                  isSubmitting ||
                  createMutation.isPending ||
                  updateMutation.isPending ||
                  // ✅ Спецификация: disabled_when = "mode == 'edit' and not has_any_changes"
                  // В режиме копирования кнопка активна всегда
                  (isEdit && !hasAnyChanges)
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