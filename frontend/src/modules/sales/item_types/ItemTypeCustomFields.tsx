// frontend/src/modules/sales/item_types/ItemTypeCustomFields.tsx
import type { Control, FieldErrors } from "react-hook-form";
import { Controller } from "react-hook-form";
import { CheckCircle2, PauseCircle } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ITEM_CLASS_LABELS, type ItemTypeFormData } from "./schemas";

interface ItemTypeCustomFieldsProps {
  control: Control<ItemTypeFormData>;
  errors: FieldErrors<ItemTypeFormData>;
  readOnly: boolean;
}

/** Бизнес-поля карточки типа номенклатуры (рендерятся внутри DocumentFormShell). */
export const ItemTypeCustomFields = ({
  control,
  errors,
  readOnly,
}: ItemTypeCustomFieldsProps) => (
  <div className="space-y-4">
    <div className="grid grid-cols-2 gap-4">
      <div className="space-y-2">
        <Label htmlFor="item-type-name">
          Наименование <span className="text-destructive">*</span>
        </Label>
        <Controller
          name="name"
          control={control}
          render={({ field }) => (
            <Input
              id="item-type-name"
              {...field}
              placeholder="Например: Крепёж стандартный"
              maxLength={255}
              disabled={readOnly}
            />
          )}
        />
        {errors.name && (
          <p className="text-xs text-destructive">{errors.name.message}</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="item-type-class">
          Класс номенклатуры <span className="text-destructive">*</span>
        </Label>
        <Controller
          name="item_class"
          control={control}
          render={({ field }) => (
            <Select
              value={field.value}
              onValueChange={field.onChange}
              disabled={readOnly}
            >
              <SelectTrigger id="item-type-class" className="w-full">
                <SelectValue placeholder="Выберите класс" />
              </SelectTrigger>
              <SelectContent
                position="popper"
                sideOffset={4}
                className="w-[var(--radix-select-trigger-width)] max-h-60"
              >
                {Object.entries(ITEM_CLASS_LABELS).map(([value, label]) => (
                  <SelectItem key={value} value={value}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
        {errors.item_class && (
          <p className="text-xs text-destructive">
            {errors.item_class.message}
          </p>
        )}
      </div>
    </div>

    <div className="space-y-2">
      <Label htmlFor="item-type-description">Описание</Label>
      <Controller
        name="description"
        control={control}
        render={({ field }) => (
          <Textarea
            id="item-type-description"
            {...field}
            value={field.value ?? ""}
            placeholder="Описание типа номенклатуры..."
            rows={3}
            disabled={readOnly}
          />
        )}
      />
      {errors.description && (
        <p className="text-xs text-destructive">{errors.description.message}</p>
      )}
    </div>

    <div className="grid grid-cols-2 gap-4">
      <div className="space-y-2">
        <Label htmlFor="item-type-vat-rate">Ставка НДС, %</Label>
        <Controller
          name="vat_rate"
          control={control}
          render={({ field }) => (
            <Input
              id="item-type-vat-rate"
              type="number"
              min={0}
              max={100}
              step="0.01"
              value={field.value}
              onChange={(e) => field.onChange(Number(e.target.value) || 0)}
              disabled={readOnly}
              className="tabular-nums"
            />
          )}
        />
        {errors.vat_rate && (
          <p className="text-xs text-destructive">{errors.vat_rate.message}</p>
        )}
      </div>
      <div className="space-y-2">
        <Label htmlFor="item-type-base-uom">Единица измерения</Label>
        <Controller
          name="base_uom"
          control={control}
          render={({ field }) => (
            <Input
              id="item-type-base-uom"
              {...field}
              value={field.value ?? ""}
              placeholder="Например: шт"
              maxLength={64}
              disabled={readOnly}
            />
          )}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="item-type-price-group">Ценовая группа</Label>
        <Controller
          name="price_group"
          control={control}
          render={({ field }) => (
            <Input
              id="item-type-price-group"
              {...field}
              value={field.value ?? ""}
              placeholder="Например: Оптовая"
              maxLength={128}
              disabled={readOnly}
            />
          )}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="item-type-supply-type">Схема обеспечения</Label>
        <Controller
          name="supply_type"
          control={control}
          render={({ field }) => (
            <Input
              id="item-type-supply-type"
              {...field}
              value={field.value ?? ""}
              placeholder="Например: Под заказ"
              maxLength={128}
              disabled={readOnly}
            />
          )}
        />
      </div>
    </div>

    {/* ✅ Правило №34: Switch с Label, цветом и иконкой.
        Пара обёрнута в ОДИН flex-контейнер: без обёртки Switch и Label
        становились отдельными элементами CSS-grid и занимали две строки. */}
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <Controller
        name="serial_tracking"
        control={control}
        render={({ field }) => (
          <div className="flex items-center gap-2">
            <Switch
              id="item-type-serial"
              checked={field.value ?? false}
              onCheckedChange={field.onChange}
              disabled={readOnly}
            />
            <Label
              htmlFor="item-type-serial"
              className={`flex items-center gap-2 cursor-pointer font-medium transition-colors ${
                field.value
                  ? "text-green-600 dark:text-green-400"
                  : "text-red-500 dark:text-red-400"
              }`}
            >
              {field.value ? (
                <CheckCircle2 className="h-4 w-4 shrink-0" />
              ) : (
                <PauseCircle className="h-4 w-4 shrink-0" />
              )}
              Серийные номера
            </Label>
          </div>
        )}
      />
      <Controller
        name="expiration_tracking"
        control={control}
        render={({ field }) => (
          <div className="flex items-center gap-2">
            <Switch
              id="item-type-expiration"
              checked={field.value ?? false}
              onCheckedChange={field.onChange}
              disabled={readOnly}
            />
            <Label
              htmlFor="item-type-expiration"
              className={`flex items-center gap-2 cursor-pointer font-medium transition-colors ${
                field.value
                  ? "text-green-600 dark:text-green-400"
                  : "text-red-500 dark:text-red-400"
              }`}
            >
              {field.value ? (
                <CheckCircle2 className="h-4 w-4 shrink-0" />
              ) : (
                <PauseCircle className="h-4 w-4 shrink-0" />
              )}
              Сроки годности
            </Label>
          </div>
        )}
      />
      <Controller
        name="has_variants"
        control={control}
        render={({ field }) => (
          <div className="flex items-center gap-2">
            <Switch
              id="item-type-variants"
              checked={field.value ?? false}
              onCheckedChange={field.onChange}
              disabled={readOnly}
            />
            <Label
              htmlFor="item-type-variants"
              className={`flex items-center gap-2 cursor-pointer font-medium transition-colors ${
                field.value
                  ? "text-green-600 dark:text-green-400"
                  : "text-red-500 dark:text-red-400"
              }`}
            >
              {field.value ? (
                <CheckCircle2 className="h-4 w-4 shrink-0" />
              ) : (
                <PauseCircle className="h-4 w-4 shrink-0" />
              )}
              Вариации товара
            </Label>
          </div>
        )}
      />
    </div>
  </div>
);
