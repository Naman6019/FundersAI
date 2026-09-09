-- Phase 1: authenticated manual mutual-fund portfolio tracking.
-- This is a position snapshot, not a transaction or external-account import ledger.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.portfolios (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL CHECK (char_length(btrim(name)) BETWEEN 1 AND 80),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS portfolios_user_created_idx
  ON public.portfolios (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS public.portfolio_positions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  portfolio_id UUID NOT NULL REFERENCES public.portfolios(id) ON DELETE CASCADE,
  scheme_code INTEGER NOT NULL CHECK (scheme_code > 0),
  units NUMERIC(24, 8) NOT NULL CHECK (units > 0),
  current_value NUMERIC(24, 4) NOT NULL CHECK (current_value >= 0),
  position_source TEXT NOT NULL DEFAULT 'manual' CHECK (position_source = 'manual'),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (portfolio_id, scheme_code)
);

CREATE INDEX IF NOT EXISTS portfolio_positions_portfolio_idx
  ON public.portfolio_positions (portfolio_id, created_at ASC);

ALTER TABLE public.portfolios ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.portfolio_positions ENABLE ROW LEVEL SECURITY;

-- Do not rely on project default privileges for newly-created public tables.
-- Signed-out clients get no Data API access; authenticated clients get only the
-- operations covered by the ownership policies below.
REVOKE ALL ON TABLE public.portfolios, public.portfolio_positions FROM anon, authenticated;

DROP POLICY IF EXISTS portfolios_select_own ON public.portfolios;
CREATE POLICY portfolios_select_own
  ON public.portfolios
  FOR SELECT TO authenticated
  USING (user_id = (select auth.uid()));

DROP POLICY IF EXISTS portfolios_insert_own ON public.portfolios;
CREATE POLICY portfolios_insert_own
  ON public.portfolios
  FOR INSERT TO authenticated
  WITH CHECK (user_id = (select auth.uid()));

DROP POLICY IF EXISTS portfolios_update_own ON public.portfolios;
CREATE POLICY portfolios_update_own
  ON public.portfolios
  FOR UPDATE TO authenticated
  USING (user_id = (select auth.uid()))
  WITH CHECK (user_id = (select auth.uid()));

DROP POLICY IF EXISTS portfolios_delete_own ON public.portfolios;
CREATE POLICY portfolios_delete_own
  ON public.portfolios
  FOR DELETE TO authenticated
  USING (user_id = (select auth.uid()));

DROP POLICY IF EXISTS portfolio_positions_select_own ON public.portfolio_positions;
CREATE POLICY portfolio_positions_select_own
  ON public.portfolio_positions
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.portfolios
      WHERE portfolios.id = portfolio_positions.portfolio_id
        AND portfolios.user_id = (select auth.uid())
    )
  );

DROP POLICY IF EXISTS portfolio_positions_insert_own ON public.portfolio_positions;
CREATE POLICY portfolio_positions_insert_own
  ON public.portfolio_positions
  FOR INSERT TO authenticated
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.portfolios
      WHERE portfolios.id = portfolio_positions.portfolio_id
        AND portfolios.user_id = (select auth.uid())
    )
  );

DROP POLICY IF EXISTS portfolio_positions_update_own ON public.portfolio_positions;
CREATE POLICY portfolio_positions_update_own
  ON public.portfolio_positions
  FOR UPDATE TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.portfolios
      WHERE portfolios.id = portfolio_positions.portfolio_id
        AND portfolios.user_id = (select auth.uid())
    )
  )
  WITH CHECK (
    EXISTS (
      SELECT 1
      FROM public.portfolios
      WHERE portfolios.id = portfolio_positions.portfolio_id
        AND portfolios.user_id = (select auth.uid())
    )
  );

DROP POLICY IF EXISTS portfolio_positions_delete_own ON public.portfolio_positions;
CREATE POLICY portfolio_positions_delete_own
  ON public.portfolio_positions
  FOR DELETE TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.portfolios
      WHERE portfolios.id = portfolio_positions.portfolio_id
        AND portfolios.user_id = (select auth.uid())
    )
  );

CREATE OR REPLACE FUNCTION public.handle_portfolio_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_portfolios_updated_at ON public.portfolios;
CREATE TRIGGER set_portfolios_updated_at
  BEFORE UPDATE ON public.portfolios
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_portfolio_updated_at();

DROP TRIGGER IF EXISTS set_portfolio_positions_updated_at ON public.portfolio_positions;
CREATE TRIGGER set_portfolio_positions_updated_at
  BEFORE UPDATE ON public.portfolio_positions
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_portfolio_updated_at();

GRANT SELECT, INSERT, UPDATE, DELETE ON public.portfolios TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.portfolio_positions TO authenticated;
GRANT ALL ON public.portfolios TO service_role;
GRANT ALL ON public.portfolio_positions TO service_role;

COMMENT ON TABLE public.portfolios IS
  'User-owned research portfolios. Phase 1 stores manual position snapshots only.';
COMMENT ON TABLE public.portfolio_positions IS
  'Manual mutual-fund positions; transactions and external imports are intentionally out of scope for phase 1.';

COMMIT;
