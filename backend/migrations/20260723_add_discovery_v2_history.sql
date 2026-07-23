alter table public.mf_discovery_runs
  add column if not exists report_sha256 text,
  add column if not exists manifest_sha256 text,
  add column if not exists persistence_state text not null default 'complete'
    check (persistence_state in ('pending', 'r2_report_stored', 'r2_manifest_stored', 'complete', 'failed')),
  add column if not exists persistence_error text,
  add column if not exists persistence_retry_count integer not null default 0
    check (persistence_retry_count >= 0);

create table if not exists public.mf_discovery_documents (
  id uuid primary key default gen_random_uuid(),
  run_id text not null references public.mf_discovery_runs(run_id) on delete cascade,
  amc text not null,
  document_type text not null,
  report_month date,
  source_url text not null,
  discovery_page_url text,
  content_sha256 text,
  readiness text not null check (readiness in ('discovered', 'link_validated', 'probe_passed', 'content_validated', 'parser_smoke_passed', 'promotable', 'needs_review', 'failed')),
  month_confirmation text not null check (month_confirmation in ('confirmed', 'unconfirmed')),
  evidence jsonb not null default '{}'::jsonb,
  observed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (run_id, source_url)
);

create index if not exists mf_discovery_documents_identity_idx
  on public.mf_discovery_documents (amc, document_type, report_month desc, observed_at desc);

alter table public.mf_discovery_documents enable row level security;
revoke all on table public.mf_discovery_documents from public;
revoke all on table public.mf_discovery_documents from anon;
revoke all on table public.mf_discovery_documents from authenticated;
grant select, insert, update, delete on table public.mf_discovery_documents to service_role;
