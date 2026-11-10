import { Controller } from "react-hook-form";
import type { Control, FieldErrors } from "react-hook-form";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import type { NoteFormData } from "./schemas";

interface NoteCustomFieldsProps {
  control: Control<NoteFormData>;
  errors: FieldErrors<NoteFormData>;
  readOnly: boolean;
}

export const NoteCustomFields = ({
  control,
  errors,
  readOnly,
}: NoteCustomFieldsProps) => (
  <>
    <div className="space-y-2">
      <Label htmlFor="note-title">
        Название <span className="text-destructive">*</span>
      </Label>
      <Controller
        name="title"
        control={control}
        render={({ field }) => (
          <Input
            id="note-title"
            {...field}
            placeholder="Введите название заметки"
            disabled={readOnly}
          />
        )}
      />
      {errors.title && (
        <p className="text-xs text-destructive">{errors.title.message}</p>
      )}
    </div>

    <div className="space-y-2">
      <Label htmlFor="note-content">Содержимое</Label>
      <Controller
        name="content"
        control={control}
        render={({ field }) => (
          <Textarea
            id="note-content"
            {...field}
            value={field.value ?? ""}
            rows={6}
            placeholder="Текст заметки..."
            disabled={readOnly}
          />
        )}
      />
    </div>
  </>
);