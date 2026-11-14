// frontend/src/modules/sales/item_types/EditItemTypeModal.tsx
import { Controller } from "react-hook-form";
import {
  useCreateSalesItemTypeSalesItemTypesPost,
  useUpdateSalesItemTypeSalesItemTypesItemTypeIdPut,
} from "@/api/generated/sales-item-types/sales-item-types";
import {
  SalesItemTypeResponseSchema,
  SalesItemTypeCreateSchemaDocStatus,
  SalesItemTypeUpdateSchemaDocStatus,
  SalesItemTypeCreateSchemaItemClass,
  SalesItemTypeUpdateSchemaItemClass,
} from "@/api/generated/coolERP.schemas";
import {
  useDocumentSave,
  mapStatusForCreate,
} from "@/lib/document-form/useDocumentSave";
import {
  DocumentFormShell,
  type DocumentDialogSize,
} from "@/lib/document-form/DocumentFormShell";
import {
  mapEnumByValue,
  joinTags,
  parseTags,
} from "@/lib/document-form/documentFormHelpers";
import { FormTabs, FormTabPanel } from "@/lib/form-blocks/FormTabs";
import { FormSection } from "@/lib/form-blocks/FormSection";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ItemTypeCustomFields } from "./ItemTypeCustomFields";
import {
  itemTypeFormSchema,
  CREATE_DEFAULTS,
  type ItemTypeFormData,
} from "./schemas";

/** Геометрия окна определяется конкретной модалкой (не шаблоном). */
const ITEM_TYPE_DIALOG_SIZE: DocumentDialogSize = {
  width: 860,
  minWidth: 640,
  minHeight: 520,
  maxWidth: "92vw",
  maxHeight: "90vh",
};

interface EditItemTypeModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData: SalesItemTypeResponseSchema | null;
  onSaved: (id: string, name?: string) => Promise<void>;
  readOnly?: boolean;
  readOnlyReason?: string;
  copyFromItemType?: SalesItemTypeResponseSchema | null;
}

