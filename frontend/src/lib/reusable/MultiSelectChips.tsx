import { useState } from "react";
import { X, Plus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ReferenceMultiSelect,
  type ReferenceMultiItem,
} from "./ReferenceMultiSelect";

interface MultiSelectChipsProps<T extends ReferenceMultiItem> {
  value: string[];
  onValueChange: (value: string[]) => void;
  fetchFn: (params: {
    skip: number;
    limit: number;
    search?: string;
  }) => Promise<{ items: T[]; total: number }>;
  queryKey: string[];
  /** Все доступные элементы (для отображения названий в chips) */
  allItems: Array<{ id: string; name: string }>;
  placeholder?: string;
  disabled?: boolean;
  limit?: number;
  heading?: string;
  columns?: Array<{ column: keyof T; label: string }>;
}

/**
 * Компонент для отображения выбранных элементов в виде chips с кнопкой "Добавить".
 * Использует ReferenceMultiSelect для выбора новых элементов.
 */
export function MultiSelectChips<T extends ReferenceMultiItem>({
  value,
  onValueChange,
  fetchFn,
  queryKey,
  allItems,
//   placeholder = "Добавить...",
  disabled = false,
  limit = 50,
  heading = "Выберите элементы",
  columns = [],
}: MultiSelectChipsProps<T>) {
  const [isAdding, setIsAdding] = useState(false);
  const [tempSelection, setTempSelection] = useState<string[]>([]);

  // Элементы, которые уже выбраны (для отображения в chips)
  const selectedItems = allItems.filter((item) => value.includes(item.id));

  const handleAdd = () => {
    setIsAdding(true);
    setTempSelection([]);
  };

  const handleConfirmAdd = () => {
    // Добавляем новые элементы к существующим
    const newValue = [...new Set([...value, ...tempSelection])];
    onValueChange(newValue);
    setIsAdding(false);
    setTempSelection([]);
  };

  const handleCancelAdd = () => {
    setIsAdding(false);
    setTempSelection([]);
  };

  const handleRemove = (itemId: string) => {
    onValueChange(value.filter((id) => id !== itemId));
  };

  return (
    <div className="space-y-2">
      {/* Chips с выбранными элементами */}
      <div className="flex flex-wrap gap-2">
        {selectedItems.map((item) => (
          <Badge
            key={item.id}
            variant="secondary"
            className="flex items-center gap-1 pr-1"
          >
            <span className="max-w-[150px] truncate">{item.name}</span>
            <button
              type="button"
              className="rounded-full outline-none ring-offset-background focus:ring-2 focus:ring-ring focus:ring-offset-1"
              onClick={() => handleRemove(item.id)}
              disabled={disabled}
            >
              <X className="h-3 w-3 text-muted-foreground hover:text-foreground" />
            </button>
          </Badge>
        ))}
      </div>

      {/* Кнопка "Добавить" или ReferenceMultiSelect */}
      {isAdding ? (
        <div className="space-y-2">
          <ReferenceMultiSelect
            fetchFn={fetchFn}
            queryKey={queryKey}
            value={tempSelection}
            onValueChange={setTempSelection}
            placeholder="Выберите для добавления..."
            limit={limit}
            heading={heading}
            columns={columns}
            excludeIds={value} // Исключаем уже выбранные
          />
          <div className="flex gap-2">
            <Button
              type="button"
              size="sm"
              onClick={handleConfirmAdd}
              disabled={tempSelection.length === 0}
            >
              Добавить ({tempSelection.length})
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={handleCancelAdd}
            >
              Отмена
            </Button>
          </div>
        </div>
      ) : (
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={handleAdd}
          disabled={disabled}
        >
          <Plus className="h-4 w-4 mr-1" />
          Добавить
        </Button>
      )}
    </div>
  );
}