-- Staging-first AMC extraction and explicit, scoped promotion.
-- This migration is additive. Applying it does not promote any data.

create extension if not exists pgcrypto;

alter table if exists public.mutual_fund_core_snapshot
  add column if not exists fund_manager text;

alter table if exists public.mf_scheme_holdings
  add column if not exists raw_scheme_name text,
  add column if not exists mapped_scheme_code text,
  add column if not exists mapped_family_id text,
  add column if not exists mapping_confidence numeric(5,2),
  add column if not exists mapping_status text not null default 'unmapped'
    check (mapping_status in ('unmapped', 'mapped', 'ambiguous', 'needs_review', 'rejected'));

create index if not exists mf_scheme_holdings_mapping_idx
  on public.mf_scheme_holdings (source_document_id, mapping_status, mapped_scheme_code);

create table if not exists public.mf_factsheet_candidates (
  id uuid primary key default gen_random_uuid(),
  source_document_id uuid not null references public.mf_raw_documents(id) on delete cascade,
  amc_code text not null references public.mf_amc_sources(amc_code),
  report_month date,
  raw_scheme_name text not null,
  normalized_scheme_name text not null,
  mapped_scheme_code text,
  mapped_family_id text,
  mapping_confidence numeric(5,2),
  mapping_status text not null default 'unmapped'
    check (mapping_status in ('unmapped', 'mapped', 'ambiguous', 'needs_review', 'rejected')),
  aum numeric,
  expense_ratio numeric,
  benchmark text,
  fund_manager text,
  risk_level text,
  validation_issues text[] not null default '{}',
  source_url text,
  storage_bucket text,
  storage_key text,
  checksum text,
  parser_version text,
  extractor_type text not null default 'deterministic',
  extractor_model text,
  extractor_confidence numeric(5,2),
  promotion_status text not null default 'staged'
    check (promotion_status in ('staged', 'needs_review', 'rejected', 'partially_promoted', 'promoted')),
  promoted_scopes text[] not null default '{}',
  staged_at timestamptz not null default now(),
  promoted_at timestamptz,
  updated_at timestamptz not null default now(),
  unique (source_document_id, normalized_scheme_name)
);

create index if not exists mf_factsheet_candidates_review_idx
  on public.mf_factsheet_candidates (amc_code, report_month desc, mapping_status, promotion_status);

