# Database Schema

Run:

```bash
psql "$DATABASE_URL" -f backend/migrations/20260501_source_neutral_stock_data.sql
psql "$DATABASE_URL" -f backend/migrations/20260503_add_stock_price_value_traded.sql
psql "$DATABASE_URL" -f backend/migrations/20260503_add_data_quality_issues.sql
psql "$DATABASE_URL" -f backend/migrations/20260512_quota_safe_provider_architecture.sql
psql "$DATABASE_URL" -f backend/migrations/20260513_add_mfdata_enrichment_tables.sql
psql "$DATABASE_URL" -f backend/migrations/20260513_drop_legacy_mutual_fund_history.sql
psql "$DATABASE_URL" -f backend/migrations/20260513_drop_empty_legacy_stock_tables.sql
```

## Source-Neutral Stock Tables
- `stocks`
- `stock_prices_daily`
- `financial_statements`
- `ratios_snapshot`
- `shareholding_pattern`
- `corporate_events`
- `data_provider_runs`
- `data_quality_issues`
- `stock_core_snapshot`
- `provider_usage_logs`

All financial values use `numeric` columns. Unique constraints prevent duplicate symbol/date/source rows.

## Mutual Fund Tables
- `mutual_fund_core_snapshot`
- `mutual_fund_nav_history`
- `mutual_fund_holdings`
- `mutual_fund_sectors`
- Existing compatibility table remains: `mutual_funds`

Legacy `nifty_stocks` remains as a small search/fallback table. `mutual_fund_history`, `stock_history`, and `stock_fundamentals` were dropped after normalized tables became active.

Old CSV import helpers are isolated under `backend/scripts/deprecated/` and are not part of the active migration or production jobs.
