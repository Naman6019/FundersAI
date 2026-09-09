-- Phase 3: private, user-owned Fund Truth Check thesis monitoring.
-- Evaluations are append-only; source-change workers may insert but never edit history.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.research_claims (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  original_text TEXT NOT NULL CHECK (char_length(btrim(original_text)) BETWEEN 3 AND 2000),
  normalized_claim JSONB NOT NULL CHECK (jsonb_typeof(normalized_claim) = 'object'),
  resolved_entities JSONB NOT NULL CHECK (jsonb_typeof(resolved_entities) = 'array'),
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS research_claims_user_created_idx
  ON public.research_claims (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS research_claims_active_idx
  ON public.research_claims (active, created_at ASC)
  WHERE active = TRUE;

CREATE TABLE IF NOT EXISTS public.research_claim_evaluations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_id UUID NOT NULL REFERENCES public.research_claims(id) ON DELETE CASCADE,
  verdict TEXT NOT NULL CHECK (verdict IN ('supported', 'contradicted', 'mixed', 'unverifiable')),
  freshness TEXT NOT NULL CHECK (freshness IN ('current', 'stale', 'unknown')),
  result JSONB NOT NULL CHECK (jsonb_typeof(result) = 'object'),
  evidence JSONB NOT NULL CHECK (jsonb_typeof(evidence) = 'array'),
  source_fingerprint TEXT NOT NULL CHECK (source_fingerprint ~ '^[a-f0-9]{64}$'),
  evaluated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (claim_id, source_fingerprint)
);

CREATE INDEX IF NOT EXISTS research_claim_evaluations_claim_time_idx
  ON public.research_claim_evaluations (claim_id, evaluated_at DESC);

ALTER TABLE public.research_claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.research_claim_evaluations ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.research_claims, public.research_claim_evaluations
  FROM anon, authenticated;
REVOKE ALL ON TABLE public.research_claims, public.research_claim_evaluations
  FROM service_role;

DROP POLICY IF EXISTS research_claims_select_own ON public.research_claims;
CREATE POLICY research_claims_select_own
  ON public.research_claims
  FOR SELECT TO authenticated
  USING (user_id = (SELECT auth.uid()));

DROP POLICY IF EXISTS research_claims_update_active_own ON public.research_claims;
CREATE POLICY research_claims_update_active_own
  ON public.research_claims
  FOR UPDATE TO authenticated
  USING (user_id = (SELECT auth.uid()))
  WITH CHECK (user_id = (SELECT auth.uid()));

DROP POLICY IF EXISTS research_claim_evaluations_select_own ON public.research_claim_evaluations;
CREATE POLICY research_claim_evaluations_select_own
  ON public.research_claim_evaluations
  FOR SELECT TO authenticated
  USING (
    EXISTS (
      SELECT 1
      FROM public.research_claims
      WHERE research_claims.id = research_claim_evaluations.claim_id
        AND research_claims.user_id = (SELECT auth.uid())
    )
  );

GRANT SELECT ON public.research_claims TO authenticated;
GRANT UPDATE (active) ON public.research_claims TO authenticated;
GRANT SELECT ON public.research_claim_evaluations TO authenticated;

GRANT SELECT, INSERT, UPDATE ON public.research_claims TO service_role;
GRANT SELECT, INSERT ON public.research_claim_evaluations TO service_role;

CREATE OR REPLACE FUNCTION public.save_research_claim_with_evaluation(
  p_user_id UUID,
  p_original_text TEXT,
  p_normalized_claim JSONB,
  p_resolved_entities JSONB,
  p_verdict TEXT,
  p_freshness TEXT,
  p_result JSONB,
  p_evidence JSONB,
  p_source_fingerprint TEXT
)
RETURNS UUID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  saved_claim_id UUID;
BEGIN
  INSERT INTO public.research_claims (
    user_id,
    original_text,
    normalized_claim,
    resolved_entities
  ) VALUES (
    p_user_id,
    p_original_text,
    p_normalized_claim,
    p_resolved_entities
  )
  RETURNING id INTO saved_claim_id;

  INSERT INTO public.research_claim_evaluations (
    claim_id,
    verdict,
    freshness,
    result,
    evidence,
    source_fingerprint
  ) VALUES (
    saved_claim_id,
    p_verdict,
    p_freshness,
    p_result,
    p_evidence,
    p_source_fingerprint
  );

  RETURN saved_claim_id;
END;
$$;

REVOKE ALL ON FUNCTION public.save_research_claim_with_evaluation(
  UUID, TEXT, JSONB, JSONB, TEXT, TEXT, JSONB, JSONB, TEXT
) FROM PUBLIC, anon, authenticated;

GRANT EXECUTE ON FUNCTION public.save_research_claim_with_evaluation(
  UUID, TEXT, JSONB, JSONB, TEXT, TEXT, JSONB, JSONB, TEXT
) TO service_role;

CREATE OR REPLACE FUNCTION public.list_active_research_claims_for_source_change(
  p_limit INTEGER DEFAULT 200
)
RETURNS TABLE (
  id UUID,
  original_text TEXT,
  normalized_claim JSONB,
  resolved_entities JSONB,
  latest_evidence JSONB,
  latest_source_fingerprint TEXT
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $$
  SELECT
    claim.id,
    claim.original_text,
    claim.normalized_claim,
    claim.resolved_entities,
    latest.evidence,
    latest.source_fingerprint
  FROM public.research_claims AS claim
  LEFT JOIN LATERAL (
    SELECT evaluation.evidence, evaluation.source_fingerprint
    FROM public.research_claim_evaluations AS evaluation
    WHERE evaluation.claim_id = claim.id
    ORDER BY evaluation.evaluated_at DESC, evaluation.id DESC
    LIMIT 1
  ) AS latest ON TRUE
  WHERE claim.active = TRUE
  ORDER BY claim.created_at ASC
  LIMIT GREATEST(1, LEAST(COALESCE(p_limit, 200), 500));
$$;

REVOKE ALL ON FUNCTION public.list_active_research_claims_for_source_change(INTEGER)
  FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.list_active_research_claims_for_source_change(INTEGER)
  TO service_role;

COMMENT ON TABLE public.research_claims IS
  'Private user-owned Fund Truth Check theses. Deactivation preserves evaluation history.';

COMMENT ON TABLE public.research_claim_evaluations IS
  'Append-only deterministic thesis evaluations. A new row is written only for a new aggregate source fingerprint.';

COMMIT;
