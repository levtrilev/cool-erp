import { BaseSyntheticEvent, useCallback, useEffect, useMemo } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useToast } from "@/components/ui/use-toast";
import { z } from "zod";
import type {
  DocumentBaseFormValues,
  DocumentFormState,
} from "./documentFormTypes";
import { mapEnumByValue } from "./documentFormHelpers";
import type { FieldValues, DefaultValues } from "react-hook-form";
import type { Resolver } from "react-hook-form";
import type { $ZodTypeDef, $ZodTypeInternals } from "zod/v4/core";

/**
 * Создаёт Zod-резолвер для дженерик-формы документа.
 *
 * Инкапсулирует приведение типа, необходимое из-за инвариантности
 * входного типа (`_zod.input`) в сигнатуре `zodResolver` для Zod 4.
 * Ограничение `T extends FieldValues` гарантирует совместимость.
 */
function createDocumentResolver<T extends FieldValues>(
  schema: z.ZodType<T>,
): Resolver<T> {
  const zodSchema = schema as z.ZodType<
    FieldValues,
    $ZodTypeDef,
    $ZodTypeInternals<FieldValues, $ZodTypeDef>
  >;
  // Безопасное утверждение типа: ограничение `T extends FieldValues`
  // гарантирует совместимость резолвера с формой на этапе рантайма.
  // Двойной каст через `unknown` необходим, потому что типы
  // `Resolver<$ZodTypeDef, ...>` и `Resolver<T>` не имеют
  // достаточного перекрытия для прямого `as` (инвариантность
  // дженерик-параметров). Аналог `typing_cast` в Правиле №47 —
  // утверждение типа в точке интеграции двух библиотек.
  return zodResolver(zodSchema) as unknown as Resolver<T>;
}

/** Конфигурация хука сохранения документа. */
import type { UseDocumentSaveConfig } from "./documentFormTypes";

export function useDocumentSave<
  TFormData extends DocumentBaseFormValues<string> & FieldValues,
  TResponse,
  TCreatePayload,
  TUpdatePayload,
