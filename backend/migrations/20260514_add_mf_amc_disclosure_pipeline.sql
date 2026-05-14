-- AMC disclosure ingestion pipeline (v1)
-- Additive migration for raw document capture, parsing traceability, and normalized holdings.

create extension if not exists pgcrypto;

create table if not exists public.mf_amc_sources (
  amc_code text primary key,
  amc_name text not null,
  listing_url text not null,
  base_url text not null,
  is_enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.mf_raw_documents (
  id uuid primary key default gen_random_uuid(),
  amc_code text not null references public.mf_amc_sources(amc_code),
  source_url text not null,
  file_name text not null,
  storage_path text not null,
  checksum text not null,
  content_type text,
  report_month date,
  parse_status text not null default 'pending',
  validation_issues text[] not null default '{}',
  parser_version text,
  source_document_type text,
  downloaded_at timestamptz,
  parsed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (checksum)
);

create index if not exists mf_raw_documents_amc_month_idx
  on public.mf_raw_documents (amc_code, report_month desc);

create index if not exists mf_raw_documents_status_idx
  on public.mf_raw_documents (parse_status, downloaded_at);

create index if not exists mf_raw_documents_source_url_idx
  on public.mf_raw_documents (source_url);

create table if not exists public.mf_schemes (
  id uuid primary key default gen_random_uuid(),
  amc_code text not null references public.mf_amc_sources(amc_code),
  scheme_name text not null,
  scheme_name_normalized text not null,
  external_scheme_code text,
  match_confidence numeric(5,2),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (amc_code, scheme_name_normalized)
);

create index if not exists mf_schemes_name_idx
  on public.mf_schemes (scheme_name_normalized);

create table if not exists public.mf_scheme_holdings (
  id uuid primary key default gen_random_uuid(),
  scheme_id uuid not null references public.mf_schemes(id),
  report_month date not null,
  instrument_name text not null,
  instrument_name_normalized text,
  isin text,
  sector text,
  percent_aum numeric(12,6),
  quantity numeric(24,6),
  market_value numeric(24,6),
  source_document_id uuid not null references public.mf_raw_documents(id),
  source_url text,
  source_row_hash text not null,
  parser_version text,
  confidence_score numeric(5,2),
  validation_status text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (source_document_id, source_row_hash)
);

create index if not exists mf_scheme_holdings_scheme_month_idx
  on public.mf_scheme_holdings (scheme_id, report_month desc);

create index if not exists mf_scheme_holdings_source_doc_idx
  on public.mf_scheme_holdings (source_document_id);

create table if not exists public.mf_scheme_monthly_metrics (
  id uuid primary key default gen_random_uuid(),
  scheme_id uuid not null references public.mf_schemes(id),
  report_month date not null,
  metric_name text not null,
  metric_value numeric(24,6),
  source_document_id uuid not null references public.mf_raw_documents(id),
  source_url text,
  parser_version text,
  confidence_score numeric(5,2),
  validation_status text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (scheme_id, report_month, metric_name, source_document_id)
);

create index if not exists mf_scheme_monthly_metrics_month_idx
  on public.mf_scheme_monthly_metrics (report_month desc);

create table if not exists public.mf_parse_review_queue (
  id uuid primary key default gen_random_uuid(),
  source_document_id uuid not null references public.mf_raw_documents(id),
  amc_code text not null,
  report_month date,
  validation_issues text[] not null default '{}',
  confidence_score numeric(5,2),
  parser_version text,
  status text not null default 'pending_review',
  reviewer_notes text,
  sample_rows jsonb,
  source_url text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists mf_parse_review_queue_status_idx
  on public.mf_parse_review_queue (status, created_at);
