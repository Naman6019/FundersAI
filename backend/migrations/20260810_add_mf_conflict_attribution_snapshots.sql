-- Migration: Add mf_conflict_attribution_snapshots
-- Date: 2026-08-10
--
-- Append-only time series of the per-AMC conflict-attribution report (see
-- scripts/report_mf_conflict_attribution.py). Each run of
-- scripts/snapshot_mf_conflict_attribution.py inserts one row per AMC recording
-- the conflict counts observed at that moment, broken down by root cause
-- (risk_mismatch, holdings_out_of_band_total, holdings_no_percent_aum_value,
-- holdings_non_valid_status) plus contributing tags (missing_isin,
-- duplicate_across_documents). This is purely observational -- it never writes
-- to any promotion/staging table -- and exists so a parser fix's effect on
-- conflict volume for a given AMC is visible as a trend instead of only ever
-- being a single current snapshot.

create extension if not exists pgcrypto;

create table if not exists public.mf_conflict_attribution_snapshots (
  id uuid primary key default gen_random_uuid(),
  taken_at timestamptz not null default now(),
  report_months date[] not null,
  amc_code text not null,
  total_conflicts integer not null default 0,
  by_cause jsonb not null default '{}'::jsonb,
  contributing_tags jsonb not null default '{}'::jsonb
);

create index if not exists mf_conflict_attribution_snapshots_amc_time_idx
  on public.mf_conflict_attribution_snapshots (amc_code, taken_at desc);

alter table public.mf_conflict_attribution_snapshots enable row level security;

revoke all on table public.mf_conflict_attribution_snapshots from public;
revoke all on table public.mf_conflict_attribution_snapshots from anon;
revoke all on table public.mf_conflict_attribution_snapshots from authenticated;

grant select, insert on table public.mf_conflict_attribution_snapshots to service_role;
