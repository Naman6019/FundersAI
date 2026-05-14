-- PPFAS source discovery + confirmation metadata updates
-- additive only

alter table if exists public.mf_amc_sources
  add column if not exists adapter_key text,
  add column if not exists factsheet_page_url text,
  add column if not exists portfolio_disclosure_page_url text,
  add column if not exists requires_confirmation boolean not null default false,
  add column if not exists confirmation_type text,
  add column if not exists confirmation_notes text;

alter table if exists public.mf_raw_documents
  add column if not exists discovery_page_url text,
  add column if not exists amc_name text,
  add column if not exists document_type text,
  add column if not exists file_ext text,
  add column if not exists file_size_bytes bigint;

insert into public.mf_amc_sources (
  amc_name,
  amc_code,
  listing_url,
  base_url,
  adapter_key,
  factsheet_page_url,
  portfolio_disclosure_page_url,
  requires_confirmation,
  confirmation_type,
  confirmation_notes,
  is_enabled,
  updated_at
)
values (
  'Parag Parikh Mutual Fund',
  'PPFAS',
  'https://amc.ppfas.com/downloads/factsheet/',
  'https://amc.ppfas.com',
  'ppfas',
  'https://amc.ppfas.com/downloads/factsheet/',
  'https://amc.ppfas.com/downloads/factsheet/',
  true,
  'indian_citizen_confirmation',
  'Downloads and statutory disclosure pages may require confirming Indian citizen eligibility before access.',
  true,
  now()
)
on conflict (amc_code) do update
set
  amc_name = excluded.amc_name,
  listing_url = excluded.listing_url,
  base_url = excluded.base_url,
  adapter_key = excluded.adapter_key,
  factsheet_page_url = excluded.factsheet_page_url,
  portfolio_disclosure_page_url = excluded.portfolio_disclosure_page_url,
  requires_confirmation = excluded.requires_confirmation,
  confirmation_type = excluded.confirmation_type,
  confirmation_notes = excluded.confirmation_notes,
  is_enabled = excluded.is_enabled,
  updated_at = now();
