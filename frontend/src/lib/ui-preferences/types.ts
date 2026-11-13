// frontend/src/lib/ui-preferences/types.ts
import {
  NavigationPreferenceSchemaLayout,
  type UiPreferencesPatchSchema,
  type UiPreferencesResponseSchema,
} from "@/api/generated/coolERP.schemas";
import {
  normalizeThemePreference,
  type UiThemePreference,
} from "./themePalettes";

export type { ThemeMode, UiThemePreference } from "./themePalettes";

// ── Производные типы из Orval-схем ────────────────────────────────
type NavigationPreference = NonNullable<
  UiPreferencesResponseSchema["navigation"]
>;
type TablesMap = NonNullable<UiPreferencesResponseSchema["tables"]>;

export type TablePreference = TablesMap[string];
type ColumnStatesMap = NonNullable<TablePreference["column_states"]>;
export type TableColumnState = ColumnStatesMap[string];

export type NavigationLayout = NonNullable<NavigationPreference["layout"]>;

/** Exclude, а не NonNullable: null — валидное значение «сортировка не задана». */
export type TableColumnSort = Exclude<TableColumnState["sort"], undefined>;

// ── Нормализованные типы для потребителей ─────────────────────────
export interface UiTableColumnState {
  sort: TableColumnSort;
  filter: string | null;
}

export interface UiTablePreference {
  column_states: Record<string, UiTableColumnState>;
  search: string;
  page: number;
  page_size: number;
}

export interface UiPreferences {
  user_id: string;
  updated_at: string | null;
  theme: UiThemePreference;
  navigation: { layout: NavigationLayout; sidebar_collapsed: boolean };
  tables: Record<string, UiTablePreference>;
}

// ── Нормализация ──────────────────────────────────────────────────
const normalizeColumnState = (
  raw: TableColumnState | undefined,
): UiTableColumnState => ({
  sort: raw?.sort ?? null,
  filter: raw?.filter ?? null,
});

const normalizeTable = (
  raw: TablePreference | undefined,
): UiTablePreference => ({
  column_states: Object.fromEntries(
    Object.entries(raw?.column_states ?? {}).map(([key, value]) => [
      key,
      normalizeColumnState(value),
    ]),
  ),
  search: raw?.search ?? "",
  page: raw?.page ?? 1,
  page_size: raw?.page_size ?? 15,
});

export const normalizeUiPreferences = (
  // ApiResponse.data в Orval — `T | null | undefined`.
  raw: UiPreferencesResponseSchema | null | undefined,
): UiPreferences => ({
  user_id: raw?.user_id ?? "",
  updated_at: raw?.updated_at ?? null,
  theme: normalizeThemePreference(raw?.theme),
  navigation: {
    layout:
      raw?.navigation?.layout ?? NavigationPreferenceSchemaLayout.sidebar,
    sidebar_collapsed: raw?.navigation?.sidebar_collapsed ?? false,
  },
  tables: Object.fromEntries(
    Object.entries(raw?.tables ?? {}).map(([key, value]) => [
      key,
      normalizeTable(value),
    ]),
  ),
});

export const DEFAULT_UI_PREFERENCES: UiPreferences =
  normalizeUiPreferences(undefined);

/**
 * Оптимистичное слияние патча в нормализованное состояние.
 * Работает напрямую с тем, что рендерит UI, — без обращения к кэшу
 * React Query по ключу, который генерирует Orval.
 * Неизменённые секции сохраняют ссылку, чтобы эффекты не перезапускались.
 */
export const mergeNormalizedPreferences = (
  base: UiPreferences,
  patch: UiPreferencesPatchSchema,
): UiPreferences => {
  const theme: UiThemePreference =
    patch.theme !== undefined && patch.theme !== null
      ? normalizeThemePreference(patch.theme)
      : base.theme;

  const navigation: UiPreferences["navigation"] =
    patch.navigation !== undefined && patch.navigation !== null
      ? {
          layout: patch.navigation.layout ?? base.navigation.layout,
          sidebar_collapsed:
            patch.navigation.sidebar_collapsed ??
            base.navigation.sidebar_collapsed,
        }
      : base.navigation;

  let tables: Record<string, UiTablePreference> = base.tables;
  if (patch.tables !== undefined && patch.tables !== null) {
    tables = { ...base.tables };
    for (const [key, value] of Object.entries(patch.tables)) {
      if (value === null) {
        delete tables[key];
      } else if (value !== undefined) {
        tables[key] = normalizeTable(value);
      }
    }
  }

  return { ...base, theme, navigation, tables };
};

/** Накопление патчей между отправками (для дебаунса табличных настроек). */
export const mergeUiPreferencesPatch = (
  base: UiPreferencesPatchSchema,
  patch: UiPreferencesPatchSchema,
): UiPreferencesPatchSchema => {
  const tables: NonNullable<UiPreferencesPatchSchema["tables"]> = {
    ...(base.tables ?? {}),
    ...(patch.tables ?? {}),
  };
  return {
    theme: patch.theme ?? base.theme,
    navigation: patch.navigation ?? base.navigation,
    tables: Object.keys(tables).length > 0 ? tables : undefined,
  };
};