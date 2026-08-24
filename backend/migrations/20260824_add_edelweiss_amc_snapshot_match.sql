-- Additive safety fix. This changes only the AMC allow-list used by promotion RPCs.
-- It does not promote, delete, or rewrite any disclosure data.

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
    when 'edelweiss' then lower(coalesce(p_amc_name, '')) like '%edelweiss%'
    else false
  end
$$;

revoke all on function public.mf_snapshot_matches_amc(text, text) from public, anon, authenticated;
grant execute on function public.mf_snapshot_matches_amc(text, text) to service_role;
