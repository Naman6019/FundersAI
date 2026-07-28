-- Audited correction for raw documents whose official body month differs from
-- the month assigned during discovery. Applying this migration changes no data.

create table if not exists public.mf_report_month_corrections (
  id uuid primary key default gen_random_uuid(),
  source_document_id uuid not null references public.mf_raw_documents(id),
  amc_code text not null,
  previous_report_month date not null,
  corrected_report_month date not null,
  expected_checksum text not null,
  observed_body_month date not null,
  previous_parse_status text not null,
  requested_by text not null,
  reason text not null,
  deleted_staging_counts jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists mf_report_month_corrections_document_idx
  on public.mf_report_month_corrections (source_document_id, created_at desc);

alter table public.mf_report_month_corrections enable row level security;
revoke all on table public.mf_report_month_corrections from public, anon, authenticated;
grant select, insert on table public.mf_report_month_corrections to service_role;

create or replace function public.reconcile_mf_raw_document_report_month(
  p_source_document_id uuid,
  p_expected_current_month date,
  p_corrected_report_month date,
  p_expected_checksum text,
  p_observed_body_month date,
  p_requested_by text,
  p_reason text
) returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  source_row public.mf_raw_documents%rowtype;
  factsheet_count integer := 0;
  holding_count integer := 0;
  metric_count integer := 0;
  review_count integer := 0;
  sector_count integer := 0;
begin
  select * into source_row
  from public.mf_raw_documents
  where id = p_source_document_id
  for update;

  if source_row.id is null then
    raise exception 'source_document_not_found';
  end if;
  if source_row.report_month is distinct from p_expected_current_month then
    raise exception 'source_current_month_mismatch';
  end if;
  if p_corrected_report_month is null
     or p_corrected_report_month <> date_trunc('month', p_corrected_report_month)::date then
    raise exception 'corrected_report_month_invalid';
  end if;
  if p_observed_body_month is distinct from p_corrected_report_month then
    raise exception 'observed_body_month_mismatch';
  end if;
  if nullif(trim(p_expected_checksum), '') is null
     or source_row.checksum is distinct from p_expected_checksum then
    raise exception 'source_checksum_mismatch';
  end if;
  if lower(coalesce(source_row.storage_backend, '')) <> 'r2'
     or source_row.storage_key is null then
    raise exception 'source_r2_evidence_missing';
  end if;
  if nullif(trim(p_requested_by), '') is null then
    raise exception 'requested_by_required';
  end if;
  if nullif(trim(p_reason), '') is null then
    raise exception 'reason_required';
  end if;
  if exists (
    select 1
    from public.mf_promotion_runs
    where source_document_id = p_source_document_id
      and status = 'applied'
  ) then
    raise exception 'source_has_applied_promotion';
  end if;

  delete from public.mf_factsheet_candidates
  where source_document_id = p_source_document_id;
  get diagnostics factsheet_count = row_count;

  delete from public.mf_scheme_holdings
  where source_document_id = p_source_document_id;
  get diagnostics holding_count = row_count;

  delete from public.mf_scheme_monthly_metrics
  where source_document_id = p_source_document_id;
  get diagnostics metric_count = row_count;

  delete from public.mf_parse_review_queue
  where source_document_id = p_source_document_id;
  get diagnostics review_count = row_count;

  if to_regclass('public.mf_scheme_sector_allocations') is not null then
    execute
      'delete from public.mf_scheme_sector_allocations where source_document_id = $1'
      using p_source_document_id;
    get diagnostics sector_count = row_count;
  end if;

  update public.mf_raw_documents
  set
    report_month = p_corrected_report_month,
    parse_status = 'needs_reparse',
    parsed_at = null,
    validation_issues = array(
      select distinct issue
      from unnest(
        coalesce(source_row.validation_issues, '{}')
        || array['report_month_reconciled_from_' || to_char(source_row.report_month, 'YYYY_MM')]
      ) issue
    ),
    updated_at = now()
  where id = p_source_document_id;

  update public.mf_discovery_documents
  set
    report_month = p_corrected_report_month,
    updated_at = now()
  where raw_document_id = p_source_document_id;

  insert into public.mf_report_month_corrections (
    source_document_id, amc_code, previous_report_month, corrected_report_month,
    expected_checksum, observed_body_month, previous_parse_status, requested_by,
    reason, deleted_staging_counts
  ) values (
    p_source_document_id, source_row.amc_code, source_row.report_month,
    p_corrected_report_month, p_expected_checksum, p_observed_body_month,
    source_row.parse_status, p_requested_by, p_reason,
    jsonb_build_object(
      'factsheet_candidates', factsheet_count,
      'holdings', holding_count,
      'monthly_metrics', metric_count,
      'review_rows', review_count,
      'sector_allocations', sector_count
    )
  );

  return jsonb_build_object(
    'status', 'reconciled',
    'source_document_id', p_source_document_id,
    'amc_code', source_row.amc_code,
    'previous_report_month', source_row.report_month,
    'corrected_report_month', p_corrected_report_month,
    'parse_status', 'needs_reparse',
    'deleted_staging_counts', jsonb_build_object(
      'factsheet_candidates', factsheet_count,
      'holdings', holding_count,
      'monthly_metrics', metric_count,
      'review_rows', review_count,
      'sector_allocations', sector_count
    )
  );
end;
$$;

revoke all on function public.reconcile_mf_raw_document_report_month(
  uuid, date, date, text, date, text, text
) from public, anon, authenticated;
grant execute on function public.reconcile_mf_raw_document_report_month(
  uuid, date, date, text, date, text, text
) to service_role;
