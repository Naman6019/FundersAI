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
| `keepalive.yml` | `*/10 * * * *` | Direct ping to Render `/health` |

## Runtime Expectations
- Jobs should be rerunnable (idempotent upserts).
- Stock EOD/history jobs are NSE bhavcopy-first and write `stock_prices_daily` with source `nse_bhavcopy`.
- Fundamentals cadence is quota-aware:
  - Weekly watchlist scope (default cap 100)
  - Monthly full scope (`NIFTY500`, default cap 500)
  - Manual symbols scope for on-demand refresh
- `ENABLE_SHAREHOLDING_SYNC=false` in scheduled fundamentals workflow, so shareholding rows may remain sparse.
- Manual fundamentals dispatch now supports `enable_shareholding_sync=true` for targeted detail backfills.
- Fundamentals workflow can trigger full `stock_core_snapshot` refresh after ratios with `refresh_stock_core_snapshot=true`.

## Required Workflow Secrets
- `SUPABASE_URL`
- `SUPABASE_KEY`
- `INDIAN_API_KEY` (for stock enrichment workflows)

## Notes
- Deprecated CSV scripts under `backend/scripts/deprecated/` are not scheduled.
- Keepalive workflow pings backend directly; frontend `/api/keepalive` is a separate client-side warm-up route.
- MF sync jobs now write normalized history to `mutual_fund_nav_history` (and `mutual_fund_core_snapshot`), not legacy `mutual_fund_history`.
