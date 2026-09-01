import { useQuery } from "@tanstack/react-query";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Loader2 } from "lucide-react";

// Универсальный тип для элемента справочника
interface ReferenceItem {
  id: string;
  name: string;
}

// Универсальные пропсы для компонента
interface ReferenceSelectProps<T extends ReferenceItem> {
  // Функция для получения данных (должна возвращать Promise с массивом элементов)
  fetchFn: () => Promise<T[]>;
  // Уникальный ключ для кэширования React Query
  queryKey: string[];
  // Текущее значение (ID выбранного элемента)
  value: string | undefined;
  // Обработчик изменения значения
  onValueChange: (value: string) => void;
  // Placeholder
  placeholder?: string;
  // Отключен ли компонент
  disabled?: boolean;
}

/**
 * Универсальный компонент Select для выбора из справочника
 * 
 * @example
 * <ReferenceSelect
 *   fetchFn={getTenants}
 *   queryKey={['tenants']}
 *   value={tenantId}
 *   onValueChange={setTenantId}
 *   placeholder="Выберите организацию"
 * />
 */
export function ReferenceSelect<T extends ReferenceItem>({
  fetchFn,
  queryKey,
  value,
  onValueChange,
  placeholder = "Выберите...",
  disabled = false,
}: ReferenceSelectProps<T>) {
  const { data, isLoading, isError } = useQuery({
    queryKey,
    queryFn: fetchFn,
    staleTime: 5 * 60 * 1000, // Кэш на 5 минут
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 h-10 px-3 border rounded-md">
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        <span className="text-sm text-muted-foreground">Загрузка...</span>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="h-10 px-3 border rounded-md flex items-center text-sm text-destructive">
        Ошибка загрузки справочника
      </div>
    );
  }

  return (
    <Select value={value} onValueChange={onValueChange} disabled={disabled}>
      <SelectTrigger className="w-full">
        <SelectValue placeholder={placeholder} />
      </SelectTrigger>
      <SelectContent>
        {data.map((item) => (
          <SelectItem key={item.id} value={item.id}>
            {item.name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}