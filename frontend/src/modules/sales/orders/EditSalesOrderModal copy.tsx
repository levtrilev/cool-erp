// import { useState, useMemo, useEffect } from "react";
// import {
//   useCreateSalesOrderSalesOrdersPost,
//   useUpdateSalesOrderSalesOrdersOrderIdPut,
// } from "@/api/generated/sales-orders/sales-orders";
// import {
//   SalesOrderResponseSchema,
//   SalesOrderCreateSchemaDocStatus,
//   SalesOrderUpdateSchemaDocStatus,
// } from "@/api/generated/coolERP.schemas";
// import { DocumentFormShell } from "@/lib/document-form/DocumentFormShell";
// import { useDocumentSave } from "@/lib/document-form/useDocumentSave";
// import { mapEnumByValue } from "@/lib/document-form/documentFormHelpers";
// import { FormTabs, FormTabPanel } from "@/lib/form-blocks/FormTabs";
// import { SalesOrderMainTab } from "@/modules/sales/orders/SalesOrderMainTab";
// import { SalesOrderDeliveryTab } from "@/modules/sales/orders/SalesOrderDeliveryTab";
// import {
//   salesOrderFormSchema,
//   SALES_ORDER_CREATE_DEFAULTS,
//   type SalesOrderFormData,
//   type OrderLineFormData,
// } from "./schemas";

// interface EditSalesOrderModalProps {
//   open: boolean;
//   onOpenChange: (open: boolean) => void;
//   initialData: SalesOrderResponseSchema | null;
//   onSaved: (id: string, docNumber?: string) => Promise<void>;
//   readOnly?: boolean;
//   readOnlyReason?: string;
//   copyFromOrder?: SalesOrderResponseSchema | null;
// }

// /** Модалка редактирования заказа продажи (каркас + вкладки). */
// export const EditSalesOrderModal = ({
//   open,
//   onOpenChange,
//   initialData,
//   onSaved,
//   readOnly = false,
//   readOnlyReason,
//   copyFromOrder = null,
// }: EditSalesOrderModalProps) => {
//   const createMutation = useCreateSalesOrderSalesOrdersPost();
//   const updateMutation = useUpdateSalesOrderSalesOrdersOrderIdPut();

//   // Черновик строк спецификации (Правило №46)
//   const [orderLinesDraft, setOrderLinesDraft] = useState<OrderLineFormData[]>([]);

//   const docForm = useDocumentSave<
//     SalesOrderFormData,
//     SalesOrderResponseSchema,
//     Parameters<typeof createMutation.mutateAsync>[0]["data"],
//     Parameters<typeof updateMutation.mutateAsync>[0]["data"]
//   >({
//     entityLabel: "заказ",
//     formSchema: salesOrderFormSchema,
//     createDefaults: SALES_ORDER_CREATE_DEFAULTS,
//     initialData,
//     copySource: copyFromOrder,
//     readOnly,
//     open,
//     onOpenChange,
//     onSaved,
//     queryKey: ["sales-orders"],
//     formId: "sales-order-form",
//     createStatusEnum: SalesOrderCreateSchemaDocStatus,
//     buildEditDefaults: (source, isCopy, defaults) => ({
//       ...defaults,
//       section_id: source.section_id,
//       doc_status: isCopy
//         ? SalesOrderUpdateSchemaDocStatus.draft
//         : (source.doc_status as SalesOrderUpdateSchemaDocStatus),
//       doc_number: isCopy ? "" : (source.doc_number ?? ""),
//       doc_date: isCopy ? "" : (source.doc_date ?? ""),
//       supplier_id: source.supplier_id,
//       customer_id: source.customer_id,
//       contact: source.contact,
//       manager_id: source.manager_id,
//       delivery_due_date: source.delivery_due_date,
//       payment_scheme: source.payment_scheme ?? "",
//       currency_id: source.currency_id,
//       delivery_address: source.delivery_address ?? "",
//       delivery_method: source.delivery_method ?? "",
//     }),

//     buildCreatePayload: (formData) => ({
//       section_id: formData.section_id,
//       doc_status: mapEnumByValue(formData.doc_status, SalesOrderCreateSchemaDocStatus),
//       doc_number: formData.doc_number || null,
//       doc_date: formData.doc_date || null,
//       supplier_id: formData.supplier_id,
//       customer_id: formData.customer_id,
//       contact: formData.contact,
//       manager_id: formData.manager_id,
//       delivery_due_date: formData.delivery_due_date,
//       payment_scheme: formData.payment_scheme || null,
//       currency_id: formData.currency_id,
//       delivery_address: formData.delivery_address || null,
//       delivery_method: formData.delivery_method || null,
//       lines: orderLinesDraft.filter((l) => !l.markedForDeletion).map((l) => ({
//         line_no: l.line_no,
//         goods_id: l.goods_id,
//         quantity: l.quantity,
//         price_with_vat: l.price_with_vat,
//         discount_percent: l.discount_percent ?? 0,
//         vat_rate_percent: l.vat_rate_percent,
//       })),
//     }),

