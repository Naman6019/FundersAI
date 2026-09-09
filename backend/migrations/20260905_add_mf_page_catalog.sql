BEGIN;
CREATE TABLE IF NOT EXISTS public.mf_page_catalog (
  scheme_code text PRIMARY KEY,
  amc_slug text NOT NULL,
  fund_slug text NOT NULL,
  scheme_name text NOT NULL,
  amc_name text NOT NULL,
  category text,
  is_published boolean NOT NULL DEFAULT false,
  gate_reasons jsonb NOT NULL DEFAULT '[]',
  metrics jsonb NOT NULL DEFAULT '{}',
  last_evaluated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(amc_slug, fund_slug),
  CHECK ((NOT is_published OR (gate_reasons = '[]'::jsonb AND category IS NOT NULL
    AND metrics->>'method_version' = 'catalog_nav_v1'
    AND metrics->>'cagr_1y' IS NOT NULL)) IS TRUE)
);
ALTER TABLE public.mf_page_catalog ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.mf_page_catalog FROM PUBLIC, anon, authenticated;
GRANT SELECT, INSERT, UPDATE ON public.mf_page_catalog TO service_role;
CREATE INDEX IF NOT EXISTS mf_page_catalog_published_idx
  ON public.mf_page_catalog (amc_slug, scheme_code) WHERE is_published;

-- An update can demote a page, but it cannot change an existing URL.
CREATE OR REPLACE FUNCTION public.freeze_mf_catalog_url() RETURNS trigger
LANGUAGE plpgsql SET search_path = public AS $$
BEGIN
  IF OLD.amc_slug IS DISTINCT FROM NEW.amc_slug OR OLD.fund_slug IS DISTINCT FROM NEW.fund_slug THEN
    RAISE EXCEPTION 'Catalog URLs are immutable; use a reviewed redirect migration';
  END IF;
  RETURN NEW;
END;
$$;
DROP TRIGGER IF EXISTS freeze_mf_catalog_url ON public.mf_page_catalog;
CREATE TRIGGER freeze_mf_catalog_url BEFORE UPDATE ON public.mf_page_catalog
  FOR EACH ROW EXECUTE FUNCTION public.freeze_mf_catalog_url();

