-- Stage official aggregate sector allocations separately from security holdings.
-- Applying this migration does not promote any data.

create table if not exists public.mf_scheme_sector_allocations (
  id uuid primary key default gen_random_uuid(),
  scheme_id uuid not null references public.mf_schemes(id),
  report_month date not null,
  sector_name text not null,
  sector_name_normalized text not null,
  weight_pct numeric(12,6) not null check (weight_pct > 0 and weight_pct <= 100),
  source_document_id uuid not null references public.mf_raw_documents(id) on delete cascade,
  source_url text,
  source_row_hash text not null,
  parser_version text,
  confidence_score numeric(5,2),
  validation_status text not null
    check (validation_status in ('valid', 'needs_review', 'invalid')),
  raw_scheme_name text not null,
  mapped_scheme_code text,
  mapped_family_id text,
  mapping_confidence numeric(5,2),
  mapping_status text not null default 'unmapped'
    check (mapping_status in ('unmapped', 'mapped', 'ambiguous', 'needs_review', 'rejected')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (source_document_id, source_row_hash)
);

create index if not exists mf_scheme_sector_allocations_mapping_idx
  on public.mf_scheme_sector_allocations (
    source_document_id,
    report_month,
    mapping_status,
    mapped_scheme_code
  );

alter table public.mf_scheme_sector_allocations enable row level security;
revoke all on table public.mf_scheme_sector_allocations from public, anon, authenticated;
grant select, insert, update, delete
  on table public.mf_scheme_sector_allocations
  to service_role;

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
  requested_scopes text[];
  staged_holding_count integer := 0;
  valid_holding_count integer := 0;
  invalid_holding_count integer := 0;
  staged_sector_count integer := 0;
  valid_sector_count integer := 0;
  invalid_sector_count integer := 0;
  derived_sector_count integer := 0;
  holding_count integer := 0;
  sector_count integer := 0;
begin
  select * into source_row
  from public.mf_raw_documents
  where id = p_source_document_id
  for update;

  if source_row.id is null then
    raise exception 'source_document_not_found';
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

  select count(*) into staged_holding_count
  from public.mf_scheme_holdings
  where source_document_id = p_source_document_id;

  select count(*) into invalid_holding_count
  from public.mf_scheme_holdings h
  left join public.mutual_fund_family_mapping m
    on m.scheme_code = h.mapped_scheme_code
  left join public.mutual_fund_core_snapshot s
    on s.scheme_code = h.mapped_scheme_code
  where h.source_document_id = p_source_document_id
    and (
      h.validation_status <> 'valid'
      or h.mapping_status <> 'mapped'
      or h.mapped_scheme_code is null
      or h.mapped_family_id is null
      or coalesce(h.mapping_confidence, 0) < 90
      or m.family_id is distinct from h.mapped_family_id
      or not public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
      or h.report_month is distinct from source_row.report_month
      or h.mapped_scheme_code !~ '^[0-9]+$'
    );

  select count(*) into valid_holding_count
  from public.mf_scheme_holdings h
  join public.mutual_fund_family_mapping m
    on m.scheme_code = h.mapped_scheme_code
   and m.family_id = h.mapped_family_id
  join public.mutual_fund_core_snapshot s
    on s.scheme_code = h.mapped_scheme_code
  where h.source_document_id = p_source_document_id
    and h.validation_status = 'valid'
    and h.mapping_status = 'mapped'
    and h.mapped_scheme_code is not null
    and h.mapped_family_id is not null
    and coalesce(h.mapping_confidence, 0) >= 90
    and public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
    and h.report_month = source_row.report_month
    and h.mapped_scheme_code ~ '^[0-9]+$';

  if 'holdings' = any(requested_scopes) then
    if staged_holding_count = 0 then
      raise exception 'staged_holdings_missing';
    end if;
    if invalid_holding_count > 0 then
      raise exception 'staged_holdings_contain_non_promotable_rows';
    end if;
    if valid_holding_count = 0 then
      raise exception 'staged_holdings_have_no_promotable_rows';
    end if;
  end if;

  select count(*) into staged_sector_count
  from public.mf_scheme_sector_allocations
  where source_document_id = p_source_document_id;

  if staged_sector_count > 0 then
    select count(*) into invalid_sector_count
    from public.mf_scheme_sector_allocations a
    left join public.mutual_fund_family_mapping m
      on m.scheme_code = a.mapped_scheme_code
    left join public.mutual_fund_core_snapshot s
      on s.scheme_code = a.mapped_scheme_code
    where a.source_document_id = p_source_document_id
      and (
        a.validation_status <> 'valid'
        or a.mapping_status <> 'mapped'
        or a.mapped_scheme_code is null
        or a.mapped_family_id is null
        or coalesce(a.mapping_confidence, 0) < 90
        or m.family_id is distinct from a.mapped_family_id
        or not public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
        or a.report_month is distinct from source_row.report_month
        or a.mapped_scheme_code !~ '^[0-9]+$'
        or a.weight_pct <= 0
        or a.weight_pct > 100
      );

    select count(*) into valid_sector_count
    from public.mf_scheme_sector_allocations a
    join public.mutual_fund_family_mapping m
      on m.scheme_code = a.mapped_scheme_code
     and m.family_id = a.mapped_family_id
    join public.mutual_fund_core_snapshot s
      on s.scheme_code = a.mapped_scheme_code
    where a.source_document_id = p_source_document_id
      and a.validation_status = 'valid'
      and a.mapping_status = 'mapped'
      and coalesce(a.mapping_confidence, 0) >= 90
      and public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
      and a.report_month = source_row.report_month
      and a.mapped_scheme_code ~ '^[0-9]+$';
  else
    select count(*) into derived_sector_count
    from public.mf_scheme_holdings h
    join public.mutual_fund_family_mapping m
      on m.scheme_code = h.mapped_scheme_code
     and m.family_id = h.mapped_family_id
    join public.mutual_fund_core_snapshot s
      on s.scheme_code = h.mapped_scheme_code
    where h.source_document_id = p_source_document_id
      and h.validation_status = 'valid'
      and h.mapping_status = 'mapped'
      and coalesce(h.mapping_confidence, 0) >= 90
      and public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
      and h.report_month = source_row.report_month
      and h.mapped_scheme_code ~ '^[0-9]+$'
      and nullif(trim(h.sector), '') is not null;
  end if;

  if 'sectors' = any(requested_scopes) then
    if staged_sector_count > 0 and invalid_sector_count > 0 then
      raise exception 'staged_sectors_contain_non_promotable_rows';
    end if;
    if staged_sector_count > 0 and valid_sector_count = 0 then
      raise exception 'staged_sectors_have_no_promotable_rows';
    end if;
    if staged_sector_count = 0 and derived_sector_count = 0 then
      raise exception 'staged_sectors_missing';
    end if;
  end if;

  if 'holdings' = any(requested_scopes) then
    delete from public.mutual_fund_holdings runtime
    where runtime.source = 'amc_disclosure'
      and runtime.as_of_date = source_row.report_month
      and runtime.scheme_code in (
        select distinct h.mapped_scheme_code::integer
        from public.mf_scheme_holdings h
        where h.source_document_id = p_source_document_id
          and h.validation_status = 'valid'
          and h.mapping_status = 'mapped'
          and coalesce(h.mapping_confidence, 0) >= 90
          and h.report_month = source_row.report_month
          and h.mapped_scheme_code ~ '^[0-9]+$'
      );

    insert into public.mutual_fund_holdings (
      scheme_code,
      family_id,
      as_of_date,
      security_name,
      isin,
      sector,
      weight_pct,
      quantity,
      market_value_cr,
      source,
      provider_payload,
      updated_at
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
      and h.validation_status = 'valid'
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

  if 'sectors' = any(requested_scopes) and staged_sector_count > 0 then
    delete from public.mutual_fund_sectors runtime
    where runtime.source = 'amc_disclosure'
      and runtime.scheme_code in (
        select distinct a.mapped_scheme_code
        from public.mf_scheme_sector_allocations a
        where a.source_document_id = p_source_document_id
          and a.validation_status = 'valid'
          and a.mapping_status = 'mapped'
          and coalesce(a.mapping_confidence, 0) >= 90
          and a.report_month = source_row.report_month
          and a.mapped_scheme_code ~ '^[0-9]+$'
      );

    insert into public.mutual_fund_sectors (
      scheme_code,
      family_id,
      sector,
      weight_pct,
      stock_count,
      source,
      provider_payload,
      updated_at
    )
    select
      a.mapped_scheme_code,
      a.mapped_family_id,
      a.sector_name,
      sum(a.weight_pct),
      null,
      'amc_disclosure',
      jsonb_build_object(
        'source_document_id', p_source_document_id,
        'report_month', source_row.report_month,
        'allocation_source', 'official_sector_allocation'
      ),
      now()
    from public.mf_scheme_sector_allocations a
    join public.mutual_fund_family_mapping m
      on m.scheme_code = a.mapped_scheme_code
     and m.family_id = a.mapped_family_id
    join public.mutual_fund_core_snapshot s
      on s.scheme_code = a.mapped_scheme_code
    where a.source_document_id = p_source_document_id
      and a.validation_status = 'valid'
      and a.mapping_status = 'mapped'
      and coalesce(a.mapping_confidence, 0) >= 90
      and public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
      and a.report_month = source_row.report_month
      and a.mapped_scheme_code ~ '^[0-9]+$'
    group by a.mapped_scheme_code, a.mapped_family_id, a.sector_name
    on conflict (scheme_code, sector)
    do update set
      family_id = excluded.family_id,
      weight_pct = excluded.weight_pct,
      stock_count = excluded.stock_count,
      source = excluded.source,
      provider_payload = excluded.provider_payload,
      updated_at = excluded.updated_at;
    get diagnostics sector_count = row_count;
  elsif 'sectors' = any(requested_scopes) then
    delete from public.mutual_fund_sectors runtime
    where runtime.source = 'amc_disclosure'
      and runtime.scheme_code in (
        select distinct h.mapped_scheme_code
        from public.mf_scheme_holdings h
        where h.source_document_id = p_source_document_id
          and h.validation_status = 'valid'
          and h.mapping_status = 'mapped'
          and coalesce(h.mapping_confidence, 0) >= 90
          and h.report_month = source_row.report_month
          and h.mapped_scheme_code ~ '^[0-9]+$'
          and nullif(trim(h.sector), '') is not null
      );

    insert into public.mutual_fund_sectors (
      scheme_code,
      family_id,
      sector,
      weight_pct,
      stock_count,
      source,
      provider_payload,
      updated_at
    )
    select
      h.mapped_scheme_code,
      h.mapped_family_id,
      trim(h.sector),
      sum(coalesce(h.percent_aum, 0)),
      count(*),
      'amc_disclosure',
      jsonb_build_object(
        'source_document_id', p_source_document_id,
        'report_month', source_row.report_month,
        'allocation_source', 'derived_from_official_holdings'
      ),
      now()
    from public.mf_scheme_holdings h
    join public.mutual_fund_family_mapping m
      on m.scheme_code = h.mapped_scheme_code
     and m.family_id = h.mapped_family_id
    join public.mutual_fund_core_snapshot s
      on s.scheme_code = h.mapped_scheme_code
    where h.source_document_id = p_source_document_id
      and h.validation_status = 'valid'
      and h.mapping_status = 'mapped'
      and coalesce(h.mapping_confidence, 0) >= 90
      and public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
      and h.report_month = source_row.report_month
      and h.mapped_scheme_code ~ '^[0-9]+$'
      and nullif(trim(h.sector), '') is not null
    group by h.mapped_scheme_code, h.mapped_family_id, trim(h.sector)
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
    source_document_id,
    amc_code,
    scopes,
    apply_requested,
    status,
    requested_by,
    validation_report,
    after_snapshot,
    completed_at
  ) values (
    p_source_document_id,
    source_row.amc_code,
    requested_scopes,
    true,
    'applied',
    p_requested_by,
    jsonb_build_object(
      'mapping_revalidated', true,
      'report_month', source_row.report_month,
      'valid_holding_rows', valid_holding_count,
      'rejected_holding_rows', invalid_holding_count,
      'valid_direct_sector_rows', valid_sector_count,
      'rejected_direct_sector_rows', invalid_sector_count,
      'derived_sector_rows', derived_sector_count
    ),
    jsonb_build_object(
      'holdings_rows', holding_count,
      'sector_rows', sector_count
    ),
    now()
  );

  return jsonb_build_object(
    'status', 'applied',
    'source_document_id', p_source_document_id,
    'scopes', requested_scopes,
    'holdings_rows', holding_count,
    'sector_rows', sector_count,
    'valid_holding_rows', valid_holding_count,
    'rejected_holding_rows', invalid_holding_count,
    'valid_direct_sector_rows', valid_sector_count,
    'rejected_direct_sector_rows', invalid_sector_count,
    'derived_sector_rows', derived_sector_count
  );
end;
$$;

revoke all on function public.promote_mf_holdings_document(
  uuid,
  text[],
  text,
  date
) from public, anon, authenticated;
grant execute on function public.promote_mf_holdings_document(
  uuid,
  text[],
  text,
  date
) to service_role;
