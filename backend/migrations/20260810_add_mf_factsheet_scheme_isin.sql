-- Preserve a source-labelled mutual-fund unit ISIN separately from holding ISINs.
-- This supports exact Kotak factsheet identity resolution without reusing an
-- underlying security's ISIN or making a new AMFI lookup.

alter table if exists public.mf_factsheet_candidates
  add column if not exists scheme_isin text;

create index if not exists mf_factsheet_candidates_scheme_isin_idx
  on public.mf_factsheet_candidates (amc_code, scheme_isin)
  where scheme_isin is not null;