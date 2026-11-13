// frontend/src/lib/ui-preferences/UiPreferencesProvider.tsx
"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import {
  useGetUserPreferencesUserPreferencesGet,
  usePatchUserPreferencesUserPreferencesPatch,
} from "@/api/generated/user-preferences/user-preferences";
import type { UiPreferencesPatchSchema } from "@/api/generated/coolERP.schemas";
import { useToast } from "@/components/ui/use-toast";
import {
  applyNavigationLayout,
  applyTheme,
  readInitialAppearance,
  readNavigationLayoutCookie,
} from "./browserAppearance";
import { useSystemTheme, type ResolvedTheme } from "./useSystemTheme";
import {
  UiPreferencesContext,
  type UiPreferencesContextValue,
} from "./uiPreferencesContext";
import {
  mergeNormalizedPreferences,
  mergeUiPreferencesPatch,
  normalizeUiPreferences,
  type NavigationLayout,
  type UiPreferences,
} from "./types";

const WRITE_DEBOUNCE_MS = 400;

export const UiPreferencesProvider = ({
  children,
}: {
  children: ReactNode;
}) => {
  const { toast } = useToast();
  const { data, isLoading, refetch } = useGetUserPreferencesUserPreferencesGet();
  const { mutateAsync } = usePatchUserPreferencesUserPreferencesPatch();
  const systemTheme: ResolvedTheme = useSystemTheme();

  const serverPreferences: UiPreferences = useMemo(
    () => normalizeUiPreferences(data?.data),
    [data?.data],
  );

  // ✅ Оптимистичный слой живёт в провайдере, а не в кэше React Query.
  // Ключ запроса генерирует Orval (["/user-preferences/"]), поэтому
  // setQueriesData/invalidateQueries по самодельному ключу не находили
  // запрос: PATCH уходил, а состояние UI не обновлялось.
  const [overlay, setOverlay] = useState<UiPreferences | null>(null);
  const preferences: UiPreferences = overlay ?? serverPreferences;

  const isRestored: boolean = !isLoading && data !== undefined;

  const pendingPatchRef = useRef<UiPreferencesPatchSchema>({});
  const timerRef = useRef<number | null>(null);
  const revisionRef = useRef<number>(0);
  const initialAppearanceAppliedRef = useRef<boolean>(false);

  const cancelTimer = useCallback((): void => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const flush = useCallback(async (): Promise<void> => {
    cancelTimer();
    const pending = pendingPatchRef.current;
    if (
      pending.theme === undefined &&
      pending.navigation === undefined &&
      pending.tables === undefined
    ) {
      return;
    }
    pendingPatchRef.current = {};
    const revision: number = revisionRef.current;

    try {
      await mutateAsync({ data: pending });
      // ✅ refetch принадлежит тому же Orval-хуку — ключ знать не нужно.
      await refetch();
      // Снимаем оптимистичный слой, только если за время запроса
      // пользователь не внёс новых изменений.
      if (revisionRef.current === revision) {
        setOverlay(null);
      }
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      toast({
        variant: "destructive",
        title: "Не удалось сохранить настройки интерфейса",
        description:
          err?.response?.data?.detail ||
          "Настройки будут восстановлены с сервера",
      });
      setOverlay(null);
      await refetch();
    }
  }, [cancelTimer, mutateAsync, refetch, toast]);

  const applyPatch = useCallback(
    (nextPatch: UiPreferencesPatchSchema): void => {
      revisionRef.current += 1;
      setOverlay((current) =>
        mergeNormalizedPreferences(current ?? serverPreferences, nextPatch),
      );
      pendingPatchRef.current = mergeUiPreferencesPatch(
        pendingPatchRef.current,
        nextPatch,
      );
    },
    [serverPreferences],
  );

  const patch = useCallback(
    (nextPatch: UiPreferencesPatchSchema): void => {
      applyPatch(nextPatch);
      cancelTimer();
      timerRef.current = window.setTimeout(() => {
        void flush();
      }, WRITE_DEBOUNCE_MS);
    },
    [applyPatch, cancelTimer, flush],
  );

  const patchImmediate = useCallback(
    (nextPatch: UiPreferencesPatchSchema): void => {
      applyPatch(nextPatch);
      cancelTimer();
      void flush();
    },
    [applyPatch, cancelTimer, flush],
  );

  // Первый кадр: оформление из cookie/localStorage, чтобы тема и палитра
  // не «мигали» дефолтом до ответа сервера. Выполняется один раз.
  useEffect(() => {
    if (initialAppearanceAppliedRef.current) return;
    initialAppearanceAppliedRef.current = true;
    applyTheme(readInitialAppearance(), systemTheme);
    const cachedLayout: NavigationLayout | null = readNavigationLayoutCookie();
    if (cachedLayout !== null) applyNavigationLayout(cachedLayout);
  }, [systemTheme]);

  // Источник истины — сервер + оптимистичный слой.
  // Ссылка preferences.theme меняется при каждом выборе в меню,
  // поэтому эффект применяет тему сразу, не дожидаясь ответа PATCH.
  useEffect(() => {
    if (!isRestored) return;
    applyTheme(preferences.theme, systemTheme);
    applyNavigationLayout(preferences.navigation.layout);
  }, [
    isRestored,
    preferences.theme,
    preferences.navigation.layout,
    systemTheme,
  ]);

  // Досыл накопленных изменений при закрытии вкладки и размонтировании.
  useEffect(() => {
    const handleBeforeUnload = (): void => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
        void flush();
      }
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
        void flush();
      }
    };
  }, [flush]);

  const value = useMemo<UiPreferencesContextValue>(
    () => ({ preferences, isRestored, patch, patchImmediate }),
    [preferences, isRestored, patch, patchImmediate],
  );

  return (
    <UiPreferencesContext.Provider value={value}>
      {children}
    </UiPreferencesContext.Provider>
  );
};