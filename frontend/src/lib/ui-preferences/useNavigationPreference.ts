// frontend/src/lib/ui-preferences/useNavigationPreference.ts
import { useCallback } from "react";
import { useUiPreferences } from "./useUiPreferences";
import type { NavigationLayout } from "./types";

/** Раскладка навигации из серверных настроек пользователя. */
export const useNavigationPreference = () => {
  const { preferences, isRestored, patchImmediate } = useUiPreferences();

  const setLayout = useCallback(
    (layout: NavigationLayout): void =>
      patchImmediate({ navigation: { ...preferences.navigation, layout } }),
    [patchImmediate, preferences.navigation],
  );

  const setSidebarCollapsed = useCallback(
    (collapsed: boolean): void =>
      patchImmediate({
        navigation: { ...preferences.navigation, sidebar_collapsed: collapsed },
      }),
    [patchImmediate, preferences.navigation],
  );

  return {
    layout: preferences.navigation.layout,
    sidebarCollapsed: preferences.navigation.sidebar_collapsed,
    setLayout,
    setSidebarCollapsed,
    isRestored,
  };
};