create extension if not exists vector;

alter table public.amc_document_chunks
  add column if not exists chunk_hash text,
  add column if not exists embedding_model text,
  add column if not exists embedding_version text,
  add column if not exists parser_version text,
  add column if not exists source_url text;

create unique index if not exists amc_document_chunks_document_hash_idx
  on public.amc_document_chunks (document_id, chunk_hash);

alter table public.amc_document_chunks enable row level security;

revoke all on table public.amc_document_chunks from public;
revoke all on table public.amc_document_chunks from anon;
revoke all on table public.amc_document_chunks from authenticated;

grant select, insert, update, delete on table public.amc_document_chunks to service_role;
