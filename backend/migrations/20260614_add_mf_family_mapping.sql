CREATE TABLE IF NOT EXISTS public.mutual_fund_family_mapping (
    scheme_code TEXT PRIMARY KEY,
    family_id TEXT NOT NULL,
    confidence NUMERIC,
    source TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Enable RLS and add basic policies
ALTER TABLE public.mutual_fund_family_mapping ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Enable read access for all users" ON public.mutual_fund_family_mapping FOR SELECT USING (true);
CREATE POLICY "Enable insert for authenticated users only" ON public.mutual_fund_family_mapping FOR INSERT WITH CHECK (true);
CREATE POLICY "Enable update for authenticated users only" ON public.mutual_fund_family_mapping FOR UPDATE USING (true);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_mutual_fund_family_mapping_updated_at ON public.mutual_fund_family_mapping;
CREATE TRIGGER update_mutual_fund_family_mapping_updated_at
    BEFORE UPDATE ON public.mutual_fund_family_mapping
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
