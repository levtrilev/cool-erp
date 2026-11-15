import { Controller } from "react-hook-form";
import {
  useCreateGoodsSalesGoodsPost,
  useUpdateGoodsSalesGoodsGoodsIdPut,
} from "@/api/generated/sales-goods/sales-goods";
import {
  SalesGoodsResponseSchema,
  SalesGoodsCreateSchemaDocStatus,
  SalesGoodsUpdateSchemaDocStatus,
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
  joinTags,
  mapEnumByValue,
  parseTags,
} from "@/lib/document-form/documentFormHelpers";
import { GoodsCustomFields } from "./GoodsCustomFields";
import { goodFormSchema, CREATE_DEFAULTS, type GoodFormData } from "./schemas";
import { FormSection, FormTabPanel, FormTabs } from "@/lib/form-blocks";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

/** Геометрия окна определяется конкретной модалкой (не шаблоном). */
const GOOD_DIALOG_SIZE: DocumentDialogSize = {
  width: 860,
  minWidth: 640,
  minHeight: 480,
  maxWidth: "92vw",
  maxHeight: "90vh",
};

interface EditGoodModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData: SalesGoodsResponseSchema | null;
  onSaved: (id: string, name?: string) => Promise<void>;
  readOnly?: boolean;
  readOnlyReason?: string;
  copyFromGood?: SalesGoodsResponseSchema | null;
}

export const EditGoodModal = ({
  open,
  onOpenChange,
  initialData,
  onSaved,
  readOnly = false,
  readOnlyReason,
  copyFromGood = null,
}: EditGoodModalProps) => {
  const createMutation = useCreateGoodsSalesGoodsPost();
  const updateMutation = useUpdateGoodsSalesGoodsGoodsIdPut();

  const docForm = useDocumentSave<
    GoodFormData,
    SalesGoodsResponseSchema,
    Parameters<typeof createMutation.mutateAsync>[0]["data"],
    Parameters<typeof updateMutation.mutateAsync>[0]["data"]
  >({
    entityLabel: "товар",
    formSchema: goodFormSchema,
    createDefaults: CREATE_DEFAULTS,
    initialData,
    copySource: copyFromGood,
    readOnly,
    open,
    onOpenChange,
    onSaved,
    queryKey: ["sales-goods"],
    formId: "sales-good-form",
    createStatusEnum: SalesGoodsCreateSchemaDocStatus,
    buildEditDefaults: (source, isCopy, defaults) => ({
      ...defaults,
      name: isCopy ? `${source.name} (копия)` : source.name,
      description: source.description ?? "",
      item_type_id: source.item_type_id ?? "",
      base_uom: source.base_uom ?? "",
      section_id: source.section_id,
      doc_number: isCopy ? undefined : (source.doc_number ?? undefined),
      doc_date: isCopy ? undefined : (source.doc_date ?? undefined),
      doc_status: isCopy
        ? SalesGoodsUpdateSchemaDocStatus.draft
        : mapEnumByValue(source.doc_status, SalesGoodsUpdateSchemaDocStatus),
      or_tags: source.or_tags ?? [],
      and_tags: source.and_tags ?? [],
      version: isCopy ? undefined : source.version,
    }),
    buildCreatePayload: (formData) => ({
      name: formData.name,
      description: formData.description || null,
      item_type_id: formData.item_type_id || null,
      base_uom: formData.base_uom || null,
      section_id: formData.section_id,
      doc_status: mapStatusForCreate(
        formData.doc_status,
        SalesGoodsCreateSchemaDocStatus,
      ),
      doc_number: formData.doc_number || null,
      doc_date: formData.doc_date || null,
      or_tags: formData.or_tags ?? null,
      and_tags: formData.and_tags ?? null,
    }),
    buildUpdatePayload: (formData, source) => ({
      name: formData.name,
      description: formData.description || null,
      item_type_id: formData.item_type_id || null,
      base_uom: formData.base_uom || null,
      section_id: formData.section_id,
      doc_status: mapEnumByValue(
        formData.doc_status,
        SalesGoodsUpdateSchemaDocStatus,
      ),
      doc_number: formData.doc_number || null,
      doc_date: formData.doc_date || null,
      or_tags: formData.or_tags ?? null,
      and_tags: formData.and_tags ?? null,
      version: source.version ?? 0,
    }),
    callCreate: (payload) => createMutation.mutateAsync({ data: payload }),
    callUpdate: (id, payload) =>
      updateMutation.mutateAsync({ goodsId: id, data: payload }),
    getEntityId: (entity) => entity.id,
    getEntityName: (entity) => entity.name,
    getEntityVersion: (entity) => entity.version,
    buildCopyTitle: (source) => `Копирование товара: ${source.name}`,
  });

  return (
    <DocumentFormShell
      docForm={docForm}
      open={open}
      dialogSize={GOOD_DIALOG_SIZE}
      titleCreate="Новый товар"
      titleEdit={`Редактировать товар: ${initialData?.name ?? ""}`}
      titleView="Просмотр товара (только чтение)"
      readOnlyReason={readOnlyReason}
      version={initialData?.version}
      isEditingLocked={initialData?.is_editing_locked}
      sectionName={
        (
          initialData as
            | (SalesGoodsResponseSchema & { section_name?: string })
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
            <GoodsCustomFields
              control={docForm.control}
              errors={docForm.errors}
              readOnly={readOnly}
              setValue={docForm.setValue}
              itemTypeName={
                (
                  initialData as
                    | (SalesGoodsResponseSchema & { item_type_name?: string })
                    | null
                )?.item_type_name
              }
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
