-- MANUAL PHASE 2 ONLY.
-- Run only after check_nav_cache_drop_readiness.py reports drop_ready=true.
-- In the same database session, first run:
-- SET fundersai.nav_drop_verified = 'archive-and-observation-verified';

BEGIN;

DO $$
BEGIN
    IF current_setting('fundersai.nav_drop_verified', true) IS DISTINCT FROM 'archive-and-observation-verified' THEN
        RAISE EXCEPTION 'Refusing legacy NAV drop without explicit archive and observation acknowledgement';
    END IF;
    IF to_regclass('public.nav_api_cache') IS NULL THEN
        RAISE EXCEPTION 'nav_api_cache must exist before dropping legacy NAV history';
    END IF;
END $$;

DROP TABLE public.mutual_fund_nav_history;

COMMIT;
