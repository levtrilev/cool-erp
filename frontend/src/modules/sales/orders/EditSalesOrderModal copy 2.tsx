// frontend/src/modules/sales/orders/EditSalesOrderModal.tsx
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  useCreateSalesOrderSalesOrdersPost,
  useUpdateSalesOrderSalesOrdersOrderIdPut,
} from "@/api/generated/sales-orders/sales-orders";
import {
  SalesOrderResponseSchema,
  SalesOrderCreateSchemaDocStatus,
  SalesOrderUpdateSchemaDocStatus,
} from "@/api/generated/coolERP.schemas";
import {
  DocumentFormShell,
  type DocumentDialogSize,
} from "@/lib/document-form/DocumentFormShell";
import { useDocumentSave } from "@/lib/document-form/useDocumentSave";
import { mapEnumByValue } from "@/lib/document-form/documentFormHelpers";
import { FormTabs, FormTabPanel } from "@/lib/form-blocks/FormTabs";
import { SalesOrderMainTab } from "@/modules/sales/orders/SalesOrderMainTab";
import { SalesOrderDeliveryTab } from "@/modules/sales/orders/SalesOrderDeliveryTab";
import {
  salesOrderFormSchema,
  SALES_ORDER_CREATE_DEFAULTS,
  type SalesOrderFormData,
  type OrderLineFormData,
} from "./schemas";

// Константа геометрии этого типа документа (вне компонента):
const SALES_ORDER_DIALOG_SIZE: DocumentDialogSize = {
  width: 1100, // широкая форма: таблица спецификации ~1040px + отступы
  minWidth: 760,
  minHeight: 480,
  maxWidth: "92vw",
  maxHeight: "90vh",
};

/** Строка спецификации, пришедшая с бэкенда (тип выводится из ответа заказа). */
type SalesOrderLineResponse = NonNullable<
  SalesOrderResponseSchema["lines"]
>[number];

/** Стабильная пустая ссылка: не создаёт новый массив на каждом рендере. */
const EMPTY_LINES: OrderLineFormData[] = [];

/**
 * Преобразование строки ответа в черновик формы.
 * При копировании id обнуляется — это новые записи (strip_ids_in: [lines]).
 * Номер строки сохраняется из источника: перенумерация существующих строк
 * недопустима — нарушит uq_sales_order_line_order_line_no при UPDATE.
 */
const toLineDraft = (
  line: SalesOrderLineResponse,
  stripId: boolean,
): OrderLineFormData => ({
  id: stripId ? undefined : line.id,
  line_no: line.line_no,
  goods_id: line.goods_id,
  quantity: Number(line.quantity),
  price_with_vat: Number(line.price_with_vat),
  discount_percent: Number(line.discount_percent),
  vat_rate_percent: Number(line.vat_rate_percent),
  markedForDeletion: false,
});

interface EditSalesOrderModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData: SalesOrderResponseSchema | null;
  onSaved: (id: string, docNumber?: string) => Promise<void>;
  readOnly?: boolean;
  readOnlyReason?: string;
  copyFromOrder?: SalesOrderResponseSchema | null;
}

