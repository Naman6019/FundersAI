-- Replace the report-month-bound factsheet promotion wrapper with one atomic
-- implementation. This avoids delegating to the legacy three-argument RPC,
-- whose nested JSON assumptions are not safe for older runtime snapshots.

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

  select to_jsonb(s) into snapshot_before
  from public.mutual_fund_core_snapshot s
  where s.scheme_code = candidate.mapped_scheme_code;

  if snapshot_before is null then
    raise exception 'mapped_scheme_snapshot_missing';
  end if;
  if not public.mf_snapshot_matches_amc(
    candidate.amc_code,
    snapshot_before->>'amc_name'
  ) then
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

  trace := case
    when snapshot_before->'provider_payload' is null
      or jsonb_typeof(snapshot_before->'provider_payload') = 'null'
      then '{}'::jsonb
    when jsonb_typeof(snapshot_before->'provider_payload') = 'object'
      then snapshot_before->'provider_payload'
    else jsonb_build_object(
      'legacy_provider_payload',
      snapshot_before->'provider_payload'
    )
  end;

  trace := trace || jsonb_build_object(
    'amc_staged_promotion',
    jsonb_build_object(
      'candidate_id', candidate.id,
      'source_document_id', candidate.source_document_id,
      'report_month', candidate.report_month,
      'scopes', requested_scopes,
      'requested_by', p_requested_by,
      'promoted_at', now()
    )
  );

  update public.mutual_fund_core_snapshot
  set
    risk_level = case
      when 'risk' = any(requested_scopes) then candidate.risk_level
      else risk_level
    end,
    expense_ratio = case
      when 'ter_aum' = any(requested_scopes) then candidate.expense_ratio
      else expense_ratio
    end,
    aum = case
      when 'ter_aum' = any(requested_scopes) then candidate.aum
      else aum
    end,
    benchmark = case
      when 'benchmark' = any(requested_scopes) then candidate.benchmark
      else benchmark
    end,
    fund_manager = case
      when 'manager' = any(requested_scopes) then candidate.fund_manager
      else fund_manager
    end,
    provider_payload = trace,
    last_updated = now()
  where scheme_code = candidate.mapped_scheme_code;

  select to_jsonb(s) into snapshot_after
  from public.mutual_fund_core_snapshot s
  where s.scheme_code = candidate.mapped_scheme_code;

  update public.mf_factsheet_candidates
  set
    promoted_scopes = (
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
    source_document_id,
    candidate_id,
    amc_code,
    scopes,
    apply_requested,
    status,
    requested_by,
    validation_report,
    before_snapshot,
    after_snapshot,
    completed_at
  ) values (
    candidate.source_document_id,
    candidate.id,
    candidate.amc_code,
    requested_scopes,
    true,
    'applied',
    p_requested_by,
    jsonb_build_object(
      'mapping_revalidated', true,
      'report_month', candidate.report_month
    ),
    snapshot_before,
    snapshot_after,
    now()
  );

  return jsonb_build_object(
    'status', 'applied',
    'candidate_id', candidate.id,
    'scheme_code', candidate.mapped_scheme_code,
    'scopes', requested_scopes
  );
end;
$$;

revoke all on function public.promote_mf_factsheet_candidate(
  uuid,
  text[],
  text,
  date
) from public, anon, authenticated;
grant execute on function public.promote_mf_factsheet_candidate(
  uuid,
  text[],
  text,
  date
) to service_role;
