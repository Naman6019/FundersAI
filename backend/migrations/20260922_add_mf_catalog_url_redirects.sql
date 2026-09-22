-- 20260922_add_mf_catalog_url_redirects.sql
--
-- The `freeze_mf_catalog_url` trigger has always raised
--   'Catalog URLs are immutable; use a reviewed redirect migration'
-- but no such mechanism was ever built, so a slug could not be corrected after publication at
-- all. This adds the reviewed redirect path the trigger already points at.
--
-- Why a redirect is needed here: the catalog's original slug generator was
-- `f"{slug(scheme_name)}-{code}"`, which left the share-class metadata in place, so every
-- scheme published after the initial hand-curated batch got a URL like
-- `hdfc-elss-tax-saver-fund-direct-plan-growth-option-119060`. Those are live 200 pages. The
-- generator is fixed, but an existing published URL must never simply change: it has to redirect
-- permanently from the old path, or the change is an unannounced 404 on a page that may be
-- ranking. That is the exact failure mode the design spec calls "the most dangerous failure
-- mode in the design".
--
-- Design: old path -> new path, keyed on the pair that actually identifies a page. Redirects are
-- data, not code, so a future correction is a reviewed INSERT rather than a migration of logic.
--
-- Idempotent: safe to re-run.

begin;

create table if not exists public.mf_catalog_url_redirects (
  id                uuid primary key default gen_random_uuid(),
  scheme_code       text not null,
  from_amc_slug     text not null,
  from_fund_slug    text not null,
  to_amc_slug       text not null,
  to_fund_slug      text not null,
  reason            text not null,
  reviewed_at       timestamptz not null default now(),
  unique (from_amc_slug, from_fund_slug)
);

create index if not exists mf_catalog_url_redirects_scheme_idx
  on public.mf_catalog_url_redirects (scheme_code);

-- Server-only: this is routing metadata, never read by the browser directly.
alter table public.mf_catalog_url_redirects enable row level security;
revoke all on table public.mf_catalog_url_redirects from public, anon, authenticated;
grant select, insert, update, delete on table public.mf_catalog_url_redirects to service_role;

-- ---------------------------------------------------------------------------
-- The reviewed redirects for the 24 pages whose slug drops share-class noise.
--
-- `reason` records why each URL moved, so the mapping is auditable rather than an unexplained
-- URL churn. Each target slug was verified to be unique within its AMC and not to collide with
-- any frozen legacy slug before this migration was written.
-- ---------------------------------------------------------------------------

insert into public.mf_catalog_url_redirects
  (scheme_code, from_amc_slug, from_fund_slug, to_amc_slug, to_fund_slug, reason)
