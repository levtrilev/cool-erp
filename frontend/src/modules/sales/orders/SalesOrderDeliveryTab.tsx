import { Controller, type Control, type FieldErrors } from "react-hook-form";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { FieldsGrid } from "@/lib/form-blocks/FieldsGrid";
import { FieldBlock } from "@/lib/form-blocks/FieldBlock";
import type { SalesOrderFormData } from "./schemas";
import { DELIVERY_METHOD_LABELS, DELIVERY_METHODS } from "./schemas";

interface SalesOrderDeliveryTabProps {
  control: Control<SalesOrderFormData>;
  errors: FieldErrors<SalesOrderFormData>;
  readOnly: boolean;
}

/** Вкладка «Доставка»: адрес и способ доставки. */
export const SalesOrderDeliveryTab = ({ control, readOnly }: SalesOrderDeliveryTabProps) => {
  return (
    <FieldsGrid cols={1}>
      <FieldBlock label="Адрес доставки" htmlFor="delivery_address">
        <Controller
          name="delivery_address"
          control={control}
          render={({ field }) => (
            <Textarea
              id="delivery_address"
              {...field}
              value={field.value ?? ""}
              rows={3}
              placeholder="Введите адрес доставки..."
              disabled={readOnly}
            />
          )}
        />
      </FieldBlock>

      <FieldBlock label="Способ доставки" htmlFor="delivery_method">
        <Controller
          name="delivery_method"
          control={control}
          render={({ field }) => (
            <Select value={field.value ?? ""} onValueChange={field.onChange} disabled={readOnly}>
              <SelectTrigger id="delivery_method" className="w-full">
                <SelectValue placeholder="Выберите способ доставки..." />
              </SelectTrigger>
              <SelectContent position="popper" sideOffset={4}>
                {DELIVERY_METHODS.map((method) => (
                  <SelectItem key={method} value={method}>
                    {DELIVERY_METHOD_LABELS[method]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
      </FieldBlock>
    </FieldsGrid>
  );
};