//     buildUpdatePayload: (formData, source) => ({
//       section_id: formData.section_id,
//       doc_status: formData.doc_status,
//       doc_number: formData.doc_number || null,
//       doc_date: formData.doc_date || null,
//       supplier_id: formData.supplier_id,
//       customer_id: formData.customer_id,
//       contact: formData.contact,
//       manager_id: formData.manager_id,
//       delivery_due_date: formData.delivery_due_date,
//       payment_scheme: formData.payment_scheme || null,
//       currency_id: formData.currency_id,
//       delivery_address: formData.delivery_address || null,
//       delivery_method: formData.delivery_method || null,
//       version: source.version ?? 0,
//       lines: orderLinesDraft.filter((l) => !l.markedForDeletion).map((l) => ({
//         id: l.id,
//         line_no: l.line_no,
//         goods_id: l.goods_id,
//         quantity: l.quantity,
//         price_with_vat: l.price_with_vat,
//         discount_percent: l.discount_percent ?? 0,
//         vat_rate_percent: l.vat_rate_percent,
//       })),
//     }),

//     callCreate: (payload) => createMutation.mutateAsync({ data: payload }),
//     callUpdate: (id, payload) => updateMutation.mutateAsync({ orderId: id, data: payload }),

//     getEntityId: (entity) => entity.id,
//     getEntityName: (entity) => entity.doc_number ?? undefined,
//     getEntityVersion: (entity) => entity.version,
//   });

//   // Инициализация черновика строк при открытии (Правило №38)
//   useEffect(() => {
//     if (open && initialData?.lines) {
//       // eslint-disable-next-line react-hooks/set-state-in-effect
//       setOrderLinesDraft(
//         initialData.lines.map((line) => ({
//           id: line.id,
//           line_no: line.line_no,
//           goods_id: line.goods_id,
//           quantity: Number(line.quantity),
//           price_with_vat: Number(line.price_with_vat),
//           discount_percent: Number(line.discount_percent),
//           vat_rate_percent: Number(line.vat_rate_percent),
//           markedForDeletion: false,
//         }))
//       );
//     } else if (open) {
//       setOrderLinesDraft([]);
//     }
//   }, [open, initialData]);

//   // Вычисление суммы заказа из черновика строк
//   const totalAmount = useMemo(() => {
//     let total = 0;
//     for (const line of orderLinesDraft) {
//       if (line.markedForDeletion) continue;
//       const lineTotal = line.quantity * line.price_with_vat;
//       const amountWithDisc = lineTotal * (1 - (line.discount_percent ?? 0) / 100);
//       total += amountWithDisc;
//     }
//     return total;
//   }, [orderLinesDraft]);

//   return (
//     <DocumentFormShell
//       docForm={docForm}
//       open={open}
//       titleCreate="Новый заказ продажи"
//       titleEdit={`Редактировать заказ: ${initialData?.doc_number ?? ""}`}
//       titleView="Просмотр заказа (только чтение)"
//       readOnlyReason={readOnlyReason}
//       version={initialData?.version}
//       isEditingLocked={initialData?.is_editing_locked}
//       sectionName={(initialData as (SalesOrderResponseSchema & { section_name?: string }) | null)?.section_name}
//       visibility={{ hideTags: true }}
//     >
//       <FormTabs defaultValue="main">
//         <FormTabPanel value="main" label="Заказ">
//           <SalesOrderMainTab
//             control={docForm.control}
//             errors={docForm.errors}
//             readOnly={readOnly}
//             initialData={initialData}
//             orderLinesDraft={orderLinesDraft}
//             setOrderLinesDraft={setOrderLinesDraft}
//             totalAmount={totalAmount}
//           />
//         </FormTabPanel>
//         <FormTabPanel value="delivery" label="Доставка">
//           <SalesOrderDeliveryTab
//             control={docForm.control}
//             errors={docForm.errors}
//             readOnly={readOnly}
//           />
//         </FormTabPanel>
//       </FormTabs>
//     </DocumentFormShell>
//   );
// };