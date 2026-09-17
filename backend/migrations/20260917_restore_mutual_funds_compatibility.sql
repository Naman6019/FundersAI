-- Restore the optional legacy mirror used by older scripts and fallback reads.
-- Canonical runtime data remains in mutual_fund_core_snapshot.

create extension if not exists pgcrypto;

create table if not exists public.mutual_funds (
  id uuid primary key default gen_random_uuid(),
  scheme_code bigint not null unique,
  scheme_name text,
  isin text,
  fund_house text,
  category text,
  sub_category text,
  nav numeric(18,6),
  nav_date date,
  expense_ratio numeric(18,6),
  aum numeric(24,4),
  exit_load text,
  benchmark text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.mutual_funds
  add column if not exists isin text,
  add column if not exists expense_ratio numeric(18,6),
  add column if not exists aum numeric(24,4),
  add column if not exists exit_load text,
  add column if not exists benchmark text;

-- NAV-only syncs do not provide enrichment fields.
alter table public.mutual_funds
  alter column fund_house drop not null,
  alter column category drop not null,
  alter column sub_category drop not null;

create index if not exists mutual_funds_updated_at_idx
  on public.mutual_funds (updated_at desc);

alter table public.mutual_funds enable row level security;
revoke all on table public.mutual_funds from public, anon, authenticated;
grant select, insert, update, delete on table public.mutual_funds to service_role;