export const EditItemTypeModal = ({
  open,
  onOpenChange,
  initialData,
  onSaved,
  readOnly = false,
  readOnlyReason,
  copyFromItemType = null,
}: EditItemTypeModalProps) => {
  const createMutation = useCreateSalesItemTypeSalesItemTypesPost();
  const updateMutation = useUpdateSalesItemTypeSalesItemTypesItemTypeIdPut();

  const docForm = useDocumentSave<
    ItemTypeFormData,
    SalesItemTypeResponseSchema,
    Parameters<typeof createMutation.mutateAsync>[0]["data"],
    Parameters<typeof updateMutation.mutateAsync>[0]["data"]
  >({
    entityLabel: "тип номенклатуры",
    formSchema: itemTypeFormSchema,
    createDefaults: CREATE_DEFAULTS,
    initialData,
    copySource: copyFromItemType,
    readOnly,
    open,
    onOpenChange,
    onSaved,
    queryKey: ["sales-item-types"],
    formId: "sales-item-type-form",
    createStatusEnum: SalesItemTypeCreateSchemaDocStatus,
    buildEditDefaults: (source, isCopy, defaults) => ({
      ...defaults,
      name: isCopy ? `${source.name} (копия)` : source.name,
      description: source.description ?? "",
      item_class: isCopy
        ? source.item_class
        : mapEnumByValue(source.item_class, SalesItemTypeUpdateSchemaItemClass),
      serial_tracking: source.serial_tracking,
      expiration_tracking: source.expiration_tracking,
      vat_rate: Number(source.vat_rate),
      base_uom: source.base_uom ?? "",
      price_group: source.price_group ?? "",
      supply_type: source.supply_type ?? "",
      has_variants: source.has_variants,
      section_id: source.section_id,
      doc_number: isCopy ? undefined : (source.doc_number ?? undefined),
      doc_date: isCopy ? undefined : (source.doc_date ?? undefined),
      doc_status: isCopy
        ? SalesItemTypeUpdateSchemaDocStatus.draft
        : mapEnumByValue(source.doc_status, SalesItemTypeUpdateSchemaDocStatus),
      or_tags: source.or_tags ?? [],
      and_tags: source.and_tags ?? [],
      version: isCopy ? undefined : source.version,
    }),
    buildCreatePayload: (formData) => ({
      name: formData.name,
      description: formData.description || null,
      item_class: mapEnumByValue(
        formData.item_class,
        SalesItemTypeCreateSchemaItemClass,
      ),
      serial_tracking: formData.serial_tracking ?? false,
      expiration_tracking: formData.expiration_tracking ?? false,
      vat_rate: formData.vat_rate,
      base_uom: formData.base_uom || null,
      price_group: formData.price_group || null,
      supply_type: formData.supply_type || null,
      has_variants: formData.has_variants ?? false,
      section_id: formData.section_id,
      doc_status: mapStatusForCreate(
        formData.doc_status,
        SalesItemTypeCreateSchemaDocStatus,
      ),
      doc_number: formData.doc_number || null,
      doc_date: formData.doc_date || null,
      or_tags: formData.or_tags ?? null,
      and_tags: formData.and_tags ?? null,
    }),
    buildUpdatePayload: (formData, source) => ({
      name: formData.name,
      description: formData.description || null,
      item_class: mapEnumByValue(
        formData.item_class,
        SalesItemTypeUpdateSchemaItemClass,
      ),
      serial_tracking: formData.serial_tracking ?? false,
      expiration_tracking: formData.expiration_tracking ?? false,
      vat_rate: formData.vat_rate,
      base_uom: formData.base_uom || null,
      price_group: formData.price_group || null,
      supply_type: formData.supply_type || null,
      has_variants: formData.has_variants ?? false,
      section_id: formData.section_id,
      doc_status: mapEnumByValue(
        formData.doc_status,
        SalesItemTypeUpdateSchemaDocStatus,
      ),
      doc_number: formData.doc_number || null,
      doc_date: formData.doc_date || null,
      or_tags: formData.or_tags ?? null,
      and_tags: formData.and_tags ?? null,
      version: source.version ?? 0,
    }),
    callCreate: (payload) => createMutation.mutateAsync({ data: payload }),
    callUpdate: (id, payload) =>
      updateMutation.mutateAsync({ itemTypeId: id, data: payload }),
    getEntityId: (entity) => entity.id,
    getEntityName: (entity) => entity.name,
    getEntityVersion: (entity) => entity.version,
    buildCopyTitle: (source) => `Копирование типа: ${source.name}`,
  });

  return (
    <DocumentFormShell
      docForm={docForm}
      open={open}
      dialogSize={ITEM_TYPE_DIALOG_SIZE}
      titleCreate="Новый тип номенклатуры"
      titleEdit={`Редактировать тип: ${initialData?.name ?? ""}`}
      titleView="Просмотр типа номенклатуры (только чтение)"
      readOnlyReason={readOnlyReason}
      version={initialData?.version}
      isEditingLocked={initialData?.is_editing_locked}
      sectionName={
        (
          initialData as
            | (SalesItemTypeResponseSchema & { section_name?: string })
            | null
        )?.section_name
      }
      // ✅ Номер, дата и тэги рендерятся на вкладке «Прочее», поэтому
      // типовые поля оболочки скрыты (без дублирования контроллеров).
      visibility={{
        hideDocNumber: true,
        hideDocDate: true,
        hideTags: true,
      }}
    >
      <FormTabs defaultValue="main">
        <FormTabPanel value="main" label="Основное">
          <FormSection
            title="Реквизиты типа номенклатуры"
            description="Наименование, класс и учётные признаки"
          >
            <ItemTypeCustomFields
              control={docForm.control}
              errors={docForm.errors}
              readOnly={readOnly}
            />
          </FormSection>
        </FormTabPanel>

        <FormTabPanel value="other" label="Прочее">
          <FormSection title="Документ" columns={2}>
            <div className="space-y-2">
              <Label htmlFor={`${docForm.formId}-doc_number`}>
                Номер документа
              </Label>
              <Controller
                name="doc_number"
                control={docForm.control}
                render={({ field }) => (
                  <Input
                    id={`${docForm.formId}-doc_number`}
                    {...field}
                    value={field.value ?? ""}
                    placeholder="Например: ТН-001"
                    maxLength={64}
                    disabled={readOnly}
                  />
                )}
              />
              {docForm.errors.doc_number && (
                <p className="text-xs text-destructive">
                  {docForm.errors.doc_number.message}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor={`${docForm.formId}-doc_date`}>
                Дата документа
              </Label>
              <Controller
                name="doc_date"
                control={docForm.control}
                render={({ field }) => (
                  <Input
                    id={`${docForm.formId}-doc_date`}
                    type="date"
                    {...field}
                    value={field.value ?? ""}
                    disabled={readOnly}
                  />
                )}
              />
            </div>
          </FormSection>

          <FormSection
            title="Тэги доступа"
            description="OR-тэги — белый список видимости, AND-тэги — обязательный допуск"
          >
            <div className="space-y-2">
              <Label htmlFor={`${docForm.formId}-or_tags`}>
                OR-тэги{" "}
                <span className="text-xs text-muted-foreground">
                  (через запятую, формат: пространство:значение)
                </span>
              </Label>
              <Controller
                name="or_tags"
                control={docForm.control}
                render={({ field }) => (
                  <Input
                    id={`${docForm.formId}-or_tags`}
                    value={joinTags(field.value)}
                    onChange={(event) =>
                      field.onChange(parseTags(event.target.value))
                    }
                    placeholder="регион:сибирь, отдел:продажи"
                    disabled={readOnly}
                  />
                )}
              />
              {docForm.errors.or_tags && (
                <p className="text-xs text-destructive">
                  {docForm.errors.or_tags.message}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor={`${docForm.formId}-and_tags`}>
                AND-тэги{" "}
                <span className="text-xs text-muted-foreground">
                  (обязательный допуск, через запятую)
                </span>
              </Label>
              <Controller
                name="and_tags"
                control={docForm.control}
                render={({ field }) => (
                  <Input
                    id={`${docForm.formId}-and_tags`}
                    value={joinTags(field.value)}
                    onChange={(event) =>
                      field.onChange(parseTags(event.target.value))
                    }
                    placeholder="гриф:секретно"
                    disabled={readOnly}
                  />
                )}
              />
              {docForm.errors.and_tags && (
                <p className="text-xs text-destructive">
                  {docForm.errors.and_tags.message}
                </p>
              )}
            </div>
          </FormSection>
        </FormTabPanel>
      </FormTabs>
    </DocumentFormShell>
  );
};