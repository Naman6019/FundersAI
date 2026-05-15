-- Additive support for Cloudflare R2 object storage and compaction manifests.

create extension if not exists pgcrypto;

alter table if exists public.mf_raw_documents
  add column if not exists storage_backend text not null default 'local',
  add column if not exists storage_bucket text,
  add column if not exists storage_key text,
  add column if not exists storage_metadata jsonb;

create index if not exists mf_raw_documents_storage_backend_idx
  on public.mf_raw_documents (storage_backend, downloaded_at);

create index if not exists mf_raw_documents_storage_key_idx
  on public.mf_raw_documents (storage_key);

create table if not exists public.mf_r2_archive_manifests (
  id uuid primary key default gen_random_uuid(),
  archive_kind text not null,
  entity_key text not null,
  report_month date,
  storage_bucket text not null,
  storage_key text not null,
  row_count integer not null default 0,
  content_type text,
  checksum text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (archive_kind, entity_key, storage_key)
);

create index if not exists mf_r2_archive_manifests_kind_entity_idx
  on public.mf_r2_archive_manifests (archive_kind, entity_key, created_at desc);

create index if not exists mf_r2_archive_manifests_month_idx
  on public.mf_r2_archive_manifests (report_month desc);