/** Модалка создания / редактирования / копирования заказа продажи. */
export const EditSalesOrderModal = ({
  open,
  onOpenChange,
  initialData,
  onSaved,
  readOnly = false,
  readOnlyReason,
  copyFromOrder = null,
}: EditSalesOrderModalProps) => {
  const createMutation = useCreateSalesOrderSalesOrdersPost();
  const updateMutation = useUpdateSalesOrderSalesOrdersOrderIdPut();

  // ✅ Единый источник истины для префилла: копирование ИЛИ редактирование
  const isCopy: boolean = copyFromOrder !== null && initialData === null;
  const sourceOrder: SalesOrderResponseSchema | null =
    copyFromOrder ?? initialData ?? null;

  const copyTitle: string = copyFromOrder?.doc_number
    ? `Копирование заказа: ${copyFromOrder.doc_number}`
    : "Копирование заказа";

  // ── Черновик строк спецификации (Правило №46) ────────────────────
  const [orderLinesDraft, setOrderLinesDraft] =
    useState<OrderLineFormData[]>(EMPTY_LINES);

  // Ключ инициализации учитывает режим: одна и та же сущность в edit и copy —
  // разные черновики (в copy id строк обнуляются).
  const linesInitKey: string =
    sourceOrder === null
      ? "create"
      : `${isCopy ? "copy" : "edit"}:${sourceOrder.id}`;

  const lastInitializedLinesKey = useRef<string | null>(null);

  const initialLinesDraft: OrderLineFormData[] = useMemo(() => {
    const sourceLines: SalesOrderLineResponse[] = sourceOrder?.lines ?? [];
    return sourceLines.map((line) => toLineDraft(line, isCopy));
  }, [sourceOrder, isCopy]);

  // ✅ Инициализация от sourceOrder, а не от initialData (Правило №38).
  // Строки приходят вместе с сущностью — отдельной загрузки нет,
  // поэтому гейт isLoading не требуется; защита — по ключу в useRef.
  useEffect(() => {
    if (!open) {
      lastInitializedLinesKey.current = null;
      return;
    }
    if (lastInitializedLinesKey.current === linesInitKey) return;
    lastInitializedLinesKey.current = linesInitKey;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setOrderLinesDraft(initialLinesDraft);
  }, [open, linesInitKey, initialLinesDraft]);

  // ✅ Сброс черновика в обработчике события, не в useEffect (Правило №46, п. 4.5)
  const handleOpenChange = useCallback(
    (nextOpen: boolean): void => {
      if (!nextOpen) {
        lastInitializedLinesKey.current = null;
        setOrderLinesDraft(EMPTY_LINES);
      }
      onOpenChange(nextOpen);
    },
    [onOpenChange],
  );

  const docForm = useDocumentSave<
    SalesOrderFormData,
    SalesOrderResponseSchema,
    Parameters<typeof createMutation.mutateAsync>[0]["data"],
    Parameters<typeof updateMutation.mutateAsync>[0]["data"]
  >({
    entityLabel: "заказ",
    formSchema: salesOrderFormSchema,
    createDefaults: SALES_ORDER_CREATE_DEFAULTS,
    initialData,
    copySource: copyFromOrder,
    readOnly,
    open,
    onOpenChange: handleOpenChange,
    onSaved,
    queryKey: ["sales-orders"],
    formId: "sales-order-form",
    createStatusEnum: SalesOrderCreateSchemaDocStatus,
    buildEditDefaults: (source, isCopyMode, defaults) => ({
      ...defaults,
      section_id: source.section_id,
      doc_status: isCopyMode
        ? SalesOrderUpdateSchemaDocStatus.draft
        : (source.doc_status as SalesOrderUpdateSchemaDocStatus),
      doc_number: isCopyMode ? "" : (source.doc_number ?? ""),
      doc_date: isCopyMode ? "" : (source.doc_date ?? ""),
      supplier_id: source.supplier_id,
      customer_id: source.customer_id,
      contact: source.contact,
      manager_id: source.manager_id,
      delivery_due_date: source.delivery_due_date,
      payment_scheme: source.payment_scheme ?? "",
      currency_id: source.currency_id,
      delivery_address: source.delivery_address ?? "",
      delivery_method: source.delivery_method ?? "",
    }),
    buildCreatePayload: (formData) => ({
      section_id: formData.section_id,
      doc_status: mapEnumByValue(
        formData.doc_status,
        SalesOrderCreateSchemaDocStatus,
      ),
      doc_number: formData.doc_number || null,
      doc_date: formData.doc_date || null,
      supplier_id: formData.supplier_id,
      customer_id: formData.customer_id,
      contact: formData.contact,
      manager_id: formData.manager_id,
      delivery_due_date: formData.delivery_due_date,
      payment_scheme: formData.payment_scheme || null,
      currency_id: formData.currency_id,
      delivery_address: formData.delivery_address || null,
      delivery_method: formData.delivery_method || null,
      // ✅ Копия создаётся мутацией создания — строки уходят вместе с заказом
      lines: orderLinesDraft
        .filter((line) => !line.markedForDeletion)
        .map((line) => ({
          line_no: line.line_no,
          goods_id: line.goods_id,
          quantity: line.quantity,
          price_with_vat: line.price_with_vat,
          discount_percent: line.discount_percent ?? 0,
          vat_rate_percent: line.vat_rate_percent,
        })),
    }),
    buildUpdatePayload: (formData, source) => ({
      section_id: formData.section_id,
      doc_status: formData.doc_status,
      doc_number: formData.doc_number || null,
      doc_date: formData.doc_date || null,
      supplier_id: formData.supplier_id,
      customer_id: formData.customer_id,
      contact: formData.contact,
      manager_id: formData.manager_id,
      delivery_due_date: formData.delivery_due_date,
      payment_scheme: formData.payment_scheme || null,
      currency_id: formData.currency_id,
      delivery_address: formData.delivery_address || null,
      delivery_method: formData.delivery_method || null,
      version: source.version ?? 0,
      // ✅ undefined → ключ не сериализуется → бэкенд не трогает спецификацию.
      // Пустой [] отправляется только осознанно (черновик инициализирован).
      lines:
        lastInitializedLinesKey.current === null
          ? undefined
          : orderLinesDraft
              .filter((line) => !line.markedForDeletion)
              .map((line) => ({
                id: line.id,
                line_no: line.line_no,
                goods_id: line.goods_id,
                quantity: line.quantity,
                price_with_vat: line.price_with_vat,
                discount_percent: line.discount_percent ?? 0,
                vat_rate_percent: line.vat_rate_percent,
              })),
    }),
    callCreate: (payload) => createMutation.mutateAsync({ data: payload }),
    callUpdate: (id, payload) =>
      updateMutation.mutateAsync({ orderId: id, data: payload }),
    getEntityId: (entity) => entity.id,
    getEntityName: (entity) => entity.doc_number ?? undefined,
    getEntityVersion: (entity) => entity.version,
  });

  // Сумма заказа из черновика строк
  const totalAmount: number = useMemo(() => {
    let total = 0;
    for (const line of orderLinesDraft) {
      if (line.markedForDeletion) continue;
      const lineTotal = line.quantity * line.price_with_vat;
      total += lineTotal * (1 - (line.discount_percent ?? 0) / 100);
    }
    return total;
  }, [orderLinesDraft]);

  return (
    <DocumentFormShell
      docForm={docForm}
      open={open}
      dialogSize={SALES_ORDER_DIALOG_SIZE}
      titleCreate={isCopy ? copyTitle : "Новый заказ продажи"}
      titleEdit={
        isCopy
          ? copyTitle
          : `Редактировать заказ: ${initialData?.doc_number ?? ""}`
      }
      titleView="Просмотр заказа (только чтение)"
      readOnlyReason={readOnlyReason}
      version={initialData?.version}
      isEditingLocked={initialData?.is_editing_locked}
      sectionName={
        (
          sourceOrder as
            | (SalesOrderResponseSchema & { section_name?: string })
            | null
        )?.section_name
      }
      visibility={{ hideTags: true }}
    >
      <FormTabs defaultValue="main">
        <FormTabPanel value="main" label="Заказ">
          <SalesOrderMainTab
            control={docForm.control}
            errors={docForm.errors}
            readOnly={readOnly}
            initialData={sourceOrder}
            orderLinesDraft={orderLinesDraft}
            setOrderLinesDraft={setOrderLinesDraft}
            totalAmount={totalAmount}
          />
        </FormTabPanel>
        <FormTabPanel value="delivery" label="Доставка">
          <SalesOrderDeliveryTab
            control={docForm.control}
            errors={docForm.errors}
            readOnly={readOnly}
          />
        </FormTabPanel>
      </FormTabs>
    </DocumentFormShell>
  );
};
