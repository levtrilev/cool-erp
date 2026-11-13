// frontend/src/lib/ui-preferences/useTablePreferences.ts
import {
  useCallback,
  useMemo,
  type Dispatch,
  type SetStateAction,
} from "react";
import type { TablePreferenceSchema } from "@/api/generated/coolERP.schemas";
import { useUiPreferences } from "./useUiPreferences";

export interface TablePreferencesConfig<TState extends object> {
  tableKey: string;
  defaultState: TState;
  toStored: (state: TState) => TablePreferenceSchema;
  fromStored: (
    stored: TablePreferenceSchema | undefined,
    defaults: TState,
  ) => TState;
}

export interface TablePreferencesResult<TState extends object> {
  state: TState;
  setState: Dispatch<SetStateAction<TState>>;
  isRestored: boolean;
  resetPreferences: () => void;
}

/**
 * Серверные настройки одной таблицы.
 * Ключ tableKey изолирует таблицы; документ хранится в БД за пользователем.
 * setState мгновенно обновляет оптимистичный кэш, запись на сервер — с дебаунсом.
 */
export function useTablePreferences<TState extends object>(
  config: TablePreferencesConfig<TState>,
): TablePreferencesResult<TState> {
  const { tableKey, defaultState, toStored, fromStored } = config;
  const { preferences, isRestored, patch } = useUiPreferences();

  const stored = preferences.tables[tableKey];
  const state = useMemo<TState>(
    () => fromStored(stored, defaultState),
    [stored, defaultState, fromStored],
  );

  const setState = useCallback<Dispatch<SetStateAction<TState>>>(
    (action) => {
      const next =
        typeof action === "function" ? action(state) : action;
      patch({ tables: { [tableKey]: toStored(next) } });
    },
    [state, patch, tableKey, toStored],
  );

  const resetPreferences = useCallback((): void => {
    patch({ tables: { [tableKey]: null } });
  }, [patch, tableKey]);

  return { state, setState, isRestored, resetPreferences };
}