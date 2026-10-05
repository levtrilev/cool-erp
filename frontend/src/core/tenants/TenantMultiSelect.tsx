import { useState } from "react";
import { Check, ChevronsUpDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { useReadTenantsTenantsGet } from "@/api/generated/tenants/tenants";

interface TenantMultiSelectProps {
  value: string[];
  onChange: (value: string[]) => void;
}

export function TenantMultiSelect({ value, onChange }: TenantMultiSelectProps) {
  const [open, setOpen] = useState(false);
  const { data } = useReadTenantsTenantsGet({ limit: 100 }); // Загружаем все тенанты (их обычно немного)
  const tenants = data?.items || [];

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="outline" role="combobox" aria-expanded={open} className="w-full justify-between">
          {value.length > 0 ? `Выбрано организаций: ${value.length}` : "Выберите организации..."}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-full p-0">
        <Command>
          <CommandInput placeholder="Поиск организации..." />
          <CommandList>
            <CommandEmpty>Организации не найдены.</CommandEmpty>
            <CommandGroup>
              {tenants.map((tenant) => (
                <CommandItem
                  key={tenant.id}
                  value={tenant.id}
                  onSelect={() => {
                    const newValue = value.includes(tenant.id)
                      ? value.filter((id) => id !== tenant.id)
                      : [...value, tenant.id];
                    onChange(newValue);
                  }}
                >
                  <Check className={cn("mr-2 h-4 w-4", value.includes(tenant.id) ? "opacity-100" : "opacity-0")} />
                  {tenant.name}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}