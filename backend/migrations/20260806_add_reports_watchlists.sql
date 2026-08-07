-- Migration: Add Saved Reports and Watchlists tables
-- Date: 2026-08-06

BEGIN;

-- 1. Create Saved Reports Table
CREATE TABLE IF NOT EXISTS public.saved_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    report_title TEXT NOT NULL,
    funds_compared TEXT[] NOT NULL DEFAULT '{}',
    markdown_content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Create Watchlists Table
CREATE TABLE IF NOT EXISTS public.watchlists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    asset_type TEXT NOT NULL CHECK (asset_type IN ('stock', 'mutual_fund')),
    asset_id TEXT NOT NULL, -- The stock symbol or MF scheme code
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Ensure unique assets per user in the watchlist
CREATE UNIQUE INDEX IF NOT EXISTS watchlists_user_asset_idx ON public.watchlists (user_id, asset_type, asset_id);

-- 3. Enable Row Level Security (RLS)
ALTER TABLE public.saved_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.watchlists ENABLE ROW LEVEL SECURITY;

-- 4. RLS Policies for Saved Reports
CREATE POLICY "Users can insert their own saved reports"
    ON public.saved_reports FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view their own saved reports"
    ON public.saved_reports FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own saved reports"
    ON public.saved_reports FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own saved reports"
    ON public.saved_reports FOR DELETE
    USING (auth.uid() = user_id);

-- 5. RLS Policies for Watchlists
CREATE POLICY "Users can insert into their own watchlist"
    ON public.watchlists FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can view their own watchlist"
    ON public.watchlists FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can delete from their own watchlist"
    ON public.watchlists FOR DELETE
    USING (auth.uid() = user_id);

-- 6. Trigger for updated_at on Saved Reports
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS trigger AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_saved_reports_updated_at ON public.saved_reports;
CREATE TRIGGER set_saved_reports_updated_at
    BEFORE UPDATE ON public.saved_reports
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_updated_at();

-- 7. Grant access to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON public.saved_reports TO authenticated;
GRANT SELECT, INSERT, DELETE ON public.watchlists TO authenticated;

-- Ensure service_role has full access
GRANT ALL ON public.saved_reports TO service_role;
GRANT ALL ON public.watchlists TO service_role;

COMMIT;
