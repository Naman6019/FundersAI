-- 20260919_harden_public_schema_privileges.sql
--
-- Close the public-schema over-grant introduced by the 2026-09-15 OCI
-- recreation. In that instance every table created by `postgres` inherited
-- default privileges granting `anon` and `authenticated`
-- SELECT/INSERT/UPDATE/DELETE/TRUNCATE, and 29 tables had RLS disabled. The
-- publishable anon key ships in the browser, so any holder could modify or
-- truncate production data through PostgREST.
--
-- What this migration does NOT do:
--   * It does not revoke anything from `service_role` or `postgres`. Both have
--     rolbypassrls = true, so the backend, Next.js server routes, Supabase
--     Studio (postgres-meta), edge functions, and GitHub Actions are unaffected.
--   * It does not remove SELECT from tables the public app reads.
--
-- Access model after this migration:
--   * `anon`          -> read-only, and only on curated public reference tables.
--   * `authenticated` -> read-only except for user-owned tables (RLS-policied).
--   * `service_role`  -> unchanged (bypasses RLS).
--
-- Idempotent: safe to re-run.

begin;

-- ---------------------------------------------------------------------------
-- 1. Enable RLS on tables that currently have none.
--    Tables owned by the server keep no policy, so anon/authenticated see
--    nothing once the grants below are revoked; service_role still bypasses.
-- ---------------------------------------------------------------------------

alter table public.corporate_events                  enable row level security;
alter table public.data_provider_runs                enable row level security;
alter table public.data_quality_issues               enable row level security;
alter table public.financial_statements              enable row level security;
alter table public.mf_amc_sources                    enable row level security;
alter table public.mf_parse_review_queue             enable row level security;
alter table public.mf_r2_archive_manifests           enable row level security;
alter table public.mf_raw_documents                  enable row level security;
alter table public.mf_scheme_holdings                enable row level security;
alter table public.mf_scheme_monthly_metrics         enable row level security;
alter table public.mf_schemes                        enable row level security;
alter table public.mutual_fund_core_snapshot         enable row level security;
alter table public.mutual_fund_details               enable row level security;
alter table public.mutual_fund_holdings              enable row level security;
alter table public.mutual_fund_sectors               enable row level security;
alter table public.provider_endpoint_health          enable row level security;
alter table public.provider_ingestion_logs           enable row level security;
alter table public.provider_runs                     enable row level security;
alter table public.provider_usage_logs               enable row level security;
alter table public.ratios_snapshot                   enable row level security;
alter table public.shareholding_pattern              enable row level security;
alter table public.stock_core_snapshot               enable row level security;
alter table public.stock_corporate_actions           enable row level security;
alter table public.stock_financial_stats             enable row level security;
alter table public.stock_prices_daily                enable row level security;
alter table public.stock_profiles                    enable row level security;
alter table public.stock_recent_announcements        enable row level security;
alter table public.stocks                           enable row level security;

-- ---------------------------------------------------------------------------
-- 2. Revoke every write privilege from the public API roles on every table.
--    No client-side code legitimately writes without a user JWT, and the
--    user-owned writes are re-granted in step 5. TRUNCATE/REFERENCES/TRIGGER
--    are never needed by PostgREST.
-- ---------------------------------------------------------------------------

revoke insert, update, delete, truncate, references, trigger
  on all tables in schema public from anon, authenticated;

-- ---------------------------------------------------------------------------
-- 3. Restrict SELECT on server-only operational tables.
--    These are read exclusively through service-role clients (admin routes,
--    ingestion jobs, edge functions), so the public roles must not see them.
-- ---------------------------------------------------------------------------

revoke select on table
  public.data_provider_runs,
  public.data_quality_issues,
  public.mf_amc_sources,
  public.mf_parse_review_queue,
  public.mf_r2_archive_manifests,
  public.mf_raw_documents,
  public.mf_scheme_holdings,
  public.mf_scheme_monthly_metrics,
  public.provider_endpoint_health,
  public.provider_ingestion_logs,
  public.provider_runs,
  public.provider_usage_logs
  from anon, authenticated;

-- ---------------------------------------------------------------------------
-- 4. Curated public read access.
--    Public market/reference data the app (or its marketing pages) may serve
--    to anonymous visitors. RLS policies are required because step 1 enabled
--    RLS on these tables and because the roles still hold SELECT.
-- ---------------------------------------------------------------------------

drop policy if exists public_read on public.corporate_events;
create policy public_read on public.corporate_events
  for select to anon, authenticated using (true);

drop policy if exists public_read on public.financial_statements;
create policy public_read on public.financial_statements
  for select to anon, authenticated using (true);

drop policy if exists public_read on public.mf_schemes;
create policy public_read on public.mf_schemes
  for select to anon, authenticated using (true);

drop policy if exists public_read on public.mutual_fund_core_snapshot;
create policy public_read on public.mutual_fund_core_snapshot
  for select to anon, authenticated using (true);

drop policy if exists public_read on public.mutual_fund_details;
create policy public_read on public.mutual_fund_details
  for select to anon, authenticated using (true);

drop policy if exists public_read on public.mutual_fund_holdings;
create policy public_read on public.mutual_fund_holdings
  for select to anon, authenticated using (true);

drop policy if exists public_read on public.mutual_fund_sectors;
create policy public_read on public.mutual_fund_sectors
  for select to anon, authenticated using (true);

drop policy if exists public_read on public.ratios_snapshot;
create policy public_read on public.ratios_snapshot
  for select to anon, authenticated using (true);

