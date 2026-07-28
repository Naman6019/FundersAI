-- Read-only compact evidence for promotion-eligible staging coverage.
-- Applying this migration does not parse, promote, or activate any fund data.

create or replace function public.mf_staging_holding_promotion_coverage_rows(
  p_report_month date
) returns table (
  source_document_id uuid,
  amc_code text,
  report_month date,
  raw_scheme_name text,
  mapped_scheme_code text,
  mapped_family_id text,
  mapping_status text,
  mapping_confidence numeric,
  validation_status text,
  sector text
)
language sql
stable
security definer
set search_path = public
as $$
  select
    h.source_document_id,
    d.amc_code,
    h.report_month,
    h.raw_scheme_name,
    h.mapped_scheme_code,
    h.mapped_family_id,
    h.mapping_status,
    h.mapping_confidence,
    h.validation_status,
    case
      when bool_or(nullif(trim(h.sector), '') is not null) then '__present__'
      else null
    end as sector
  from public.mf_raw_documents d
  join public.mf_scheme_holdings h
    on h.source_document_id = d.id
  where d.report_month = p_report_month
    and h.report_month = p_report_month
  group by
    h.source_document_id,
    d.amc_code,
    h.report_month,
    h.raw_scheme_name,
    h.mapped_scheme_code,
    h.mapped_family_id,
    h.mapping_status,
    h.mapping_confidence,
    h.validation_status
$$;

create or replace function public.mf_staging_sector_promotion_coverage_rows(
  p_report_month date
) returns table (
  source_document_id uuid,
  amc_code text,
  report_month date,
  raw_scheme_name text,
  mapped_scheme_code text,
  mapped_family_id text,
  mapping_status text,
  mapping_confidence numeric,
  validation_status text,
  sector_name text
)
language sql
stable
security definer
set search_path = public
as $$
  select
    a.source_document_id,
    d.amc_code,
    a.report_month,
    a.raw_scheme_name,
    a.mapped_scheme_code,
    a.mapped_family_id,
    a.mapping_status,
    a.mapping_confidence,
    a.validation_status,
    '__present__'::text as sector_name
  from public.mf_raw_documents d
  join public.mf_scheme_sector_allocations a
    on a.source_document_id = d.id
  where d.report_month = p_report_month
    and a.report_month = p_report_month
    and nullif(trim(a.sector_name), '') is not null
  group by
    a.source_document_id,
    d.amc_code,
    a.report_month,
    a.raw_scheme_name,
    a.mapped_scheme_code,
    a.mapped_family_id,
    a.mapping_status,
    a.mapping_confidence,
    a.validation_status
$$;

revoke all on function public.mf_staging_holding_promotion_coverage_rows(date)
  from public, anon, authenticated;
grant execute on function public.mf_staging_holding_promotion_coverage_rows(date)
  to service_role;

revoke all on function public.mf_staging_sector_promotion_coverage_rows(date)
  from public, anon, authenticated;
grant execute on function public.mf_staging_sector_promotion_coverage_rows(date)
  to service_role;
