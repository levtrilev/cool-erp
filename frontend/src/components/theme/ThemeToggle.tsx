import { Check, Monitor, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useTheme } from "@/components/hooks/useTheme";
import { THEME_PALETTES } from "@/components/theme/theme-context";

export const ThemeToggle = () => {
  const { theme, resolvedTheme, palette, setTheme, setPalette } = useTheme();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" title="Тема оформления">
          {resolvedTheme === "dark" ? (
            <Moon className="h-4 w-4" />
          ) : (
            <Sun className="h-4 w-4" />
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        {/* Режимы */}
        <DropdownMenuItem onClick={() => setTheme("light")}>
          <Sun className="mr-2 h-4 w-4" />
          Светлая
          {theme === "light" && (
            <Check className="ml-auto h-4 w-4 text-primary" />
          )}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme("system")}>
          <Monitor className="mr-2 h-4 w-4" />
          Как в системе
          {theme === "system" && (
            <Check className="ml-auto h-4 w-4 text-primary" />
          )}
        </DropdownMenuItem>

        <DropdownMenuSeparator />
        <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">
          Тёмная тема — палитра
        </DropdownMenuLabel>

        {/* Палитры тёмной темы: выбор включает режим dark */}
        {THEME_PALETTES.map((p) => (
          <DropdownMenuItem
            key={p.id}
            onClick={() => {
              setTheme("dark");
              setPalette(p.id);
            }}
          >
            <Moon className="mr-2 h-4 w-4" />
            <span className="flex flex-col leading-tight">
              <span>{p.label}</span>
              <span className="text-xs text-muted-foreground">{p.hint}</span>
            </span>
            {theme === "dark" && palette === p.id && (
              <Check className="ml-auto h-4 w-4 text-primary" />
            )}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};