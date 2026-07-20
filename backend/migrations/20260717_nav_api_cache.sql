BEGIN;

CREATE TABLE IF NOT EXISTS public.nav_api_cache (
    scheme_code TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    point_count INTEGER NOT NULL,
    first_nav_date DATE,
    last_nav_date DATE,
    source TEXT NOT NULL DEFAULT 'mfapi',
    fetched_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT nav_api_cache_payload_is_array CHECK (jsonb_typeof(payload) = 'array'),
    CONSTRAINT nav_api_cache_point_count_non_negative CHECK (point_count >= 0),
    CONSTRAINT nav_api_cache_date_order CHECK (
        first_nav_date IS NULL OR last_nav_date IS NULL OR first_nav_date <= last_nav_date
    )
);

CREATE INDEX IF NOT EXISTS idx_nav_api_cache_expires_at
    ON public.nav_api_cache (expires_at);

CREATE INDEX IF NOT EXISTS idx_nav_api_cache_updated_at
    ON public.nav_api_cache (updated_at);

ALTER TABLE public.nav_api_cache ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.nav_api_cache FROM anon, authenticated;
GRANT ALL ON public.nav_api_cache TO service_role;

COMMENT ON TABLE public.nav_api_cache IS
    'Server-only, on-demand cache of complete MFAPI NAV histories.';

COMMIT;
