-- 20260922_quarantine_corrupt_amfi_holdings.sql
--
-- Remove holdings written from the corrupt Apr-Jun 2026 AMFI scheme-wise disclosure payload.
--
-- Background: the AMFI endpoint returned an ISIN column that was not row-aligned with
-- Company_Name for MF_ID 28 (UTI Mutual Fund), strMonth 01-Apr-2026. 33 of 53 distinct ISINs
-- were each paired with multiple unrelated issuers — INE009A01021 (Infosys) appeared against
-- ITC, Coal India, Voltas and 10 others. Persisting that produced holdings where a stock's ISIN
-- identified a different company.
--
-- Impact: frontend/lib/portfolioAnalytics.ts keys holdings on `isin:` first, so the portfolio
-- overlap view grouped unrelated companies as the same holding.
--
-- Scope: MF_ID 18 (LIC Mutual Fund) for the same quarter is clean and is deliberately retained.
-- Verified before writing this migration: UTI Apr-2026 = 33 conflicting ISINs of 53;
-- LIC Apr-2026 = 0 conflicting ISINs of 25.
--
-- The rows are moved to a quarantine table rather than deleted outright, so the evidence for the
-- AMFI report stays queryable and the move is reversible. `sync_mf_metadata.py` now refuses such
-- a payload at write time, so the rows will not reappear once AMFI corrects the feed.
--
-- Idempotent: safe to re-run. The final delete is a no-op once the rows are already quarantined.

begin;

-- ---------------------------------------------------------------------------
-- 1. Quarantine table: service-role only, matching the source table's access model.
-- ---------------------------------------------------------------------------

create table if not exists public.mutual_fund_holdings_quarantine (
  like public.mutual_fund_holdings including defaults
);

alter table public.mutual_fund_holdings_quarantine
  add column if not exists quarantined_at timestamptz not null default now(),
  add column if not exists quarantine_reason text not null default 'unknown';

-- `LIKE` copies NOT NULL but not constraints or indexes, so the primary key must be added
-- explicitly for the `ON CONFLICT (id)` in step 3 to be valid. Guarded so a re-run is a no-op.
do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conrelid = 'public.mutual_fund_holdings_quarantine'::regclass and contype = 'p'
  ) then
    alter table public.mutual_fund_holdings_quarantine add primary key (id);
  end if;
end $$;

alter table public.mutual_fund_holdings_quarantine enable row level security;
revoke all on table public.mutual_fund_holdings_quarantine from public, anon, authenticated;
grant select, insert, update, delete on table public.mutual_fund_holdings_quarantine to service_role;

-- ---------------------------------------------------------------------------
-- 2. Verify the target really is the corrupt payload before touching anything.
--    Abort the migration rather than delete from a clean source.
-- ---------------------------------------------------------------------------

do $$
declare
  conflicting_isins integer;
  target_rows integer;
begin
  select count(*) into target_rows
  from public.mutual_fund_holdings
  where source = 'AMFI scheme-wise disclosure: UTI Mutual Fund'
    and as_of_date = '2026-04-01';

  select count(*) into conflicting_isins
  from (
    select isin
    from public.mutual_fund_holdings
    where source = 'AMFI scheme-wise disclosure: UTI Mutual Fund'
      and as_of_date = '2026-04-01'
      and isin is not null
      and lower(isin) not in ('(blank)', 'blank', 'n/a', 'na', 'none', 'null', '-', '--')
    group by isin
    having count(distinct regexp_replace(
      regexp_replace(lower(regexp_replace(security_name, '&', ' and ', 'g')),
        '\y(ltd|limited|pvt|private|co|company|corp|corporation|inc|plc|the|and)\y', ' ', 'g'),
      '[^a-z0-9]+', '', 'g')) > 1
  ) conflicts;

  if target_rows = 0 then
    raise notice 'No UTI Apr-2026 holdings present; nothing to quarantine.';
  elsif conflicting_isins = 0 then
    -- Refusing here is the whole point: if the payload is not self-contradictory, this migration
    -- is operating on data it was not written for, and deleting would lose good rows.
    raise exception
      'Refusing to quarantine % UTI Apr-2026 rows: no conflicting ISINs detected.', target_rows;
  else
    raise notice 'Verified corrupt payload: % rows, % conflicting ISINs.', target_rows, conflicting_isins;
  end if;
end $$;

-- ---------------------------------------------------------------------------
-- 3. Move the corrupt rows into quarantine.
-- ---------------------------------------------------------------------------

insert into public.mutual_fund_holdings_quarantine
  (id, scheme_code, as_of_date, security_name, isin, sector, weight_pct, source,
   updated_at, family_id, holding_type, quantity, market_value_cr, provider_payload,
   quarantine_reason)
select
  id, scheme_code, as_of_date, security_name, isin, sector, weight_pct, source,
  updated_at, family_id, holding_type, quantity, market_value_cr, provider_payload,
  'amfi_isin_company_misalignment:MF_ID=28:strMonth=01-Apr-2026'
from public.mutual_fund_holdings
where source = 'AMFI scheme-wise disclosure: UTI Mutual Fund'
  and as_of_date = '2026-04-01'
on conflict (id) do nothing;

-- ---------------------------------------------------------------------------
-- 4. Delete the quarantined rows from the serving table.
-- ---------------------------------------------------------------------------

delete from public.mutual_fund_holdings
where source = 'AMFI scheme-wise disclosure: UTI Mutual Fund'
  and as_of_date = '2026-04-01';

commit;
