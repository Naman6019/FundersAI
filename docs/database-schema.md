# Database Schema (Migration Runbook)

Run migrations in order:

```bash
psql "$DATABASE_URL" -f backend/migrations/20260501_source_neutral_stock_data.sql
psql "$DATABASE_URL" -f backend/migrations/20260503_add_stock_price_value_traded.sql
psql "$DATABASE_URL" -f backend/migrations/20260503_add_data_quality_issues.sql
psql "$DATABASE_URL" -f backend/migrations/20260512_quota_safe_provider_architecture.sql
psql "$DATABASE_URL" -f backend/migrations/20260513_add_mfdata_enrichment_tables.sql
psql "$DATABASE_URL" -f backend/migrations/20260513_drop_legacy_mutual_fund_history.sql
psql "$DATABASE_URL" -f backend/migrations/20260513_drop_empty_legacy_stock_tables.sql
psql "$DATABASE_URL" -f backend/migrations/20260514_add_mf_amc_disclosure_pipeline.sql
psql "$DATABASE_URL" -f backend/migrations/20260514_update_ppfas_source_discovery.sql
psql "$DATABASE_URL" -f backend/migrations/20260515_add_r2_storage_and_compaction_support.sql
psql "$DATABASE_URL" -f backend/migrations/20260519_add_user_profiles_admin_roles.sql
```

Note: `20260513_add_mfdata_enrichment_tables.sql` is a historical filename. The active mutual-fund enrichment flow no longer calls MFdata and uses AMFI + AMC disclosures.

## Active Table Families

### Stock
- `stocks`
- `stock_prices_daily`
- `financial_statements`
- `ratios_snapshot`
- `shareholding_pattern`
- `corporate_events`
- `stock_core_snapshot`

### Mutual Fund Runtime
- `mutual_funds`
- `mutual_fund_core_snapshot`
- `mutual_fund_nav_history`
- `mutual_fund_holdings`
- `mutual_fund_sectors`

### Mutual Fund Ingestion / Parsing
- `mf_amc_sources`
- `mf_raw_documents`
- `mf_schemes`
- `mf_scheme_holdings`
- `mf_scheme_monthly_metrics`
- `mf_parse_review_queue`

### Storage/Archive
- `mf_r2_archive_manifests`

### Admin/Auth
- `user_profiles`

### Telemetry/Observability
- `data_provider_runs`
- `provider_usage_logs`
- `data_quality_issues`

## Notes
- `mf_raw_documents` now supports R2 metadata (`storage_backend`, `storage_bucket`, `storage_key`, `storage_metadata`).
- Legacy tables (`mutual_fund_history`, `stock_history`, `stock_fundamentals`) were intentionally dropped.
- `nifty_stocks` remains as a small compatibility/search fallback table.
