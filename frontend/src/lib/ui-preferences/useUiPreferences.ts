// frontend/src/lib/ui-preferences/useUiPreferences.ts
import { useContext } from "react";
import {
  UiPreferencesContext,
  type UiPreferencesContextValue,
} from "./uiPreferencesContext";

export const useUiPreferences = (): UiPreferencesContextValue => {
  const context = useContext(UiPreferencesContext);
  if (context === null) {
    throw new Error(
      "useUiPreferences должен вызываться внутри UiPreferencesProvider",
    );
  }
  return context;
};