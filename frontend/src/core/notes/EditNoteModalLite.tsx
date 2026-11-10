import {
  useCreateNoteNotesPost,
  useUpdateNoteNotesNoteIdPut,
} from "@/api/generated/notes/notes";
import {
  NoteResponseSchema,
  NoteCreateSchemaDocStatus,
  NoteUpdateSchemaDocStatus,
} from "@/api/generated/coolERP.schemas";
import { useDocumentSave, mapStatusForCreate } from "@/lib/document-form/useDocumentSave";
import { DocumentFormShell } from "@/lib/document-form/DocumentFormShell";
import { NoteCustomFields } from "./NoteCustomFields";
import { noteFormSchema, CREATE_DEFAULTS, type NoteFormData } from "./schemas";
import { mapEnumByValue } from "@/lib/document-form/documentFormHelpers";

interface EditNoteModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  initialData: NoteResponseSchema | null;
  onSaved: (id: string, title?: string) => Promise<void>;
  readOnly?: boolean;
  readOnlyReason?: string;
  copyFromNote?: NoteResponseSchema | null;
}

export const EditNoteModal = ({
  open,
  onOpenChange,
  initialData,
  onSaved,
  readOnly = false,
  readOnlyReason,
  copyFromNote = null,
}: EditNoteModalProps) => {
  const createMutation = useCreateNoteNotesPost();
  const updateMutation = useUpdateNoteNotesNoteIdPut();

  const docForm = useDocumentSave<
    NoteFormData,
    NoteResponseSchema,
    Parameters<typeof createMutation.mutateAsync>[0]["data"],
    Parameters<typeof updateMutation.mutateAsync>[0]["data"]
  >({
    entityLabel: "заметка",
    formSchema: noteFormSchema,
    createDefaults: CREATE_DEFAULTS,
    initialData,
    copySource: copyFromNote,
    readOnly,
    open,
    onOpenChange,
    onSaved,
    queryKey: ["notes"],
    createStatusEnum: NoteCreateSchemaDocStatus,
    formId: "note-form",
    buildEditDefaults: (source, isCopy, defaults) => ({
      ...defaults,
      title: isCopy ? `${source.title} (копия)` : source.title,
      content: source.content ?? "",
      section_id: source.section_id,
      doc_number: isCopy ? undefined : (source.doc_number ?? undefined),
      doc_date: isCopy ? undefined : (source.doc_date ?? undefined),
      doc_status: isCopy
        ? NoteUpdateSchemaDocStatus.draft
        : mapEnumByValue(source.doc_status, NoteUpdateSchemaDocStatus),
      or_tags: source.or_tags ?? [],
      and_tags: source.and_tags ?? [],
      version: isCopy ? undefined : source.version,
    }),
    buildCreatePayload: (formData) => ({
      title: formData.title,
      content: formData.content || null,
      section_id: formData.section_id,
      doc_status: mapStatusForCreate(
        formData.doc_status,
        NoteCreateSchemaDocStatus,
      ),
      doc_number: formData.doc_number || null,
      doc_date: formData.doc_date || null,
      or_tags: formData.or_tags ?? null,
      and_tags: formData.and_tags ?? null,
    }),

    buildUpdatePayload: (formData, source) => ({
      title: formData.title,
      content: formData.content || null,
      section_id: formData.section_id,
      doc_status: formData.doc_status,
      doc_number: formData.doc_number || null,
      doc_date: formData.doc_date || null,
      or_tags: formData.or_tags ?? null,
      and_tags: formData.and_tags ?? null,
      version: source.version ?? 0,
    }),

    callCreate: (payload) => createMutation.mutateAsync({ data: payload }),
    callUpdate: (id, payload) =>
      updateMutation.mutateAsync({ noteId: id, data: payload }),

    getEntityId: (entity) => entity.id,
    getEntityName: (entity) => entity.title,
    getEntityVersion: (entity) => entity.version,

    buildCopyTitle: (source) => `${source.title} (копия)`,
  });

  return (
    <DocumentFormShell
      docForm={docForm}
      open={open}
      titleCreate="Новая заметка"
      titleEdit="Редактировать заметку"
      titleView="Просмотр заметки (только чтение)"
      readOnlyReason={readOnlyReason}
      version={initialData?.version}
      isEditingLocked={initialData?.is_editing_locked}
      sectionName={
        (initialData as (NoteResponseSchema & { section_name?: string }) | null)
          ?.section_name
      }
    >
      <NoteCustomFields
        control={docForm.control}
        errors={docForm.errors}
        readOnly={readOnly}
      />
    </DocumentFormShell>
  );
};