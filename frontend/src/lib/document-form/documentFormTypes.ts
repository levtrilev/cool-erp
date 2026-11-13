import { BaseSyntheticEvent } from "react";
import type { Control, FieldErrors } from "react-hook-form";

/**
 * Базовые значения формы документа (поля миксинов, ТЗ §3.3 + жизненный цикл).
 * Бизнес-форма расширяет этот интерфейс своими полями.
 *
 * @template TDocStatus — номинальный enum статуса конкретной сущности
 *                        (например, NoteUpdateSchemaDocStatus).
 */
export interface DocumentBaseFormValues<TDocStatus extends string = string> {
  section_id: string;
  doc_status: TDocStatus;
  doc_number?: string;
  doc_date?: string;
  or_tags?: string[];
  and_tags?: string[];
}

/**
 * Контракт ответа мутации сохранения. Совместим с Orval-обёрткой
 * `ApiResponse<T>`, где `data` — сохранённая сущность.
 */
export interface DocumentSaveResponse {
  data?: { id: string; [key: string]: unknown } | null;
}

/**
 * Состояние формы документа, возвращаемое хуком `useDocumentSave`.
 * Передаётся в `DocumentFormShell` и используется бизнес-полями.
 */
export interface DocumentFormState<TFormData extends DocumentBaseFormValues<string>> {
  control: Control<TFormData>;
  errors: FieldErrors<TFormData>;
  handleSubmit: (e?: BaseSyntheticEvent) => Promise<unknown>;  
  isSaving: boolean;
  isEdit: boolean;
  isCopy: boolean;
  readOnly: boolean;
  formId: string;
  handleOpenChange: (nextOpen: boolean) => void;
}

/**
 * Пропсы-переключатели видимости типовых полей (Решение 3).
 * По умолчанию все поля видны.
 */
export interface DocumentFieldVisibility {
  hideDocNumber?: boolean;
  hideDocDate?: boolean;
  hideTags?: boolean;
}

import type { DefaultValues, FieldValues } from "react-hook-form";
import type { z } from "zod";

// /**
//  * Конфигурация хука `useDocumentSave`.
//  *
//  * Определяет полный контракт между бизнес-кодом и каркасом документа:
//  * схема формы, дефолты, мутации, сборка payload, извлечение полей ответа.
//  *
//  * @template TFormData — тип значений формы (расширяет `DocumentBaseFormValues` и `FieldValues`)
//  * @template TResponse — тип сущности из ответа мутации (например, `NoteResponseSchema`)
//  * @template TCreatePayload — тип полезной нагрузки для мутации создания
//  * @template TUpdatePayload — тип полезной нагрузки для мутации обновления
//  */
export interface UseDocumentSaveConfig<
  TFormData extends DocumentBaseFormValues<string> & FieldValues,
  TResponse,
  TCreatePayload,
  TUpdatePayload,
> {
  /** Название сущности для заголовков: "заметка", "счёт" и т.д. */
  entityLabel: string;

  /** Zod-схема формы. */
  formSchema: z.ZodType<TFormData>;

  /** Дефолты для режима создания (Правило №20). */
  createDefaults: DefaultValues<TFormData>;

  /** Редактируемая сущность (null для создания/копирования). */
  initialData: TResponse | null;

  /** Исходная сущность для копирования (null для создания/редактирования). */
  copySource: TResponse | null;

  /** Режим только чтения. */
  readOnly: boolean;

  /** Открыта ли модалка. */
  open: boolean;

  /** Колбэк изменения состояния открытия. */
  onOpenChange: (nextOpen: boolean) => void;

  /** Колбэк после успешного сохранения. */
  onSaved: (id: string, name?: string) => Promise<void>;

  /** Ключ инвалидации кэша списка (Правило №24). */
  queryKey: readonly string[];

  /** Enum статуса для схемы создания (маппинг Update → Create). */
  createStatusEnum: Record<string, string>;

  /**
   * Сборка полных дефолтов формы из исходной сущности.
   * Бизнес-код копирует свои поля (title, content и т.д.)
   * и трансформирует их при копировании.
   */
  buildEditDefaults: (
    source: TResponse,
    isCopy: boolean,
    defaults: TFormData,
  ) => TFormData;

  /** Сборка полезной нагрузки для создания (без version). */
  buildCreatePayload: (formData: TFormData) => TCreatePayload;

  /** Сборка полезной нагрузки для обновления (с version). */
  buildUpdatePayload: (
    formData: TFormData,
    initialData: TResponse,
  ) => TUpdatePayload;

  /** Вызов мутации создания. */
  callCreate: (payload: TCreatePayload) => Promise<DocumentSaveResponse>;

  /** Вызов мутации обновления. */
  callUpdate: (
    id: string,
    payload: TUpdatePayload,
  ) => Promise<DocumentSaveResponse>;

  /** Извлечение ID сущности из ответа мутации. */
  getEntityId: (response: TResponse) => string;

  /** Извлечение имени сущности из ответа мутации. */
  getEntityName: (response: TResponse) => string | undefined;

  /** Извлечение версии сущности из ответа мутации. */
  getEntityVersion: (response: TResponse) => number | undefined;

  /** Трансформация имени при копировании: "(копия)". */
  buildCopyTitle?: (source: TResponse) => string;

  /** Идентификатор формы для связи кнопки в футере с `<form>`. */
  formId: string;
}