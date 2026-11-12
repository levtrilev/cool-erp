import { useState } from 'react';
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from '@/components/ui/command';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Button } from '@/components/ui/button';
import { Check, ChevronsUpDown } from 'lucide-react';

interface ComboboxProps<T> {
  value: string;
  onValueChange: (value: string) => void;
  options: T[];
  getOptionLabel: (option: T) => string;
  getOptionValue: (option: T) => string;
  placeholder?: string;
  className?: string;
}

export function Combobox<T>({ value, onValueChange, options, getOptionLabel, getOptionValue, placeholder, className }: ComboboxProps<T>) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');

  const filteredOptions = options.filter((option) =>
    getOptionLabel(option).toLowerCase().includes(search.toLowerCase())
  );

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={`w-[200px] justify-between ${className}`}
        >
          {value
            ? getOptionLabel(options.find((option) => getOptionValue(option) === value)!)
            : placeholder || 'Select...'}
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[200px] p-0">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Search..."
            value={search}
            onValueChange={setSearch}
          />
          <CommandEmpty>No results found.</CommandEmpty>
          <CommandGroup>
            <CommandList>
              {filteredOptions.map((option) => (
                <CommandItem
                  key={getOptionValue(option)}
                  value={getOptionValue(option)}
                  onSelect={(currentValue) => {
                    onValueChange(currentValue === value ? '' : currentValue);
                    setOpen(false);
                  }}
                >
                  <Check
                    className={`mr-2 h-4 w-4 ${value === getOptionValue(option) ? 'opacity-100' : 'opacity-0'}`}
                  />
                  {getOptionLabel(option)}
                </CommandItem>
              ))}
            </CommandList>
          </CommandGroup>
        </Command>
      </PopoverContent>
    </Popover>
  );
}