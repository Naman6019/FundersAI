# Database Schema

MarketMind uses Supabase (PostgreSQL) as its primary structured data store.  
Writes are server-side only (backend jobs, backend APIs, or trusted service-role environments).

## Core Stock Tables
- `stocks`
- `stock_prices_daily`
- `financial_statements`
- `ratios_snapshot`
- `shareholding_pattern`
- `corporate_events`
- `stock_core_snapshot`

## Core Mutual Fund Tables
- `mutual_funds` (compatibility/source table)
- `mutual_fund_core_snapshot`
- `mutual_fund_nav_history`
- `mutual_fund_holdings`
- `mutual_fund_sectors`

## MF AMC Disclosure Pipeline Tables
- `mf_amc_sources`
- `mf_raw_documents`
- `mf_schemes`
- `mf_scheme_holdings`
- `mf_scheme_monthly_metrics`
- `mf_parse_review_queue`

## R2 / Compaction Support
- `mf_r2_archive_manifests`
- `mf_raw_documents.storage_backend/storage_bucket/storage_key/storage_metadata`

## Admin / Access Control
- `user_profiles`
  - `role`: `user | admin | tester`
  - `tier`: `free | pro`
  - `last_active_at`, `created_at`, `updated_at`
- RLS policies enforce:
  - user can read own profile
  - admin can read all profiles
  - only admin can perform role/tier updates

## Observability / Job Telemetry
- `data_provider_runs`
- `provider_usage_logs`
- `data_quality_issues`

## Legacy / Compatibility Notes
- `nifty_stocks` remains as a small fallback/search helper table.
- Legacy heavy tables (`mutual_fund_history`, `stock_history`, `stock_fundamentals`) were dropped to stay within storage limits.
