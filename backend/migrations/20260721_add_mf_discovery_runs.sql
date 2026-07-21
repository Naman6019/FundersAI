create extension if not exists pgcrypto;

create table if not exists public.mf_discovery_runs (
  id uuid primary key default gen_random_uuid(),
  run_id text not null unique,
  trigger_source text not null,
  status text not null check (status in ('completed', 'partial', 'escalated', 'failed')),
  expected_month date,
  document_types text[] not null default '{}',
  requested_amcs text[] not null default '{}',
  agent_status_counts jsonb not null default '{}'::jsonb,
  completed_agent_count integer not null default 0 check (completed_agent_count >= 0),
  document_count integer not null default 0 check (document_count >= 0),
  report_bucket text not null,
  report_key text not null,
  manifest_bucket text not null,
  manifest_key text not null,
  started_at timestamptz,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists mf_discovery_runs_completed_at_idx
  on public.mf_discovery_runs (completed_at desc);

alter table public.mf_discovery_runs enable row level security;

revoke all on table public.mf_discovery_runs from public;
revoke all on table public.mf_discovery_runs from anon;
revoke all on table public.mf_discovery_runs from authenticated;

grant select, insert, update, delete on table public.mf_discovery_runs to service_role;
