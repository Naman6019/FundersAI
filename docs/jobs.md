# Jobs

GitHub Actions runs stock and mutual-fund sync jobs from `.github/workflows/`.

## Stock Workflows

| Workflow file | Schedule (UTC) | Job module |
|---|---|---|
| `sync-stock-universe.yml` | `0 1 1 * *` | `python -m backend.app.jobs.sync_stock_universe` |
| `sync-prices-daily.yml` | `30 12 * * 1-5` | `python -m backend.app.jobs.sync_latest_prices` |
| `sync-price-history.yml` | Manual | `python -m backend.app.jobs.sync_price_history` |
| `sync-fundamentals-weekly.yml` | `0 2 * * 6` and `0 2 1 * *`, plus manual | `python -m backend.app.jobs.sync_fundamentals` then `calculate_ratios` |
| `sync-corporate-events.yml` | `0 3 * * *` | `python -m backend.app.jobs.sync_corporate_events` |
| `backfill-stock-core-snapshot.yml` | Manual | `python -m backend.app.jobs.backfill_stock_core_snapshot` |

## Mutual Fund Workflows

| Workflow file | Schedule (UTC) | Steps |
|---|---|---|
| `mf-sync.yml` | `30 13 * * 1-5` | `sync_mf.py` -> `sync_mf_history.py` -> `sync_mf_metadata.py` -> `python -m backend.app.jobs.sync_mf_nav` |
| `sync-mf-enrichment.yml` | `0 4 2 * *`, plus manual | `python -m backend.app.jobs.sync_mf_enrichment` |
| `sync-mf-disclosures.yml` | `30 4 * * 1-5`, plus manual | `ingest_latest_amc_docs` + `parse_pending_documents` for `ppfas,icici,hdfc,sbi` (R2-first) |
| `compact-mf-storage.yml` | `45 3 * * 0`, plus manual | `compact_mf_nav_5y` + `compact_mf_holdings_latest_only` |
| `migrate-mf-raw-to-r2.yml` | Manual | `migrate_mf_raw_to_r2` |
| `keepalive.yml` | `*/10 * * * *` | Direct ping to Render `/health` |

## Runtime Expectations
- Jobs should be rerunnable (idempotent upserts).
- Stock EOD/history jobs are NSE bhavcopy-first and write `stock_prices_daily` with source `nse_bhavcopy`.
- Stock universe and fundamentals jobs are FinEdge-first and write source-neutral `stocks`, `financial_statements`, `ratios_snapshot`, and optional `shareholding_pattern`.
- Fundamentals cadence is quota-aware:
  - Weekly watchlist scope (default cap 100)
  - Monthly full scope (`NIFTY500`, default cap 500)
  - Manual symbols scope for on-demand refresh
- `ENABLE_SHAREHOLDING_SYNC=false` in scheduled fundamentals workflow, so shareholding rows may remain sparse.
- Manual fundamentals dispatch now supports `enable_shareholding_sync=true` for targeted detail backfills.
- Fundamentals workflow can trigger full `stock_core_snapshot` refresh after ratios with `refresh_stock_core_snapshot=true`.
- Corporate events are FinEdge-first. IndianAPI corporate-event fallback is disabled unless explicitly enabled.

## Required Workflow Secrets
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `FINEDGE_API_KEY` (for stock universe, fundamentals, and corporate events)
- `INDIAN_API_KEY` (only for explicitly enabled IndianAPI fallback/research workflows)

## Notes
- Deprecated CSV scripts under `backend/scripts/deprecated/` are not scheduled.
- Keepalive workflow pings backend directly; frontend `/api/keepalive` is a separate client-side warm-up route.
- MF sync jobs now write normalized history to `mutual_fund_nav_history` (and `mutual_fund_core_snapshot`), not legacy `mutual_fund_history`.
- MF enrichment writes MFdata fields into `mutual_fund_core_snapshot` and optional holdings/sectors into `mutual_fund_holdings` and `mutual_fund_sectors`.
- MF disclosure ingestion is configured for R2-first storage (`MF_REQUIRE_R2_FOR_RAW_STORAGE=true` in workflow env), while Supabase stores query-critical structured rows and manifest metadata.