create table if not exists public.mf_promotion_runs (
  id uuid primary key default gen_random_uuid(),
  source_document_id uuid not null references public.mf_raw_documents(id),
  candidate_id uuid references public.mf_factsheet_candidates(id),
  amc_code text not null,
  scopes text[] not null,
  apply_requested boolean not null default false,
  status text not null
    check (status in ('dry_run', 'applied', 'rejected', 'failed')),
  requested_by text not null,
  validation_report jsonb not null default '{}'::jsonb,
  before_snapshot jsonb not null default '{}'::jsonb,
  after_snapshot jsonb not null default '{}'::jsonb,
  error_message text,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create index if not exists mf_promotion_runs_document_idx
  on public.mf_promotion_runs (source_document_id, created_at desc);

alter table if exists public.mf_discovery_documents
  add column if not exists canonical_url text,
  add column if not exists etag text,
  add column if not exists last_modified text,
  add column if not exists raw_document_id uuid references public.mf_raw_documents(id);

create index if not exists mf_discovery_documents_canonical_idx
  on public.mf_discovery_documents (amc, document_type, report_month, canonical_url);

alter table public.mf_factsheet_candidates enable row level security;
alter table public.mf_promotion_runs enable row level security;

revoke all on table public.mf_factsheet_candidates from public, anon, authenticated;
revoke all on table public.mf_promotion_runs from public, anon, authenticated;
grant select, insert, update, delete on table public.mf_factsheet_candidates to service_role;
grant select, insert, update, delete on table public.mf_promotion_runs to service_role;

create or replace function public.mf_snapshot_matches_amc(p_amc_code text, p_amc_name text)
returns boolean
language sql
immutable
as $$
  select case lower(coalesce(p_amc_code, ''))
    when 'hdfc' then lower(coalesce(p_amc_name, '')) like '%hdfc%'
    when 'sbi' then lower(coalesce(p_amc_name, '')) like '%sbi%'
    when 'icici' then lower(coalesce(p_amc_name, '')) like '%icici%'
    when 'axis' then lower(coalesce(p_amc_name, '')) like '%axis%'
    when 'ppfas' then lower(coalesce(p_amc_name, '')) like any(array['%ppfas%', '%parag parikh%'])
    when 'nippon' then lower(coalesce(p_amc_name, '')) like '%nippon%'
    when 'motilal' then lower(coalesce(p_amc_name, '')) like '%motilal%'
    when 'mirae' then lower(coalesce(p_amc_name, '')) like '%mirae%'
    when 'uti' then lower(coalesce(p_amc_name, '')) like '%uti%'
    when 'dsp' then lower(coalesce(p_amc_name, '')) like '%dsp%'
    when 'kotak' then lower(coalesce(p_amc_name, '')) like '%kotak%'
    when 'absl' then lower(coalesce(p_amc_name, '')) like any(array['%aditya birla%', '%birla sun life%'])
    else false
  end
$$;

revoke all on function public.mf_snapshot_matches_amc(text, text) from public, anon, authenticated;
grant execute on function public.mf_snapshot_matches_amc(text, text) to service_role;

create or replace function public.promote_mf_factsheet_candidate(
  p_candidate_id uuid,
  p_scopes text[],
  p_requested_by text,
  p_expected_report_month date
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  candidate public.mf_factsheet_candidates%rowtype;
  source_row public.mf_raw_documents%rowtype;
  mapping_family text;
  snapshot_before jsonb;
  snapshot_after jsonb;
  allowed_scopes constant text[] := array['risk', 'ter_aum', 'benchmark', 'manager'];
  requested_scopes text[];
  trace jsonb;
begin
  select * into candidate
  from public.mf_factsheet_candidates
  where id = p_candidate_id
  for update;

  if candidate.id is null then
    raise exception 'candidate_not_found';
  end if;
  select * into source_row
  from public.mf_raw_documents
  where id = candidate.source_document_id;
  if source_row.id is null then
    raise exception 'source_document_not_found';
  end if;
  if candidate.mapping_status <> 'mapped'
     or candidate.mapped_scheme_code is null
     or candidate.mapped_family_id is null
     or coalesce(candidate.mapping_confidence, 0) < 90 then
    raise exception 'candidate_mapping_not_promotable';
  end if;
  if candidate.report_month is null then
    raise exception 'candidate_report_month_missing';
  end if;
  if p_expected_report_month is null
     or candidate.report_month is distinct from p_expected_report_month
     or source_row.report_month is distinct from p_expected_report_month then
    raise exception 'candidate_report_month_mismatch';
  end if;
  if lower(candidate.amc_code) is distinct from lower(source_row.amc_code) then
    raise exception 'candidate_source_amc_mismatch';
  end if;
  if candidate.checksum is distinct from source_row.checksum
     or candidate.storage_key is distinct from source_row.storage_key
     or lower(coalesce(source_row.storage_backend, '')) <> 'r2'
     or source_row.storage_key is null
     or source_row.checksum is null then
    raise exception 'candidate_source_evidence_changed';
  end if;

  select family_id into mapping_family
  from public.mutual_fund_family_mapping
  where scheme_code = candidate.mapped_scheme_code;
  if mapping_family is distinct from candidate.mapped_family_id then
    raise exception 'candidate_mapping_changed';
  end if;

  select coalesce(array_agg(distinct scope), '{}')
  into requested_scopes
  from unnest(coalesce(p_scopes, '{}')) scope
  where scope = any(allowed_scopes);
  if cardinality(requested_scopes) = 0 then
    raise exception 'promotion_scope_required';
  end if;
  if 'risk' = any(requested_scopes) and candidate.risk_level is null then
    raise exception 'candidate_scope_value_missing:risk';
  end if;
  if 'ter_aum' = any(requested_scopes)
     and (candidate.expense_ratio is null or candidate.aum is null) then
    raise exception 'candidate_scope_value_missing:ter_aum';
  end if;
  if 'benchmark' = any(requested_scopes) and candidate.benchmark is null then
    raise exception 'candidate_scope_value_missing:benchmark';
  end if;
  if 'manager' = any(requested_scopes) and candidate.fund_manager is null then
    raise exception 'candidate_scope_value_missing:manager';
  end if;

  select to_jsonb(s) into snapshot_before
  from public.mutual_fund_core_snapshot s
  where s.scheme_code = candidate.mapped_scheme_code;
  if snapshot_before is null then
    raise exception 'mapped_scheme_snapshot_missing';
  end if;
  if not public.mf_snapshot_matches_amc(candidate.amc_code, snapshot_before->>'amc_name') then
    raise exception 'candidate_amc_mismatch';
  end if;

  trace := coalesce(snapshot_before->'provider_payload', '{}'::jsonb);
  trace := jsonb_set(
    trace,
    '{amc_staged_promotion}',
    jsonb_build_object(
      'candidate_id', candidate.id,
      'source_document_id', candidate.source_document_id,
      'report_month', candidate.report_month,
      'scopes', requested_scopes,
      'requested_by', p_requested_by,
      'promoted_at', now()
    ),
    true
  );

  update public.mutual_fund_core_snapshot
  set
    risk_level = case when 'risk' = any(requested_scopes) and candidate.risk_level is not null
      then candidate.risk_level else risk_level end,
    expense_ratio = case when 'ter_aum' = any(requested_scopes) and candidate.expense_ratio is not null
      then candidate.expense_ratio else expense_ratio end,
    aum = case when 'ter_aum' = any(requested_scopes) and candidate.aum is not null
      then candidate.aum else aum end,
    benchmark = case when 'benchmark' = any(requested_scopes) and candidate.benchmark is not null
      then candidate.benchmark else benchmark end,
    fund_manager = case when 'manager' = any(requested_scopes) and candidate.fund_manager is not null
      then candidate.fund_manager else fund_manager end,
    provider_payload = trace,
    last_updated = now()
  where scheme_code = candidate.mapped_scheme_code;

  select to_jsonb(s) into snapshot_after
  from public.mutual_fund_core_snapshot s
  where s.scheme_code = candidate.mapped_scheme_code;

  update public.mf_factsheet_candidates
  set promoted_scopes = (
        select array_agg(distinct scope)
        from unnest(coalesce(promoted_scopes, '{}') || requested_scopes) scope
      ),
      promotion_status = case
        when array['risk', 'ter_aum', 'benchmark', 'manager'] <@ (
          select array_agg(distinct scope)
          from unnest(coalesce(promoted_scopes, '{}') || requested_scopes) scope
        ) then 'promoted'
        else 'partially_promoted'
      end,
      promoted_at = now(),
      updated_at = now()
  where id = candidate.id;

  insert into public.mf_promotion_runs (
    source_document_id, candidate_id, amc_code, scopes, apply_requested,
    status, requested_by, validation_report, before_snapshot, after_snapshot, completed_at
  ) values (
    candidate.source_document_id, candidate.id, candidate.amc_code, requested_scopes, true,
    'applied', p_requested_by,
    jsonb_build_object('mapping_revalidated', true, 'report_month', candidate.report_month),
    coalesce(snapshot_before, '{}'::jsonb), coalesce(snapshot_after, '{}'::jsonb), now()
  );

  return jsonb_build_object(
    'status', 'applied',
    'candidate_id', candidate.id,
    'scheme_code', candidate.mapped_scheme_code,
    'scopes', requested_scopes
  );
end;
$$;

revoke all on function public.promote_mf_factsheet_candidate(uuid, text[], text, date) from public, anon, authenticated;
grant execute on function public.promote_mf_factsheet_candidate(uuid, text[], text, date) to service_role;

create or replace function public.promote_mf_holdings_document(
  p_source_document_id uuid,
  p_scopes text[],
  p_requested_by text,
  p_expected_report_month date
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  source_row public.mf_raw_documents%rowtype;
  invalid_count integer;
  valid_count integer;
  holding_count integer := 0;
  sector_count integer := 0;
  requested_scopes text[];
begin
  select * into source_row
  from public.mf_raw_documents
  where id = p_source_document_id
  for update;
  if source_row.id is null then
    raise exception 'source_document_not_found';
  end if;
  if source_row.report_month is null then
    raise exception 'source_report_month_missing';
  end if;
  if p_expected_report_month is null
     or source_row.report_month is distinct from p_expected_report_month then
    raise exception 'source_report_month_mismatch';
  end if;
  if lower(coalesce(source_row.storage_backend, '')) <> 'r2'
     or source_row.storage_key is null
     or source_row.checksum is null then
    raise exception 'source_r2_evidence_missing';
  end if;

  select coalesce(array_agg(distinct scope), '{}')
  into requested_scopes
  from unnest(coalesce(p_scopes, '{}')) scope
  where scope in ('holdings', 'sectors');
  if cardinality(requested_scopes) = 0 then
    raise exception 'promotion_scope_required';
  end if;

  select count(*) into invalid_count
  from public.mf_scheme_holdings h
  left join public.mutual_fund_family_mapping m
    on m.scheme_code = h.mapped_scheme_code
  left join public.mutual_fund_core_snapshot s
    on s.scheme_code = h.mapped_scheme_code
  where h.source_document_id = p_source_document_id
    and (
      h.mapping_status <> 'mapped'
      or h.mapped_scheme_code is null
      or h.mapped_family_id is null
      or coalesce(h.mapping_confidence, 0) < 90
      or m.family_id is distinct from h.mapped_family_id
      or not public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
      or h.report_month is distinct from source_row.report_month
      or h.mapped_scheme_code !~ '^[0-9]+$'
    );
  if not exists (
    select 1 from public.mf_scheme_holdings
    where source_document_id = p_source_document_id
  ) then
    raise exception 'staged_holdings_missing';
  end if;
  select count(*) into valid_count
  from public.mf_scheme_holdings h
  join public.mutual_fund_family_mapping m
    on m.scheme_code = h.mapped_scheme_code
   and m.family_id = h.mapped_family_id
  join public.mutual_fund_core_snapshot s
    on s.scheme_code = h.mapped_scheme_code
  where h.source_document_id = p_source_document_id
    and h.mapping_status = 'mapped'
    and h.mapped_scheme_code is not null
    and h.mapped_family_id is not null
    and coalesce(h.mapping_confidence, 0) >= 90
    and public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
    and h.report_month = source_row.report_month
    and h.mapped_scheme_code ~ '^[0-9]+$';
  if valid_count = 0 then
    raise exception 'staged_holdings_have_no_promotable_rows';
  end if;

  if 'holdings' = any(requested_scopes) then
    delete from public.mutual_fund_holdings runtime
    where runtime.source = 'amc_disclosure'
      and runtime.as_of_date = source_row.report_month
      and runtime.scheme_code in (
        select distinct h.mapped_scheme_code::integer
        from public.mf_scheme_holdings h
        join public.mutual_fund_family_mapping m
          on m.scheme_code = h.mapped_scheme_code
         and m.family_id = h.mapped_family_id
        join public.mutual_fund_core_snapshot s
          on s.scheme_code = h.mapped_scheme_code
        where h.source_document_id = p_source_document_id
          and h.mapping_status = 'mapped'
          and coalesce(h.mapping_confidence, 0) >= 90
          and public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
          and h.report_month = source_row.report_month
          and h.mapped_scheme_code ~ '^[0-9]+$'
      );

    insert into public.mutual_fund_holdings (
      scheme_code, family_id, as_of_date, security_name, isin, sector,
      weight_pct, quantity, market_value_cr, source, provider_payload, updated_at
    )
    select
      h.mapped_scheme_code::integer,
      h.mapped_family_id,
      h.report_month,
      h.instrument_name,
      nullif(h.isin, ''),
      nullif(h.sector, ''),
      h.percent_aum,
      h.quantity,
      h.market_value / 10000000.0,
      'amc_disclosure',
      jsonb_build_object(
        'source_document_id', h.source_document_id,
        'source_url', h.source_url,
        'parser_version', h.parser_version,
        'raw_scheme_name', h.raw_scheme_name
      ),
      now()
    from public.mf_scheme_holdings h
    join public.mutual_fund_family_mapping m
      on m.scheme_code = h.mapped_scheme_code
     and m.family_id = h.mapped_family_id
    join public.mutual_fund_core_snapshot s
      on s.scheme_code = h.mapped_scheme_code
    where h.source_document_id = p_source_document_id
      and h.mapping_status = 'mapped'
      and coalesce(h.mapping_confidence, 0) >= 90
      and public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
      and h.report_month = source_row.report_month
      and h.mapped_scheme_code ~ '^[0-9]+$'
    on conflict (scheme_code, as_of_date, security_name, isin)
    do update set
      family_id = excluded.family_id,
      sector = excluded.sector,
      weight_pct = excluded.weight_pct,
      quantity = excluded.quantity,
      market_value_cr = excluded.market_value_cr,
      source = excluded.source,
      provider_payload = excluded.provider_payload,
      updated_at = excluded.updated_at;
    get diagnostics holding_count = row_count;
  end if;

  if 'sectors' = any(requested_scopes) then
    delete from public.mutual_fund_sectors runtime
    where runtime.source = 'amc_disclosure'
      and runtime.scheme_code in (
        select distinct h.mapped_scheme_code
        from public.mf_scheme_holdings h
        join public.mutual_fund_family_mapping m
          on m.scheme_code = h.mapped_scheme_code
         and m.family_id = h.mapped_family_id
        join public.mutual_fund_core_snapshot s
          on s.scheme_code = h.mapped_scheme_code
        where h.source_document_id = p_source_document_id
          and h.mapping_status = 'mapped'
          and coalesce(h.mapping_confidence, 0) >= 90
          and public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
          and h.report_month = source_row.report_month
          and h.mapped_scheme_code ~ '^[0-9]+$'
      );

    insert into public.mutual_fund_sectors (
      scheme_code, family_id, sector, weight_pct, stock_count,
      source, provider_payload, updated_at
    )
    select
      h.mapped_scheme_code,
      h.mapped_family_id,
      coalesce(nullif(trim(h.sector), ''), 'Unclassified'),
      sum(coalesce(h.percent_aum, 0)),
      count(*),
      'amc_disclosure',
      jsonb_build_object(
        'source_document_id', p_source_document_id,
        'report_month', source_row.report_month
      ),
      now()
    from public.mf_scheme_holdings h
    join public.mutual_fund_family_mapping m
      on m.scheme_code = h.mapped_scheme_code
     and m.family_id = h.mapped_family_id
    join public.mutual_fund_core_snapshot s
      on s.scheme_code = h.mapped_scheme_code
    where h.source_document_id = p_source_document_id
      and h.mapping_status = 'mapped'
      and coalesce(h.mapping_confidence, 0) >= 90
      and public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
      and h.report_month = source_row.report_month
      and h.mapped_scheme_code ~ '^[0-9]+$'
    group by h.mapped_scheme_code, h.mapped_family_id, coalesce(nullif(trim(h.sector), ''), 'Unclassified')
    on conflict (scheme_code, sector)
    do update set
      family_id = excluded.family_id,
      weight_pct = excluded.weight_pct,
      stock_count = excluded.stock_count,
      source = excluded.source,
      provider_payload = excluded.provider_payload,
      updated_at = excluded.updated_at;
    get diagnostics sector_count = row_count;
  end if;

  insert into public.mf_promotion_runs (
    source_document_id, amc_code, scopes, apply_requested, status, requested_by,
    validation_report, after_snapshot, completed_at
  ) values (
    p_source_document_id, source_row.amc_code, requested_scopes, true, 'applied', p_requested_by,
    jsonb_build_object(
      'mapping_revalidated', true,
      'report_month', source_row.report_month,
      'valid_staged_rows', valid_count,
      'rejected_staged_rows', invalid_count
    ),
    jsonb_build_object('holdings_rows', holding_count, 'sector_rows', sector_count),
    now()
  );

  return jsonb_build_object(
    'status', 'applied',
    'source_document_id', p_source_document_id,
    'scopes', requested_scopes,
    'holdings_rows', holding_count,
    'sector_rows', sector_count,
    'valid_staged_rows', valid_count,
    'rejected_staged_rows', invalid_count
  );
end;
$$;

revoke all on function public.promote_mf_holdings_document(uuid, text[], text, date) from public, anon, authenticated;
grant execute on function public.promote_mf_holdings_document(uuid, text[], text, date) to service_role;