-- Reserve every existing registry URL without publishing unverified data.
INSERT INTO public.mf_page_catalog (scheme_code, amc_slug, fund_slug, scheme_name, amc_name, gate_reasons) VALUES
('120503', 'hdfc', 'hdfc-flexi-cap-fund', 'HDFC Flexi Cap Fund', 'HDFC Mutual Fund', '["not_evaluated"]'::jsonb),
('119552', 'hdfc', 'hdfc-mid-cap-opportunities-fund', 'HDFC Mid-Cap Opportunities Fund', 'HDFC Mutual Fund', '["not_evaluated"]'::jsonb),
('119598', 'hdfc', 'hdfc-small-cap-fund', 'HDFC Small Cap Fund', 'HDFC Mutual Fund', '["not_evaluated"]'::jsonb),
('119533', 'hdfc', 'hdfc-top-100-fund', 'HDFC Top 100 Fund', 'HDFC Mutual Fund', '["not_evaluated"]'::jsonb),
('122639', 'ppfas', 'parag-parikh-flexi-cap-fund', 'Parag Parikh Flexi Cap Fund', 'PPFAS Mutual Fund', '["not_evaluated"]'::jsonb),
('149021', 'ppfas', 'parag-parikh-elss-tax-saver-fund', 'Parag Parikh ELSS Tax Saver Fund', 'PPFAS Mutual Fund', '["not_evaluated"]'::jsonb),
('118989', 'mirae-asset', 'mirae-asset-emerging-bluechip-fund', 'Mirae Asset Emerging Bluechip Fund', 'Mirae Asset Mutual Fund', '["not_evaluated"]'::jsonb),
('118701', 'mirae-asset', 'mirae-asset-large-cap-fund', 'Mirae Asset Large Cap Fund', 'Mirae Asset Mutual Fund', '["not_evaluated"]'::jsonb),
('147493', 'mirae-asset', 'mirae-asset-midcap-fund', 'Mirae Asset Midcap Fund', 'Mirae Asset Mutual Fund', '["not_evaluated"]'::jsonb),
('125497', 'sbi', 'sbi-small-cap-fund', 'SBI Small Cap Fund', 'SBI Mutual Fund', '["not_evaluated"]'::jsonb),
('119206', 'sbi', 'sbi-bluechip-fund', 'SBI Bluechip Fund', 'SBI Mutual Fund', '["not_evaluated"]'::jsonb),
('119213', 'sbi', 'sbi-contra-fund', 'SBI Contra Fund', 'SBI Mutual Fund', '["not_evaluated"]'::jsonb),
('120586', 'icici-prudential', 'icici-prudential-bluechip-fund', 'ICICI Prudential Bluechip Fund', 'ICICI Prudential Mutual Fund', '["not_evaluated"]'::jsonb),
('120594', 'icici-prudential', 'icici-prudential-technology-fund', 'ICICI Prudential Technology Fund', 'ICICI Prudential Mutual Fund', '["not_evaluated"]'::jsonb),
('120588', 'icici-prudential', 'icici-prudential-value-discovery-fund', 'ICICI Prudential Value Discovery Fund', 'ICICI Prudential Mutual Fund', '["not_evaluated"]'::jsonb),
('118825', 'nippon', 'nippon-india-small-cap-fund', 'Nippon India Small Cap Fund', 'Nippon India Mutual Fund', '["not_evaluated"]'::jsonb),
('118834', 'nippon', 'nippon-india-growth-fund', 'Nippon India Growth Fund', 'Nippon India Mutual Fund', '["not_evaluated"]'::jsonb),
('120847', 'quant', 'quant-small-cap-fund', 'Quant Small Cap Fund', 'Quant Mutual Fund', '["not_evaluated"]'::jsonb),
('120828', 'quant', 'quant-active-fund', 'Quant Active Fund', 'Quant Mutual Fund', '["not_evaluated"]'::jsonb),
('120505', 'kotak', 'kotak-flexi-cap-fund', 'Kotak Flexi Cap Fund', 'Kotak Mahindra Mutual Fund', '["not_evaluated"]'::jsonb),
('120152', 'kotak', 'kotak-emerging-equity-fund', 'Kotak Emerging Equity Fund', 'Kotak Mahindra Mutual Fund', '["not_evaluated"]'::jsonb),
('141870', 'axis', 'axis-flexi-cap-fund', 'Axis Flexi Cap Fund', 'Axis Mutual Fund', '["not_evaluated"]'::jsonb),
('120465', 'axis', 'axis-small-cap-fund', 'Axis Small Cap Fund', 'Axis Mutual Fund', '["not_evaluated"]'::jsonb),
('120716', 'uti', 'uti-nifty-50-index-fund', 'UTI Nifty 50 Index Fund', 'UTI Mutual Fund', '["not_evaluated"]'::jsonb),
('147622', 'motilal-oswal', 'motilal-oswal-midcap-fund', 'Motilal Oswal Midcap Fund', 'Motilal Oswal Mutual Fund', '["not_evaluated"]'::jsonb),
('147890', 'bandhan', 'bandhan-small-cap-fund', 'Bandhan Small Cap Fund', 'Bandhan Mutual Fund', '["not_evaluated"]'::jsonb),
('135781', 'tata', 'tata-digital-india-fund', 'Tata Digital India Fund', 'Tata Mutual Fund', '["not_evaluated"]'::jsonb),
('119270', 'aditya-birla-sun-life', 'aditya-birla-sun-life-frontline-equity-fund', 'Aditya Birla Sun Life Frontline Equity Fund', 'Aditya Birla Sun Life Mutual Fund', '["not_evaluated"]'::jsonb),
('119230', 'dsp', 'dsp-mid-cap-fund', 'DSP Mid Cap Fund', 'DSP Mutual Fund', '["not_evaluated"]'::jsonb)
ON CONFLICT (scheme_code) DO NOTHING;
COMMIT;