values
  ('119333', 'baroda-bnp-paribas-mutual-fund', 'baroda-bnp-paribas-banking-and-financial-services-fund-direct-plan-growth-option-119333', 'baroda-bnp-paribas-mutual-fund', 'baroda-bnp-paribas-banking-and-financial-services-fund', 'share_class_metadata_removed_from_slug'),
  ('118273', 'canara-robeco-mutual-fund', 'canara-robeco-consumption-fund-direct-plan-growth-option-118273', 'canara-robeco-mutual-fund', 'canara-robeco-consumption-fund', 'share_class_metadata_removed_from_slug'),
  ('118275', 'canara-robeco-mutual-fund', 'canara-robeco-flexi-cap-fund-direct-plan-growth-option-118275', 'canara-robeco-mutual-fund', 'canara-robeco-flexi-cap-fund', 'share_class_metadata_removed_from_slug'),
  ('118267', 'canara-robeco-mutual-fund', 'canara-robeco-infrastructure-fund-direct-plan-growth-option-118267', 'canara-robeco-mutual-fund', 'canara-robeco-infrastructure-fund', 'share_class_metadata_removed_from_slug'),
  ('118278', 'canara-robeco-mutual-fund', 'canara-robeco-large-and-mid-cap-fund-direct-plan-growth-option-118278', 'canara-robeco-mutual-fund', 'canara-robeco-large-and-mid-cap-fund', 'share_class_metadata_removed_from_slug'),
  ('118269', 'canara-robeco-mutual-fund', 'canara-robeco-large-cap-fund-direct-plan-growth-option-118269', 'canara-robeco-mutual-fund', 'canara-robeco-large-cap-fund', 'share_class_metadata_removed_from_slug'),
  ('118285', 'canara-robeco-mutual-fund', 'canara-robeco-elss-tax-saver-fund-direct-plan-growth-option-118285', 'canara-robeco-mutual-fund', 'canara-robeco-elss-tax-saver-fund', 'share_class_metadata_removed_from_slug'),
  ('118620', 'edelweiss-mutual-fund', 'edelweiss-elss-tax-saver-fund-direct-plan-growth-118620', 'edelweiss-mutual-fund', 'edelweiss-elss-tax-saver-fund', 'share_class_metadata_removed_from_slug'),
  ('118617', 'edelweiss-mutual-fund', 'edelweiss-large-cap-fund-direct-plan-growth-118617', 'edelweiss-mutual-fund', 'edelweiss-large-cap-fund', 'share_class_metadata_removed_from_slug'),
  ('119065', 'hdfc', 'hdfc-bse-sensex-index-fund-direct-plan-growth-option-119065', 'hdfc', 'hdfc-bse-sensex-index-fund', 'share_class_metadata_removed_from_slug'),
  ('119060', 'hdfc', 'hdfc-elss-tax-saver-fund-direct-plan-growth-option-119060', 'hdfc', 'hdfc-elss-tax-saver-fund', 'share_class_metadata_removed_from_slug'),
  ('118979', 'hdfc', 'hdfc-infrastructure-fund-direct-plan-growth-option-118979', 'hdfc', 'hdfc-infrastructure-fund', 'share_class_metadata_removed_from_slug'),
  ('119063', 'hdfc', 'hdfc-nifty-50-index-fund-direct-plan-growth-option-119063', 'hdfc', 'hdfc-nifty-50-index-fund', 'share_class_metadata_removed_from_slug'),
  ('120046', 'hsbc-mutual-fund', 'hsbc-flexi-cap-fund-direct-plan-growth-120046', 'hsbc-mutual-fund', 'hsbc-flexi-cap-fund', 'share_class_metadata_removed_from_slug'),
  ('120030', 'hsbc-mutual-fund', 'hsbc-large-cap-fund-direct-plan-growth-120030', 'hsbc-mutual-fund', 'hsbc-large-cap-fund', 'share_class_metadata_removed_from_slug'),
  ('120587', 'icici-prudential', 'icici-prudential-fmcg-fund-direct-plan-growth-120587', 'icici-prudential', 'icici-prudential-fmcg-fund', 'share_class_metadata_removed_from_slug'),
  ('120621', 'icici-prudential', 'icici-prudential-infrastructure-fund-direct-plan-growth-120621', 'icici-prudential', 'icici-prudential-infrastructure-fund', 'share_class_metadata_removed_from_slug'),
  ('120244', 'icici-prudential', 'icici-prudential-banking-and-financial-services-fund-direct-plan-growth-120244', 'icici-prudential', 'icici-prudential-banking-and-financial-services-fund', 'share_class_metadata_removed_from_slug'),
  ('120596', 'icici-prudential', 'icici-prudential-large-and-mid-cap-fund-direct-plan-growth-120596', 'icici-prudential', 'icici-prudential-large-and-mid-cap-fund', 'share_class_metadata_removed_from_slug'),
  ('120592', 'icici-prudential', 'icici-prudential-elss-tax-saver-fund-direct-plan-growth-120592', 'icici-prudential', 'icici-prudential-elss-tax-saver-fund', 'share_class_metadata_removed_from_slug'),
  ('120591', 'icici-prudential', 'icici-prudential-small-cap-fund-direct-plan-growth-120591', 'icici-prudential', 'icici-prudential-small-cap-fund', 'share_class_metadata_removed_from_slug'),
  ('120264', 'lic-mutual-fund', 'lic-mf-flexi-cap-fund-direct-plan-growth-120264', 'lic-mutual-fund', 'lic-mf-flexi-cap-fund', 'share_class_metadata_removed_from_slug'),
  ('111549', 'quantum-mutual-fund', 'quantum-elss-tax-saver-fund-direct-plan-growth-option-111549', 'quantum-mutual-fund', 'quantum-elss-tax-saver-fund', 'share_class_metadata_removed_from_slug'),
  ('119827', 'sbi', 'sbi-nifty-index-fund-direct-plan-growth-119827', 'sbi', 'sbi-nifty-index-fund', 'share_class_metadata_removed_from_slug')
on conflict (from_amc_slug, from_fund_slug) do nothing;

-- ---------------------------------------------------------------------------
-- Apply the slug changes. The freeze trigger fires BEFORE UPDATE, so it is disabled for this
-- transaction only, and only for rows that have a reviewed redirect recorded. Every change is
-- paired with a redirect above, which is what makes moving the URL safe.
-- ---------------------------------------------------------------------------

alter table public.mf_page_catalog disable trigger freeze_mf_catalog_url;

update public.mf_page_catalog as c
set fund_slug = r.to_fund_slug,
    last_evaluated_at = now()
from public.mf_catalog_url_redirects as r
where c.scheme_code = r.scheme_code
  and c.amc_slug = r.from_amc_slug
  and c.fund_slug = r.from_fund_slug;

alter table public.mf_page_catalog enable trigger freeze_mf_catalog_url;

commit;
