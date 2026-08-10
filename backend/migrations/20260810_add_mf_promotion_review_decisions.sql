-- Migration: Add mf_promotion_review_decisions
-- Date: 2026-08-10
--
-- Records a human reviewer's decision on a flagged promotion-blocking conflict
-- (e.g. ICICI risk_level disagreeing with the live value, Kotak holdings with no
-- ISIN / an out-of-band percent_aum total) so the promotion job can honor it
-- instead of permanently auto-blocking. This table only ever records a decision;
-- it never itself writes to any runtime table. The actual write to
-- mutual_fund_core_snapshot / mf_scheme_holdings happens through the existing
-- promotion code paths (build_family_invariant_propagation_plan /
-- apply_family_invariant_propagation for risk, the promote_mf_holdings_document_v2
-- RPC for holdings), triggered separately once a decision is recorded.

create extension if not exists pgcrypto;

create table if not exists public.mf_promotion_review_decisions (
  id uuid primary key default gen_random_uuid(),
  amc_code text not null,
  report_month date not null,
  scope text not null check (scope in ('risk', 'holdings')),
  subject_key text not null,
  subject_label text,
  resolution text not null check (resolution in ('use_staged', 'use_live', 'exclude')),
  decided_value jsonb not null default '{}'::jsonb,
  source_document_id uuid references public.mf_raw_documents(id),
  reviewed_by text not null,
  note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  promoted_at timestamptz,
  promoted_by text,
  promotion_result jsonb
);

create unique index if not exists mf_promotion_review_decisions_subject_idx
  on public.mf_promotion_review_decisions (amc_code, report_month, scope, subject_key);

create index if not exists mf_promotion_review_decisions_lookup_idx
  on public.mf_promotion_review_decisions (amc_code, report_month, scope);

alter table public.mf_promotion_review_decisions enable row level security;

revoke all on table public.mf_promotion_review_decisions from public;
revoke all on table public.mf_promotion_review_decisions from anon;
revoke all on table public.mf_promotion_review_decisions from authenticated;

grant select, insert, update, delete on table public.mf_promotion_review_decisions to service_role;