>(
  config: UseDocumentSaveConfig<
    TFormData,
    TResponse,
    TCreatePayload,
    TUpdatePayload
  >,
): DocumentFormState<TFormData> {
  const {
    formSchema,
    createDefaults,
    initialData,
    copySource,
    readOnly,
    open,
    onOpenChange,
    onSaved,
    queryKey,
    buildEditDefaults,
    buildCreatePayload,
    buildUpdatePayload,
    callCreate,
    callUpdate,
    getEntityId,
    getEntityName,
    getEntityVersion,
    formId,
  } = config;

  const { toast } = useToast();
  const queryClient = useQueryClient();

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<TFormData>({
    resolver: createDocumentResolver(formSchema),
    defaultValues: createDefaults as DefaultValues<TFormData>,
  });

  // Режимы работы формы.
  const isEdit = initialData !== null;
  const isCopy = copySource !== null && !isEdit;
  const sourceEntity = copySource ?? initialData ?? null;

  const isSaving = isSubmitting;

  // Синхронизация формы при открытии (Правило №37).
  // Для копирования: имя с суффиксом, без номера/даты, статус → draft.
  // useEffect(() => {
  //   if (!open) return;

  //   if (sourceEntity === null) {
  //     reset(createDefaults);
  //     return;
  //   }

  //   // Бизнес-код предоставит полные значения через `buildEditDefaults`
  //   const editDefaults = buildEditDefaults(
  //     sourceEntity as TResponse,
  //     isCopy,
  //     createDefaults as TFormData,
  //   );
  //   reset(editDefaults);
  //   // либо через расширение ниже. Здесь заполняем только типовые поля.
  //   const baseDefaults = {
  //     ...createDefaults,
  //     section_id: (sourceEntity as { section_id?: string }).section_id ?? "",
  //     doc_number: isCopy
  //       ? ""
  //       : ((sourceEntity as { doc_number?: string | null }).doc_number ?? ""),
  //     doc_date: isCopy
  //       ? ""
  //       : ((sourceEntity as { doc_date?: string | null }).doc_date ?? ""),
  //     or_tags: (sourceEntity as { or_tags?: string[] | null }).or_tags ?? [],
  //     and_tags: (sourceEntity as { and_tags?: string[] | null }).and_tags ?? [],
  //   } as Partial<TFormData>;

  //   reset(baseDefaults as TFormData);
  //   // eslint-disable-next-line react-hooks/exhaustive-deps
  // }, [open, sourceEntity, isCopy, reset]);
  useEffect(() => {
    if (!open) return;

    if (sourceEntity === null) {
      reset(createDefaults);
      return;
    }

    // ✅ Бизнес-код собирает полные дефолты, включая бизнес-поля
    // (title, content) с трансформацией при копировании.
    const editDefaults = buildEditDefaults(
      sourceEntity as TResponse,
      isCopy,
      createDefaults as TFormData,
    );
    reset(editDefaults);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, sourceEntity, isCopy, reset]);

  const handleOpenChange = useCallback(
    (nextOpen: boolean) => {
      if (!nextOpen) {
        reset(createDefaults);
      }
      onOpenChange(nextOpen);
    },
    [reset, createDefaults, onOpenChange],
  );

  const onSubmit = useCallback(
    async (formData: TFormData) => {
      if (readOnly) return;

      try {
        if (initialData !== null) {
          const version = getEntityVersion(initialData);
          if (version === undefined) {
            toast({
              variant: "destructive",
              title: "Ошибка",
              description: "Отсутствует версия документа",
            });
            return;
          }

          const payload = buildUpdatePayload(formData, initialData);
          const saved = await callUpdate(getEntityId(initialData), payload);

          // Строгий порядок (Правило №24):
          // 1. Инвалидация кэша
          await queryClient.invalidateQueries({ queryKey: [...queryKey] });
          // 2. Закрытие модалки
          handleOpenChange(false);
          // 3. Callback родителя
          const savedData = saved.data;
          if (savedData) {
            await onSaved(savedData.id, getEntityName(initialData));
          }
        } else {
          // При создании маппим статус из Update-контракта в Create-контракт.
          const payload = buildCreatePayload(formData);
          const saved = await callCreate(payload);

          await queryClient.invalidateQueries({ queryKey: [...queryKey] });
          handleOpenChange(false);

          const savedData = saved.data;
          if (savedData) {
            // ✅ При создании имя берём из ответа сервера (savedData),
            // а не из sourceEntity, который === null в этом режиме.
            await onSaved(savedData.id, getEntityName(savedData as TResponse));
          }
        }
      } catch (error: unknown) {
        let message = `Не удалось сохранить: ${config.entityLabel}`;
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
    },
    [
      readOnly,
      initialData,
      // sourceEntity,
      buildCreatePayload,
      buildUpdatePayload,
      callCreate,
      callUpdate,
      getEntityId,
      getEntityName,
      getEntityVersion,
      queryClient,
      queryKey,
      handleOpenChange,
      onSaved,
      toast,
      config.entityLabel,
    ],
  );

  return useMemo(
    () => ({
      control,
      errors,
      handleSubmit: handleSubmit(onSubmit) as (
        e?: BaseSyntheticEvent,
      ) => Promise<unknown>,
      isSaving,
      isEdit,
      isCopy,
      readOnly,
      formId,
      handleOpenChange,
    }),
    [
      control,
      errors,
      handleSubmit,
      onSubmit,
      isSaving,
      isEdit,
      isCopy,
      readOnly,
      formId,
      handleOpenChange,
    ],
  );
}

/**
 * Вспомогательная функция для сборки `buildCreatePayload` с маппингом статуса.
 * Вызывается бизнес-кодом внутри `buildCreatePayload`.
 */
export function mapStatusForCreate<TFrom extends string, TTo extends string>(
  status: TFrom,
  createStatusEnum: Record<string, TTo>,
): TTo {
  return mapEnumByValue(status, createStatusEnum);
}