drop policy if exists public_read on public.shareholding_pattern;
create policy public_read on public.shareholding_pattern
  for select to anon, authenticated using (true);

drop policy if exists public_read on public.stock_core_snapshot;
create policy public_read on public.stock_core_snapshot
  for select to anon, authenticated using (true);

drop policy if exists public_read on public.stock_corporate_actions;
create policy public_read on public.stock_corporate_actions
  for select to anon, authenticated using (true);

drop policy if exists public_read on public.stock_financial_stats;
create policy public_read on public.stock_financial_stats
  for select to anon, authenticated using (true);

drop policy if exists public_read on public.stock_prices_daily;
create policy public_read on public.stock_prices_daily
  for select to anon, authenticated using (true);

drop policy if exists public_read on public.stock_profiles;
create policy public_read on public.stock_profiles
  for select to anon, authenticated using (true);

drop policy if exists public_read on public.stock_recent_announcements;
create policy public_read on public.stock_recent_announcements
  for select to anon, authenticated using (true);

drop policy if exists public_read on public.stocks;
create policy public_read on public.stocks
  for select to anon, authenticated using (true);

-- ---------------------------------------------------------------------------
-- 5. Re-grant writes for genuinely user-owned tables.
--    Every grant below is still gated by that table's RLS policy
--    (auth.uid() = user_id, or an owner/admin predicate), so a user can only
--    touch their own rows.
-- ---------------------------------------------------------------------------

grant select, insert, update, delete on public.portfolios          to authenticated;
grant select, insert, update, delete on public.portfolio_positions to authenticated;
grant select, insert, update, delete on public.saved_reports       to authenticated;
grant select, insert, update, delete on public.watchlists          to authenticated;
grant select, insert, update, delete on public.chat_messages       to authenticated;
grant select, insert, update, delete on public.ai_chat_sessions    to authenticated;
grant select, insert, update, delete on public.ai_chat_messages    to authenticated;
grant select, update (active)          on public.research_claims   to authenticated;
grant select                           on public.research_claim_evaluations to authenticated;
grant select, insert, update           on public.user_profiles     to authenticated;

-- ---------------------------------------------------------------------------
-- 6. Remove the two always-true policies on mutual_fund_family_mapping.
--    That table is written only by service-role jobs (bypasses RLS), so the
--    authenticated INSERT/UPDATE policies served no purpose and the security
--    advisor flagged them as effectively bypassing RLS.
-- ---------------------------------------------------------------------------

drop policy if exists "Enable insert for authenticated users only" on public.mutual_fund_family_mapping;
drop policy if exists "Enable update for authenticated users only" on public.mutual_fund_family_mapping;

-- ---------------------------------------------------------------------------
-- 7. Tighten the SECURITY DEFINER helper.
--    current_user_is_admin() is required by RLS policies evaluated for
--    `authenticated`, so that role keeps EXECUTE. Anonymous callers only ever
--    receive false; PUBLIC's implicit EXECUTE makes it reachable at
--    /rest/v1/rpc/current_user_is_admin, so revoke it there.
-- ---------------------------------------------------------------------------

revoke execute on function public.current_user_is_admin() from anon, public;
grant execute on function public.current_user_is_admin() to authenticated, service_role;

-- ---------------------------------------------------------------------------
-- 8. Stop the over-grant from recurring.
--    Tables/functions created later by postgres/supabase_admin must not
--    inherit anon or authenticated privileges. New objects need explicit grants.
-- ---------------------------------------------------------------------------

alter default privileges for role postgres in schema public
  revoke insert, update, delete, truncate, references, trigger on tables from anon, authenticated;
alter default privileges for role postgres in schema public
  revoke select on tables from anon, authenticated;
alter default privileges for role postgres in schema public
  revoke execute on functions from anon, public;

-- supabase_admin is the image's superuser; `postgres` cannot change its default
-- privileges. It is applied opportunistically so this migration still succeeds
-- when run as `postgres` (the Studio/MCP path). Re-running it as supabase_admin
-- (see the note below) completes this step.
do $$
begin
  begin
    execute 'alter default privileges for role supabase_admin in schema public '
         || 'revoke insert, update, delete, truncate, references, trigger on tables from anon, authenticated';
    execute 'alter default privileges for role supabase_admin in schema public '
         || 'revoke select on tables from anon, authenticated';
    execute 'alter default privileges for role supabase_admin in schema public '
         || 'revoke execute on functions from anon, public';
  exception
    when insufficient_privilege then
      raise notice 'Skipped supabase_admin default privileges (run as supabase_admin to apply).';
  end;
end
$$;

commit;

-- ---------------------------------------------------------------------------
-- Verification (run after applying):
--
--   -- Expect zero rows: no anon write anywhere.
--   select c.relname, p.grantee, p.privilege_type
--   from pg_class c
--   join pg_namespace n on n.oid = c.relnamespace
--   cross join lateral aclexplode(coalesce(c.relacl, acldefault('r', c.relowner))) p
--   where n.nspname = 'public' and c.relkind = 'r'
--     and p.grantee = 'anon'::regrole
--     and p.privilege_type in ('INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER');
--
--   -- Expect zero rows: no public table without RLS.
--   select c.relname from pg_class c
--   join pg_namespace n on n.oid = c.relnamespace
--   where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity;
--
--   -- Expect: current_user = postgres and no error, via the MCP/Studio path.
--   select current_user;
-- ---------------------------------------------------------------------------
