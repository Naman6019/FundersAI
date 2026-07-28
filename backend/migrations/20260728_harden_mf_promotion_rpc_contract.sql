-- Add report-month-bound promotion RPCs without trusting the legacy three-argument entry points.

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
  snapshot_amc text;
  requested_scopes text[];
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

  if p_expected_report_month is null
     or candidate.report_month is distinct from p_expected_report_month
     or source_row.report_month is distinct from p_expected_report_month then
    raise exception 'candidate_report_month_mismatch';
  end if;
  if candidate.mapping_status <> 'mapped'
     or candidate.mapped_scheme_code is null
     or candidate.mapped_family_id is null
     or coalesce(candidate.mapping_confidence, 0) < 90 then
    raise exception 'candidate_mapping_not_promotable';
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

  select amc_name into snapshot_amc
  from public.mutual_fund_core_snapshot
  where scheme_code = candidate.mapped_scheme_code;
  if snapshot_amc is null then
    raise exception 'mapped_scheme_snapshot_missing';
  end if;
  if not public.mf_snapshot_matches_amc(candidate.amc_code, snapshot_amc) then
    raise exception 'candidate_amc_mismatch';
  end if;

  select coalesce(array_agg(distinct scope), '{}')
  into requested_scopes
  from unnest(coalesce(p_scopes, '{}')) scope
  where scope in ('risk', 'ter_aum', 'benchmark', 'manager');
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

  return public.promote_mf_factsheet_candidate(
    p_candidate_id,
    requested_scopes,
    p_requested_by
  );
end;
$$;

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
  staged_count integer;
  invalid_count integer;
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

  select count(*) into staged_count
  from public.mf_scheme_holdings
  where source_document_id = p_source_document_id;
  if staged_count = 0 then
    raise exception 'staged_holdings_missing';
  end if;

  select count(*) into invalid_count
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
  if invalid_count > 0 then
    raise exception 'staged_holdings_contain_non_promotable_rows';
  end if;

  return public.promote_mf_holdings_document(
    p_source_document_id,
    requested_scopes,
    p_requested_by
  );
end;
$$;

revoke all on function public.promote_mf_factsheet_candidate(uuid, text[], text) from public, anon, authenticated, service_role;
revoke all on function public.promote_mf_holdings_document(uuid, text[], text) from public, anon, authenticated, service_role;

revoke all on function public.promote_mf_factsheet_candidate(uuid, text[], text, date) from public, anon, authenticated;
grant execute on function public.promote_mf_factsheet_candidate(uuid, text[], text, date) to service_role;

revoke all on function public.promote_mf_holdings_document(uuid, text[], text, date) from public, anon, authenticated;
grant execute on function public.promote_mf_holdings_document(uuid, text[], text, date) to service_role;
