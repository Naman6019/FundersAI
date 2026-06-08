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
| `mf-sync.yml` | `30 17 * * 1-5` | `sync_mf.py` -> `sync_mf_history.py` -> `python -m backend.app.jobs.sync_mf_nav` -> `python -m backend.app.jobs.sync_mf_enrichment_unified` |
| `sync-mf-enrichment.yml` | Manual only | `python -m backend.app.jobs.sync_mf_enrichment_unified` (AMFI first, optional MFdata fallback) |
| `sync-mf-disclosures.yml` | `30 4 * * 1-5`, plus manual | `ingest_latest_amc_docs` + `parse_pending_documents` for `ppfas,icici,hdfc,sbi` (R2-first) |
| `retry-mf-parser-actions.yml` | `15 */6 * * *`, plus manual | `reparse_needs_review` for cooled-down `needs_review` / `failed` docs, default order `sbi,hdfc,icici,ppfas` |
| `migrate-mf-raw-to-r2.yml` | Manual | `migrate_mf_raw_to_r2` |
| `compact-mf-storage.yml` | `45 3 * * 0`, plus manual | `compact_mf_nav_5y` + `compact_mf_holdings_latest_only` |
| `keepalive.yml` | `*/10 * * * *` | Direct ping to Render `/health` |

## Runtime Expectations
- Jobs should be rerunnable (idempotent upserts).
- Stock EOD/history jobs are NSE bhavcopy-first and write `stock_prices_daily` with source `nse_bhavcopy`.
- Stock universe and fundamentals jobs are FinEdge-first and write source-neutral `stocks`, `financial_statements`, `ratios_snapshot`, and optional `shareholding_pattern`.
- MF disclosures workflow is strict by design (`--strict --fail-on-needs-review`), so `needs_review` rows can fail the run.
- MF parser retry is cooldown-based (`--min-age-hours`, default 6) and non-blocking for rows that still need review; true parser/classification issues still need code fixes or admin skip.
- MF enrichment is AMFI-first. Optional MFdata fallback fills blanks only and must not replace AMFI/AMC/MFapi values.
- MF disclosure ingestion is configured for R2-first storage (`MF_REQUIRE_R2_FOR_RAW_STORAGE=true`), while Supabase stores structured/query-critical rows and manifests.

## MF Storage Reduction Runbook
Run in this order when Supabase storage is high:
1. `migrate-mf-raw-to-r2.yml` with `dry_run=true` then `dry_run=false`.
2. `compact-mf-storage.yml` with `dry_run=true` then `dry_run=false`.
3. Re-run compaction weekly (already scheduled Sundays).

Recommended manual values:
- `migrate-mf-raw-to-r2.yml`: start `limit=300`, then scale up if stable.
- `compact-mf-storage.yml`: `nav_scheme_limit=400`, `holdings_group_limit=1500`.

## Compact Job Notes
- `compact-mf-storage.yml` has `timeout-minutes: 15` at workflow job level.
- Dry-run for NAV compaction is safe after the loop fix in `compact_mf_nav_5y.py` (dry-run now exits per scheme instead of re-reading the same batch forever).

## Required Workflow Secrets
- `SUPABASE_URL`
- `SUPABASE_KEY` (or service-role equivalent in runtime env)
- `R2_ENDPOINT`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_RAW_BUCKET`
- `R2_COLD_BUCKET`
- `FINEDGE_API_KEY` (stock universe/fundamentals/corporate events)
- `INDIAN_API_KEY` (only for explicitly enabled IndianAPI fallback/research flows)

## Notes
- Deprecated CSV scripts under `backend/scripts/deprecated/` are not scheduled.
- Keepalive workflow pings backend directly; frontend `/api/keepalive` is a separate client-side warm-up route.
- MF sync writes normalized history to `mutual_fund_nav_history` and snapshot data to `mutual_fund_core_snapshot`.
