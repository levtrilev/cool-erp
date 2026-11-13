// frontend/src/components/theme/ThemeToggle.tsx
import { Check, Monitor, Moon, Sun, type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ThemePreferenceSchemaMode } from "@/api/generated/coolERP.schemas";
import {
  DARK_PALETTES,
  LIGHT_PALETTES,
} from "@/components/theme/theme-context";
import { useThemePreference } from "@/lib/ui-preferences/useThemePreference";
import type { ThemeMode } from "@/lib/ui-preferences/themePalettes";
import { cn } from "@/lib/utils";

type ModeItem = {
  value: ThemeMode;
  label: string;
  Icon: LucideIcon;
};

const MODE_ITEMS: readonly ModeItem[] = [
  { value: ThemePreferenceSchemaMode.light, label: "Светлая", Icon: Sun },
  { value: ThemePreferenceSchemaMode.dark, label: "Тёмная", Icon: Moon },
  { value: ThemePreferenceSchemaMode.system, label: "Как в системе", Icon: Monitor },
];

/** Полоса прокрутки списка палитр в токенах текущей темы. */
const SCROLLBAR_CLASS =
  "[&::-webkit-scrollbar]:w-2 [&::-webkit-scrollbar-track]:rounded-full " +
  "[&::-webkit-scrollbar-track]:bg-muted " +
  "[&::-webkit-scrollbar-thumb]:rounded-full " +
  "[&::-webkit-scrollbar-thumb]:bg-border " +
  "hover:[&::-webkit-scrollbar-thumb]:bg-muted-foreground/40 " +
  "[scrollbar-width:thin] [scrollbar-color:hsl(var(--border))_hsl(var(--muted))]";

/**
 * Переключатель темы и палитр.
 * Пишет в серверные настройки пользователя, поэтому оформление
 * подхватывается в любом браузере после входа.
 * Обязан находиться внутри UiPreferencesProvider.
 */
export const ThemeToggle = () => {
  const {
    mode,
    resolvedTheme,
    lightPalette,
    darkPalette,
    setMode,
    setLightPalette,
    setDarkPalette,
    isRestored,
  } = useThemePreference();

  const TriggerIcon: LucideIcon = resolvedTheme === "dark" ? Moon : Sun;
  const isLightActive: boolean = resolvedTheme === "light";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-9 w-9"
          disabled={!isRestored}
          title="Тема оформления"
        >
          <TriggerIcon className="h-4 w-4" />
          <span className="sr-only">Выбор темы оформления</span>
        </Button>
      </DropdownMenuTrigger>

      <DropdownMenuContent
        align="end"
        className={cn(
          "w-72 max-h-[min(70vh,34rem)] overflow-y-auto overscroll-contain",
          SCROLLBAR_CLASS,
        )}
      >
        {/* ── Режимы ─────────────────────────────────────────── */}
        {MODE_ITEMS.map(({ value, label, Icon }) => (
          <DropdownMenuItem
            key={value}
            onClick={() => setMode(value)}
            className="cursor-pointer gap-2"
          >
            <Icon className="h-4 w-4 shrink-0" />
            <span className="flex-1">{label}</span>
            {mode === value && (
              <Check className="h-4 w-4 shrink-0 text-primary" />
            )}
          </DropdownMenuItem>
        ))}

        {/* ── Светлые палитры ────────────────────────────────── */}
        <DropdownMenuSeparator />
        <DropdownMenuLabel
          className={cn(
            "text-xs font-normal",
            isLightActive ? "text-foreground" : "text-muted-foreground",
          )}
        >
          Светлая тема — палитра
          {isLightActive && (
            <span className="ml-1.5 text-[10px] uppercase tracking-wide text-primary">
              активна
            </span>
          )}
        </DropdownMenuLabel>

        {LIGHT_PALETTES.map((palette) => (
          <DropdownMenuItem
            key={palette.id}
            onClick={() => setLightPalette(palette.id)}
            className="cursor-pointer items-start gap-2 py-1.5"
          >
            <Sun className="mt-0.5 h-4 w-4 shrink-0" />
            <span className="flex min-w-0 flex-1 flex-col leading-tight">
              <span className="truncate">{palette.label}</span>
              <span className="text-xs text-muted-foreground">
                {palette.hint}
              </span>
            </span>
            {lightPalette === palette.id && (
              <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            )}
          </DropdownMenuItem>
        ))}

        {/* ── Тёмные палитры ─────────────────────────────────── */}
        <DropdownMenuSeparator />
        <DropdownMenuLabel
          className={cn(
            "text-xs font-normal",
            isLightActive ? "text-muted-foreground" : "text-foreground",
          )}
        >
          Тёмная тема — палитра
          {!isLightActive && (
            <span className="ml-1.5 text-[10px] uppercase tracking-wide text-primary">
              активна
            </span>
          )}
        </DropdownMenuLabel>

        {DARK_PALETTES.map((palette) => (
          <DropdownMenuItem
            key={palette.id}
            onClick={() => setDarkPalette(palette.id)}
            className="cursor-pointer items-start gap-2 py-1.5"
          >
            <Moon className="mt-0.5 h-4 w-4 shrink-0" />
            <span className="flex min-w-0 flex-1 flex-col leading-tight">
              <span className="truncate">{palette.label}</span>
              <span className="text-xs text-muted-foreground">
                {palette.hint}
              </span>
            </span>
            {darkPalette === palette.id && (
              <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
            )}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};