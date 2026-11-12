// frontend/src/lib/document-form/DocumentFormShell.tsx
import {
  useState,
  useRef,
  useCallback,
  type ReactNode,
  type CSSProperties,
} from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import { Controller, useFormState, type Path } from "react-hook-form";
import {
  Loader2,
  AlertCircle,
  AlertTriangle,
  Lock as LockIcon,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { ReferenceSelect } from "@/lib/reusable/ReferenceSelect";
import { getSectionsSectionsGet } from "@/api/generated/sections/sections";
import type {
  DocumentBaseFormValues,
  DocumentFieldVisibility,
  DocumentFormState,
} from "./documentFormTypes";
import { DOC_STATUS_LABELS, parseTags, joinTags } from "./documentFormHelpers";

/**
 * Геометрия окна документа (секция `dialog` задания cool-erp-form v1.2).
 * Задаётся в КОНКРЕТНОЙ модалке документа: каждый тип документа
 * определяет собственные размеры. Шаблон размеров не хранит.
 */
export interface DocumentDialogSize {
  /** Начальная ширина окна, px. */
  width: number;
  /** Начальная высота; по умолчанию — по содержимому. */
  height?: number | string;
  /** Минимальная ширина при ручном ресайзе, px. */
  minWidth?: number;
  /** Минимальная высота при ручном ресайзе, px. */
  minHeight?: number;
  /** Предел ширины (px или CSS-строка, например "92vw"). */
  maxWidth?: number | string;
  /** Предел высоты (px или CSS-строка, например "90vh"). */
  maxHeight?: number | string;
}

type DragOffset = { x: number; y: number };
type DragOrigin = { pointerX: number; pointerY: number; offset: DragOffset };

const INITIAL_DRAG_OFFSET: DragOffset = { x: 0, y: 0 };
const DRAG_MARGIN_PX = 8;

/**
 * Запрет закрытия по клику/фокусу вне окна.
 * Структурный тип совместим и с PointerDownOutsideEvent, и с InteractOutsideEvent,
 * поэтому не требует импорта типов из @radix-ui.
 * preventDefault() отменяет onDismiss у DismissableLayer (Radix).
 */
const preventOutsideDismiss = (event: { preventDefault: () => void }): void => {
  event.preventDefault();
};

const clampNumber = (value: number, min: number, max: number): number =>
  Math.min(Math.max(value, Math.min(min, max)), Math.max(min, max));

const clampDragOffset = (
  next: DragOffset,
  current: DragOffset,
  content: HTMLElement,
): DragOffset => {
  if (typeof window === "undefined") return next;
  const rect = content.getBoundingClientRect();
  const baseLeft = rect.left - current.x;
  const baseTop = rect.top - current.y;
  const maxLeft = window.innerWidth - DRAG_MARGIN_PX - rect.width;
  const maxTop = window.innerHeight - DRAG_MARGIN_PX - rect.height;
  return {
    x: clampNumber(next.x, DRAG_MARGIN_PX - baseLeft, maxLeft - baseLeft),
    y: clampNumber(next.y, DRAG_MARGIN_PX - baseTop, maxTop - baseTop),
  };
};

export interface DocumentFormShellProps<
  TFormData extends DocumentBaseFormValues<string>,
> {
  docForm: DocumentFormState<TFormData>;
  open: boolean;
  /** Заголовки для режимов. */
  titleCreate: string;
  titleEdit: string;
  titleView: string;
  readOnlyReason?: string;
  /** Версия и блокировка для отображения (из `initialData`). */
  version?: number;
  isEditingLocked?: boolean;
  /** Имя раздела для `selectedLabel` в ReferenceSelect (Правило №27, №42). */
  sectionName?: string;
  /** Видимость типовых полей (Решение 3). */
  visibility?: DocumentFieldVisibility;
  /**
   * Геометрия окна. Обязательна: размеры определяет конкретная
   * модалка документа, а не шаблон.
   */
  dialogSize: DocumentDialogSize;
  /**
   * Наличие несохранённых изменений ВО ВНЕШНИХ черновиках
   * (табличные части вне react-hook-form: спецификации, строки, позиции).
   * Объединяется по ИЛИ с `isDirty` самой формы.
   */
  hasDraftChanges?: boolean;
  /** Бизнес-поля рендерятся внутри формы перед типовыми полями. */
  children: ReactNode;
}

export function DocumentFormShell<
  TFormData extends DocumentBaseFormValues<string>,
>({
  docForm,
  open,
  titleCreate,
  titleEdit,
  titleView,
  readOnlyReason,
  version,
  isEditingLocked,
  sectionName,
  visibility,
  dialogSize,
  hasDraftChanges = false,
  children,
}: DocumentFormShellProps<TFormData>) {
  const {
    control,
    errors,
    isSaving,
    isEdit,
    readOnly,
    formId,
    handleOpenChange,
  } = docForm;

  const hideDocNumber = visibility?.hideDocNumber ?? false;
  const hideDocDate = visibility?.hideDocDate ?? false;
  const hideTags = visibility?.hideTags ?? false;

  // ✅ Реактивное чтение состояния формы (Правило №45/46: useFormState, не watch()).
  // isDirty сравнивает текущие значения с defaultValues, выставленными при reset().
  const { isDirty: isFormDirty } = useFormState({ control });

  // В режиме «только чтение» изменений быть не может — выход всегда свободный.
  const hasUnsavedChanges: boolean =
    !readOnly && (isFormDirty || hasDraftChanges);

  // Drag-состояние.
  const [dragOffset, setDragOffset] = useState<DragOffset>(INITIAL_DRAG_OFFSET);
  const [previousOpen, setPreviousOpen] = useState<boolean>(open);
  const dragOriginRef = useRef<DragOrigin | null>(null);
  const dragHandleRef = useRef<HTMLDivElement | null>(null);

  // Подтверждение выхода при несохранённых изменениях.
  const [confirmExitOpen, setConfirmExitOpen] = useState<boolean>(false);

  // Сброс позиции и диалога подтверждения при смене состояния окна.
  if (open !== previousOpen) {
    setPreviousOpen(open);
    if (open) {
      setDragOffset(INITIAL_DRAG_OFFSET);
    }
    setConfirmExitOpen(false);
  }

  /**
   * Единая точка выхода из окна.
   * Вызывается из кнопок «Отмена»/«Закрыть», крестика Radix и Escape.
   * Клик вне окна сюда не доходит — он заблокирован на уровне DialogContent.
   */
  const requestClose = useCallback((): void => {
    // Во время сохранения окно не закрываем: мутация должна завершиться.
    if (isSaving) return;
    if (hasUnsavedChanges) {
      setConfirmExitOpen(true);
      return;
    }
    handleOpenChange(false);
  }, [isSaving, hasUnsavedChanges, handleOpenChange]);

  /** Перехват onOpenChange Radix: сюда приходят Escape и встроенный крестик. */
  const handleDialogOpenChange = useCallback(
    (nextOpen: boolean): void => {
      if (nextOpen) {
        handleOpenChange(true);
        return;
      }
      requestClose();
    },
    [handleOpenChange, requestClose],
  );

  /** «Закрыть без сохранения» — выход подтверждён, освобождаем блокировку. */
  const handleConfirmExit = useCallback((): void => {
    setConfirmExitOpen(false);
    handleOpenChange(false);
  }, [handleOpenChange]);

  const getContentElement = (): HTMLElement | null => {
    const handle = dragHandleRef.current;
    if (!handle) return null;
    const content = handle.closest('[data-slot="dialog-content"]');
    return content instanceof HTMLElement ? content : null;
  };

  const handleDragPointerDown = (
    event: ReactPointerEvent<HTMLDivElement>,
  ): void => {
    if (event.button !== 0) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    dragOriginRef.current = {
      pointerX: event.clientX,
      pointerY: event.clientY,
      offset: dragOffset,
    };
  };

  const handleDragPointerMove = (
    event: ReactPointerEvent<HTMLDivElement>,
  ): void => {
    const origin = dragOriginRef.current;
    if (!origin) return;
    const next: DragOffset = {
      x: origin.offset.x + (event.clientX - origin.pointerX),
      y: origin.offset.y + (event.clientY - origin.pointerY),
    };
    const content = getContentElement();
    if (!content) {
      setDragOffset(next);
      return;
    }
    setDragOffset((current) => clampDragOffset(next, current, content));
  };

  const handleDragPointerEnd = (
    event: ReactPointerEvent<HTMLDivElement>,
  ): void => {
    dragOriginRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  // Все размеры — из конкретной модалки. В шаблоне только структурное
  // поведение окна: ресайз, прокрутка, высота по содержимому и drag-смещение.
  const dialogStyle: CSSProperties = {
    resize: "both",
    overflow: "auto",
    width: dialogSize.width,
    height: dialogSize.height ?? "auto",
    minWidth: dialogSize.minWidth,
    minHeight: dialogSize.minHeight,
    // "none" снимает библиотечный max-w-lg у DialogContent,
    // чтобы ширина из модалки применялась без скрытого ограничения.
    maxWidth: dialogSize.maxWidth ?? "none",
    maxHeight: dialogSize.maxHeight,
    translate: `${dragOffset.x}px ${dragOffset.y}px`,
  };

  const title = readOnly ? titleView : isEdit ? titleEdit : titleCreate;

  return (
    <>
      <Dialog open={open} onOpenChange={handleDialogOpenChange}>
        <DialogContent
          className="items-start pt-8"
          style={dialogStyle}
          // ✅ Клик по overlay и уход фокуса наружу больше не закрывают окно.
          onPointerDownOutside={preventOutsideDismiss}
          onInteractOutside={preventOutsideDismiss}
        >
          <div
            ref={dragHandleRef}
            className="cursor-grab select-none touch-none active:cursor-grabbing"
            onPointerDown={handleDragPointerDown}
            onPointerMove={handleDragPointerMove}
            onPointerUp={handleDragPointerEnd}
            onPointerCancel={handleDragPointerEnd}
          >
            <DialogHeader>
              <DialogTitle>{title}</DialogTitle>
            </DialogHeader>
          </div>

          {readOnly && (
            <Alert
              variant="destructive"
              className="flex items-center gap-3 py-2.5"
            >
              {readOnlyReason?.includes(
                "редактируется другим пользователем",
              ) && <LockIcon className="h-4 w-4 shrink-0" />}
              {readOnlyReason?.includes("нет прав на изменение") && (
                <AlertCircle className="h-4 w-4 shrink-0" />
              )}
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
            onSubmit={docForm.handleSubmit}
            className="space-y-4"
            id={formId}
          >
            {children}

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>
                  Раздел <span className="text-destructive">*</span>
                </Label>
                <Controller
                  name={"section_id" as Path<TFormData>}
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
                      value={field.value as string}
                      onValueChange={field.onChange}
                      placeholder="Выберите раздел..."
                      selectedLabel={sectionName ?? "Выберите раздел..."}
                      heading="Разделы"
                      limit={50}
                      disabled={readOnly}
                    />
                  )}
                />
                {errors.section_id && (
                  <p className="text-xs text-destructive">
                    {errors.section_id.message as string}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor={`${formId}-doc_status`}>
                  Статус <span className="text-destructive">*</span>
                </Label>
                <Controller
                  name={"doc_status" as Path<TFormData>}
                  control={control}
                  render={({ field }) => (
                    <Select
                      value={field.value as string}
                      onValueChange={field.onChange}
                      disabled={readOnly}
                    >
                      <SelectTrigger
                        id={`${formId}-doc_status`}
                        className="w-full"
                      >
                        <SelectValue placeholder="Выберите статус" />
                      </SelectTrigger>
                      <SelectContent
                        position="popper"
                        sideOffset={4}
                        className="w-[var(--radix-select-trigger-width)] max-h-60"
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

            {(!hideDocNumber || !hideDocDate) && (
              <div className="grid grid-cols-2 gap-4">
                {!hideDocNumber && (
                  <div className="space-y-2">
                    <Label htmlFor={`${formId}-doc_number`}>
                      Номер документа
                    </Label>
                    <Controller
                      name={"doc_number" as Path<TFormData>}
                      control={control}
                      render={({ field }) => (
                        <Input
                          id={`${formId}-doc_number`}
                          {...field}
                          value={(field.value as string) ?? ""}
                          placeholder="Например: Н-001"
                          maxLength={64}
                          disabled={readOnly}
                        />
                      )}
                    />
                    {errors.doc_number && (
                      <p className="text-xs text-destructive">
                        {errors.doc_number.message as string}
                      </p>
                    )}
                  </div>
                )}
                {!hideDocDate && (
                  <div className="space-y-2">
                    <Label htmlFor={`${formId}-doc_date`}>Дата документа</Label>
                    <Controller
                      name={"doc_date" as Path<TFormData>}
                      control={control}
                      render={({ field }) => (
                        <Input
                          id={`${formId}-doc_date`}
                          type="date"
                          {...field}
                          value={(field.value as string) ?? ""}
                          disabled={readOnly}
                        />
                      )}
                    />
                  </div>
                )}
              </div>
            )}

            {!hideTags && (
              <>
                <div className="space-y-2">
                  <Label htmlFor={`${formId}-or_tags`}>
                    OR-теги{" "}
                    <span className="text-xs text-muted-foreground">
                      (через запятую, формат: пространство:значение)
                    </span>
                  </Label>
                  <Controller
                    name={"or_tags" as Path<TFormData>}
                    control={control}
                    render={({ field }) => (
                      <Input
                        id={`${formId}-or_tags`}
                        value={joinTags(field.value as string[] | undefined)}
                        onChange={(event) =>
                          field.onChange(parseTags(event.target.value))
                        }
                        placeholder="регион:сибирь, отдел:продажи"
                        disabled={readOnly}
                      />
                    )}
                  />
                  {errors.or_tags && (
                    <p className="text-xs text-destructive">
                      {errors.or_tags.message as string}
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor={`${formId}-and_tags`}>
                    AND-теги{" "}
                    <span className="text-xs text-muted-foreground">
                      (обязательный допуск, через запятую)
                    </span>
                  </Label>
                  <Controller
                    name={"and_tags" as Path<TFormData>}
                    control={control}
                    render={({ field }) => (
                      <Input
                        id={`${formId}-and_tags`}
                        value={joinTags(field.value as string[] | undefined)}
                        onChange={(event) =>
                          field.onChange(parseTags(event.target.value))
                        }
                        placeholder="гриф:секретно"
                        disabled={readOnly}
                      />
                    )}
                  />
                  {errors.and_tags && (
                    <p className="text-xs text-destructive">
                      {errors.and_tags.message as string}
                    </p>
                  )}
                </div>
              </>
            )}

            {isEdit && version !== undefined && (
              <p className="text-xs text-muted-foreground">
                Версия: {version}
                {isEditingLocked && " · 🔒 Заблокировано для редактирования"}
              </p>
            )}
          </form>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={requestClose}
              disabled={isSaving}
            >
              {readOnly ? "Закрыть" : "Отмена"}
            </Button>
            {!readOnly && (
              <Button type="submit" form={formId} disabled={isSaving}>
                {isSaving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isEdit ? "Сохранить" : "Создать"}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Подтверждение потери изменений.
          Кнопки — вертикально на всю ширину: длинные подписи помещаются
          при любой ширине диалога, текст переносится, высота по содержимому.
          Radix AlertDialog не закрывается по клику вне окна; Escape здесь
          закрывает только подтверждение = возврат к редактированию. */}
      <AlertDialog open={confirmExitOpen} onOpenChange={setConfirmExitOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 shrink-0 text-amber-500" />
              Несохранённые изменения
            </AlertDialogTitle>
            <AlertDialogDescription>
              В документе есть несохранённые изменения. Если закрыть окно
              сейчас, они будут потеряны. Вернуться к редактированию или закрыть
              без сохранения?
            </AlertDialogDescription>
          </AlertDialogHeader>

          {/* flex-col-reverse + w-full переопределяют библиотечный sm:flex-row
              и sm:space-x-2 через tailwind-merge: ряд не переполняется. */}
          <AlertDialogFooter className="flex-col-reverse gap-2 sm:flex-col-reverse sm:space-x-0">
            <AlertDialogCancel className="mt-0 h-auto min-h-9 w-full whitespace-normal py-2">
              Вернуться к редактированию
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmExit}
              className="h-auto min-h-9 w-full whitespace-normal py-2 bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Закрыть без сохранения
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
