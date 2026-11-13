// frontend/src/lib/ui-preferences/useTablePreferences.ts
import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  type Dispatch,
  type SetStateAction,
} from "react";
import type { TablePreferenceSchema } from "@/api/generated/coolERP.schemas";
import { useUiPreferences } from "./useUiPreferences";
import type { UiTablePreference } from "./types";

export interface TablePreferencesConfig<TState extends object> {
  tableKey: string;
  defaultState: TState;
  toStored: (state: TState) => TablePreferenceSchema;
  fromStored: (
    stored: UiTablePreference | undefined,
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

  const stored: UiTablePreference | undefined = preferences.tables[tableKey];
  const state = useMemo<TState>(
    () => fromStored(stored, defaultState),
    [stored, defaultState, fromStored],
  );

  // ✅ Актуальное состояние с учётом ещё не отрендеренных обновлений.
  // Обработчики страниц вызывают сеттер несколько раз подряд в одном событии
  // (сортировка + сброс страницы, поиск + сброс страницы). Функциональный
  // апдейтер обязан видеть результат предыдущего вызова, иначе второе
  // обновление перезаписывает первое и изменение «теряется».
  const latestRef = useRef<TState>(state);

  // Синхронизация с внешними изменениями: когда производное состояние
  // поменялось не нами (ответ сервера, откат после ошибки PATCH, другая
  // вкладка), принимаем его за новую базу для последующих обновлений.
  useEffect(() => {
    latestRef.current = state;
  }, [state]);

  const setState = useCallback<Dispatch<SetStateAction<TState>>>(
    (action) => {
      const next: TState =
        typeof action === "function"
          ? (action as (prev: TState) => TState)(latestRef.current)
          : action;
      latestRef.current = next;
      patch({ tables: { [tableKey]: toStored(next) } });
    },
    [patch, tableKey, toStored],
  );

  const resetPreferences = useCallback((): void => {
    latestRef.current = defaultState;
    patch({ tables: { [tableKey]: null } });
  }, [patch, tableKey, defaultState]);

  return { state, setState, isRestored, resetPreferences };
}