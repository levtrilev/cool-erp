-- ════════════════════════════════════════════════════════════════
-- ROLLBACK
-- ════════════════════════════════════════════════════════════════

DROP TRIGGER IF EXISTS trg_user_ui_preferences_updated_at
    ON public.user_ui_preferences;

DROP FUNCTION IF EXISTS public.user_ui_preferences_set_updated_at();

-- Индекс PK удаляется вместе с таблицей.
DROP TABLE IF EXISTS public.user_ui_preferences;