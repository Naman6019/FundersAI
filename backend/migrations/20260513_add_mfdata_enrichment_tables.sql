-- Schema-only patch for MFdata enrichment.
-- Keep this additive so it can run on the existing legacy mutual_fund_holdings table.

create table if not exists public.mutual_fund_holdings (
  id uuid primary key default gen_random_uuid(),
  scheme_code integer not null,
  as_of_date date,
  security_name text not null,
  isin text,
  sector text,
  weight_pct numeric,
  source text,
  updated_at timestamptz default now(),
  unique (scheme_code, as_of_date, security_name, isin)
);

alter table public.mutual_fund_holdings add column if not exists family_id text;
alter table public.mutual_fund_holdings add column if not exists holding_type text default 'equity';
alter table public.mutual_fund_holdings add column if not exists quantity numeric(24,4);
alter table public.mutual_fund_holdings add column if not exists market_value_cr numeric(24,4);
alter table public.mutual_fund_holdings add column if not exists provider_payload jsonb;

create index if not exists mutual_fund_holdings_scheme_date_idx
  on public.mutual_fund_holdings (scheme_code, as_of_date desc);

create index if not exists mutual_fund_holdings_security_idx
  on public.mutual_fund_holdings (security_name);

create index if not exists mutual_fund_holdings_type_idx
  on public.mutual_fund_holdings (holding_type);

create table if not exists public.mutual_fund_sectors (
  scheme_code text not null,
  family_id text,
  sector text not null,
  weight_pct numeric(18,6),
  stock_count int,
  market_value_cr numeric(24,4),
  source text,
  provider_payload jsonb,
  updated_at timestamptz not null default now(),
  primary key (scheme_code, sector)
);

create index if not exists mutual_fund_sectors_scheme_idx
  on public.mutual_fund_sectors (scheme_code);
