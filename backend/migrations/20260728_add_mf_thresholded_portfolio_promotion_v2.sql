-- Bound large source-document reads and promote only validated portfolio families.
-- Applying this migration does not promote any data.

create index if not exists mf_scheme_holdings_source_document_id_id_idx
  on public.mf_scheme_holdings (source_document_id, id);

create index if not exists mf_scheme_sector_allocations_source_document_id_id_idx
  on public.mf_scheme_sector_allocations (source_document_id, id);

create or replace function public.promote_mf_holdings_document_v2(
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
  rejected_holding_count integer := 0;
  observed_holding_family_count integer := 0;
  mapped_holding_family_count integer := 0;
  valid_holding_family_count integer := 0;
  holding_mapping_coverage numeric := 0;
  holding_validation_coverage numeric := 0;
  staged_sector_count integer := 0;
  valid_sector_count integer := 0;
  rejected_sector_count integer := 0;
  observed_sector_family_count integer := 0;
  mapped_sector_family_count integer := 0;
  valid_sector_family_count integer := 0;
  sector_mapping_coverage numeric := 0;
  sector_validation_coverage numeric := 0;
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
  if source_row.parse_status not in ('parsed', 'parsed_partial')
     or lower(coalesce(source_row.storage_backend, '')) <> 'r2'
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

  select
    count(*),
    count(*) filter (
      where h.validation_status = 'valid'
        and h.mapping_status = 'mapped'
        and h.mapped_scheme_code is not null
        and h.mapped_family_id is not null
        and coalesce(h.mapping_confidence, 0) >= 90
        and m.family_id = h.mapped_family_id
        and public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
        and h.report_month = source_row.report_month
        and h.mapped_scheme_code ~ '^[0-9]+$'
    ),
    count(distinct coalesce(
      nullif(h.mapped_family_id, ''),
      'raw:' || lower(trim(h.raw_scheme_name))
    )),
    count(distinct h.mapped_family_id) filter (
      where h.mapping_status = 'mapped'
        and h.mapped_scheme_code is not null
        and h.mapped_family_id is not null
        and coalesce(h.mapping_confidence, 0) >= 90
        and m.family_id = h.mapped_family_id
        and public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
        and h.report_month = source_row.report_month
        and h.mapped_scheme_code ~ '^[0-9]+$'
    ),
    count(distinct h.mapped_family_id) filter (
      where h.validation_status = 'valid'
        and h.mapping_status = 'mapped'
        and h.mapped_scheme_code is not null
        and h.mapped_family_id is not null
        and coalesce(h.mapping_confidence, 0) >= 90
        and m.family_id = h.mapped_family_id
        and public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
        and h.report_month = source_row.report_month
        and h.mapped_scheme_code ~ '^[0-9]+$'
    )
  into
    staged_holding_count,
    valid_holding_count,
    observed_holding_family_count,
    mapped_holding_family_count,
    valid_holding_family_count
  from public.mf_scheme_holdings h
  left join public.mutual_fund_family_mapping m
    on m.scheme_code = h.mapped_scheme_code
  left join public.mutual_fund_core_snapshot s
    on s.scheme_code = h.mapped_scheme_code
  where h.source_document_id = p_source_document_id;

  rejected_holding_count := staged_holding_count - valid_holding_count;
  holding_mapping_coverage := case
    when observed_holding_family_count = 0 then 0
    else round(
      mapped_holding_family_count::numeric
      * 100
      / observed_holding_family_count,
      2
    )
  end;
  holding_validation_coverage := case
    when mapped_holding_family_count = 0 then 0
    else round(
      valid_holding_family_count::numeric
      * 100
      / mapped_holding_family_count,
      2
    )
  end;

  if 'holdings' = any(requested_scopes) then
    if staged_holding_count = 0 then
      raise exception 'staged_holdings_missing';
    end if;
    if valid_holding_count = 0 then
      raise exception 'staged_holdings_have_no_promotable_rows';
    end if;
    if holding_mapping_coverage < 80
       or holding_validation_coverage < 80 then
      raise exception 'staged_holdings_below_family_coverage_threshold';
    end if;
  end if;

  select count(*) into staged_sector_count
  from public.mf_scheme_sector_allocations
  where source_document_id = p_source_document_id;

  if staged_sector_count > 0 then
    select
      count(*) filter (
        where a.validation_status = 'valid'
          and a.mapping_status = 'mapped'
          and a.mapped_scheme_code is not null
          and a.mapped_family_id is not null
          and coalesce(a.mapping_confidence, 0) >= 90
          and m.family_id = a.mapped_family_id
          and public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
          and a.report_month = source_row.report_month
          and a.mapped_scheme_code ~ '^[0-9]+$'
          and a.weight_pct > 0
          and a.weight_pct <= 100
      ),
      count(distinct coalesce(
        nullif(a.mapped_family_id, ''),
        'raw:' || lower(trim(a.raw_scheme_name))
      )),
      count(distinct a.mapped_family_id) filter (
        where a.mapping_status = 'mapped'
          and a.mapped_scheme_code is not null
          and a.mapped_family_id is not null
          and coalesce(a.mapping_confidence, 0) >= 90
          and m.family_id = a.mapped_family_id
          and public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
          and a.report_month = source_row.report_month
          and a.mapped_scheme_code ~ '^[0-9]+$'
      ),
      count(distinct a.mapped_family_id) filter (
        where a.validation_status = 'valid'
          and a.mapping_status = 'mapped'
          and a.mapped_scheme_code is not null
          and a.mapped_family_id is not null
          and coalesce(a.mapping_confidence, 0) >= 90
          and m.family_id = a.mapped_family_id
          and public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
          and a.report_month = source_row.report_month
          and a.mapped_scheme_code ~ '^[0-9]+$'
          and a.weight_pct > 0
          and a.weight_pct <= 100
      )
    into
      valid_sector_count,
      observed_sector_family_count,
      mapped_sector_family_count,
      valid_sector_family_count
    from public.mf_scheme_sector_allocations a
    left join public.mutual_fund_family_mapping m
      on m.scheme_code = a.mapped_scheme_code
    left join public.mutual_fund_core_snapshot s
      on s.scheme_code = a.mapped_scheme_code
    where a.source_document_id = p_source_document_id;

    rejected_sector_count := staged_sector_count - valid_sector_count;
  else
    select
      count(*) filter (
        where h.validation_status = 'valid'
          and h.mapping_status = 'mapped'
          and h.mapped_scheme_code is not null
          and h.mapped_family_id is not null
          and coalesce(h.mapping_confidence, 0) >= 90
          and m.family_id = h.mapped_family_id
          and public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
          and h.report_month = source_row.report_month
          and h.mapped_scheme_code ~ '^[0-9]+$'
          and nullif(trim(h.sector), '') is not null
      ),
      count(distinct coalesce(
        nullif(h.mapped_family_id, ''),
        'raw:' || lower(trim(h.raw_scheme_name))
      )) filter (
        where nullif(trim(h.sector), '') is not null
          or lower(h.raw_scheme_name) !~ (
            'fund of fund| fof|gold etf|silver etf|liquid etf|'
            'overnight fund|money market fund|short term fund|'
            'short duration fund|low duration fund|ultra short duration fund|'
            'medium duration fund|long duration fund|corporate bond fund|'
            'credit risk fund|banking (and|&) psu debt fund|gilt fund|floater fund'
          )
      ),
      count(distinct h.mapped_family_id) filter (
        where h.mapping_status = 'mapped'
          and h.mapped_scheme_code is not null
          and h.mapped_family_id is not null
          and coalesce(h.mapping_confidence, 0) >= 90
          and m.family_id = h.mapped_family_id
          and public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
          and h.report_month = source_row.report_month
          and h.mapped_scheme_code ~ '^[0-9]+$'
          and (
            nullif(trim(h.sector), '') is not null
            or lower(h.raw_scheme_name) !~ (
              'fund of fund| fof|gold etf|silver etf|liquid etf|'
              'overnight fund|money market fund|short term fund|'
              'short duration fund|low duration fund|ultra short duration fund|'
              'medium duration fund|long duration fund|corporate bond fund|'
              'credit risk fund|banking (and|&) psu debt fund|gilt fund|floater fund'
            )
          )
      ),
      count(distinct h.mapped_family_id) filter (
        where h.validation_status = 'valid'
          and h.mapping_status = 'mapped'
          and h.mapped_scheme_code is not null
          and h.mapped_family_id is not null
          and coalesce(h.mapping_confidence, 0) >= 90
          and m.family_id = h.mapped_family_id
          and public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
          and h.report_month = source_row.report_month
          and h.mapped_scheme_code ~ '^[0-9]+$'
          and nullif(trim(h.sector), '') is not null
      )
    into
      derived_sector_count,
      observed_sector_family_count,
      mapped_sector_family_count,
      valid_sector_family_count
    from public.mf_scheme_holdings h
    left join public.mutual_fund_family_mapping m
      on m.scheme_code = h.mapped_scheme_code
    left join public.mutual_fund_core_snapshot s
      on s.scheme_code = h.mapped_scheme_code
    where h.source_document_id = p_source_document_id;

    valid_sector_count := derived_sector_count;
  end if;

  sector_mapping_coverage := case
    when observed_sector_family_count = 0 then 0
    else round(
      mapped_sector_family_count::numeric
      * 100
      / observed_sector_family_count,
      2
    )
  end;
  sector_validation_coverage := case
    when mapped_sector_family_count = 0 then 0
    else round(
      valid_sector_family_count::numeric
      * 100
      / mapped_sector_family_count,
      2
    )
  end;

  if 'sectors' = any(requested_scopes) then
    if staged_sector_count = 0 and derived_sector_count = 0 then
      raise exception 'staged_sectors_missing';
    end if;
    if valid_sector_count = 0 then
      raise exception 'staged_sectors_have_no_promotable_rows';
    end if;
    if sector_mapping_coverage < 80
       or sector_validation_coverage < 80 then
      raise exception 'staged_sectors_below_family_coverage_threshold';
    end if;
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
          and h.validation_status = 'valid'
          and h.mapping_status = 'mapped'
          and coalesce(h.mapping_confidence, 0) >= 90
          and public.mf_snapshot_matches_amc(source_row.amc_code, s.amc_name)
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
          and a.weight_pct > 0
          and a.weight_pct <= 100
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
      and a.weight_pct > 0
      and a.weight_pct <= 100
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
      'minimum_family_coverage', 80,
      'holding_mapping_coverage', holding_mapping_coverage,
      'holding_validation_coverage', holding_validation_coverage,
      'valid_holding_rows', valid_holding_count,
      'rejected_holding_rows', rejected_holding_count,
      'sector_mapping_coverage', sector_mapping_coverage,
      'sector_validation_coverage', sector_validation_coverage,
      'valid_sector_rows', valid_sector_count,
      'rejected_direct_sector_rows', rejected_sector_count
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
    'minimum_family_coverage', 80,
    'holding_mapping_coverage', holding_mapping_coverage,
    'holding_validation_coverage', holding_validation_coverage,
    'holdings_rows', holding_count,
    'valid_holding_rows', valid_holding_count,
    'rejected_holding_rows', rejected_holding_count,
    'sector_mapping_coverage', sector_mapping_coverage,
    'sector_validation_coverage', sector_validation_coverage,
    'sector_rows', sector_count,
    'valid_sector_rows', valid_sector_count,
    'rejected_direct_sector_rows', rejected_sector_count
  );
end;
$$;

revoke all on function public.promote_mf_holdings_document_v2(
  uuid,
  text[],
  text,
  date
) from public, anon, authenticated;
grant execute on function public.promote_mf_holdings_document_v2(
  uuid,
  text[],
  text,
  date
) to service_role;
