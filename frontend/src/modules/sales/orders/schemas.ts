import { SalesOrderUpdateSchemaDocStatus } from "@/api/generated/coolERP.schemas";
import { z } from "zod";

/** Допустимые значения способа доставки. */
export const DELIVERY_METHODS = [
  "pickup",
  "own_transport",
  "third_party",
] as const;

export type DeliveryMethod = (typeof DELIVERY_METHODS)[number];

export const DELIVERY_METHOD_LABELS: Record<DeliveryMethod, string> = {
  pickup: "Самовывоз",
  own_transport: "Транспорт поставщика",
  third_party: "Транспортная компания",
};

/** Схема строки спецификации. */
export const orderLineSchema = z.object({
  id: z.string().optional(),
  line_no: z.number().int().min(1),
  goods_id: z.string().min(1, "Товар обязателен"),
  quantity: z.number().positive("Количество должно быть больше 0"),
  price_with_vat: z.number().min(0, "Цена не может быть отрицательной"),
  discount_percent: z.number().min(0).max(100).default(0),
  vat_rate_percent: z.number().min(0).max(100),
  markedForDeletion: z.boolean().optional(),
});

export type OrderLineFormData = z.infer<typeof orderLineSchema>;

/** Схема формы заказа продажи. */
export const salesOrderFormSchema = z.object({
  section_id: z.string().min(1, "Раздел обязателен"),
  doc_status: z.nativeEnum(SalesOrderUpdateSchemaDocStatus),
  doc_number: z.string().max(64).optional(),
  doc_date: z.string().min(1, "Дата документа обязательна"),
  supplier_id: z.string().min(1, "Поставщик обязателен"),
  customer_id: z.string().min(1, "Заказчик обязателен"),
  contact: z.string().min(1, "Контакт обязателен"),
  manager_id: z.string().min(1, "Менеджер обязателен"),
  delivery_due_date: z.string().min(1, "Дата исполнения обязательна"),
  payment_scheme: z.string().optional(),
  currency_id: z.string().min(1, "Валюта обязательна"),
  delivery_address: z.string().optional(),
  delivery_method: z.string().optional(),
});

export type SalesOrderFormData = z.infer<typeof salesOrderFormSchema>;

/** Дефолты для режима создания. */
export const SALES_ORDER_CREATE_DEFAULTS: SalesOrderFormData = {
  section_id: "",
  doc_status: SalesOrderUpdateSchemaDocStatus.draft,
  doc_number: "",
  doc_date: "",
  supplier_id: "",
  customer_id: "",
  contact: "",
  manager_id: "",
  delivery_due_date: "",
  payment_scheme: "",
  currency_id: "",
  delivery_address: "",
  delivery_method: "",
};

/** Метки статусов документа. */
export const DOC_STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  pending: "На утверждении",
  approved: "Утверждён",
  active: "Действует",
  archived: "Архив",
};