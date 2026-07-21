# Jobs

**Last updated:** 2026-07-21

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
| `mf-sync.yml` | `30 17 * * 1-5` | `sync_mf.py` -> `python -m backend.app.jobs.sync_mf_enrichment_unified` |
| `sync-mf-enrichment.yml` | Manual only | `python -m backend.app.jobs.sync_mf_enrichment_unified` (AMFI + AMC disclosures) |
| `discover-mf-documents.yml` | `15 3 * * 1-5`, plus manual | runs the bounded top-10 discovery supervisor, persists the report/manifest to R2 and `mf_discovery_runs`, and enforces a configurable completion gate; it does not ingest documents |
| `sync-mf-disclosures.yml` | `30 4 * * 1-5`, plus manual | preflight/Edge-R2 acquisition where required, then ingest + parse for `axis,hdfc,sbi,icici,ppfas,nippon` |
| `retry-mf-parser-actions.yml` | `15 */6 * * *`, plus manual | retries cooled-down `needs_review`, `failed`, and `parsed_partial` rows for the same six-AMC matrix |
| `archive-mf-nav-history.yml` | Manual | archives and verifies legacy NAV history, then emits the drop-readiness report |
| `migrate-mf-raw-to-r2.yml` | Manual | `migrate_mf_raw_to_r2` |
| `reacquire-mf-raw-to-r2.yml` | Manual | reacquires missing local raw documents into R2 |
| `compact-mf-storage.yml` | `45 3 * * 0`, plus manual | cleans expired `nav_api_cache` rows and compacts holdings to latest-only retention |
| `keepalive.yml` | `*/10 * * * *` | Direct ping to Render `/health` |

## Runtime Expectations
- Jobs should be rerunnable (idempotent upserts).
- Stock EOD/history jobs are NSE bhavcopy-first and write `stock_prices_daily` with source `nse_bhavcopy`.
- Stock universe and fundamentals jobs are FinEdge-first and write source-neutral `stocks`, `financial_statements`, `ratios_snapshot`, and optional `shareholding_pattern`.
- MF disclosures workflow is strict by design (`--strict --fail-on-needs-review`), so `needs_review` rows can fail the run.
- AMC discovery is manifest-only. Its default minimum is eight completed factsheet agents, and discovery-only AMCs require a separate parser review and production promotion.
- MF parser retry is cooldown-based (`--min-age-hours`, default 6) and non-blocking by default for rows that still need review; true parser/classification issues still need code fixes or admin skip.
- MF enrichment is AMFI + AMC disclosures only. It must not call unofficial fallback APIs for mutual-fund enrichment.
- MF disclosure ingestion is configured for R2-first storage (`MF_REQUIRE_R2_FOR_RAW_STORAGE=true`), while Supabase stores structured/query-critical rows and manifests.

## MF Storage Reduction Runbook
Run in this order when Supabase storage is high:
1. `migrate-mf-raw-to-r2.yml` with `dry_run=true` then `dry_run=false`.
2. Use `reacquire-mf-raw-to-r2.yml` for rows whose local raw file is missing and has no R2 object.
3. `compact-mf-storage.yml` with `dry_run=true` then `dry_run=false`.
4. Re-run compaction weekly (already scheduled Sundays).
5. Run `archive-mf-nav-history.yml` separately; never drop `mutual_fund_nav_history` unless its readiness artifact reports `drop_ready=true`.

Recommended manual values:
- `migrate-mf-raw-to-r2.yml`: start `limit=300`, then scale up if stable.
- `compact-mf-storage.yml`: tune `holdings_group_limit` conservatively; NAV cache retention is controlled by `MF_NAV_CACHE_RETENTION_DAYS` in the workflow.

## Compact Job Notes
- `compact-mf-storage.yml` cleans the server-only NAV API cache; it does not authorize dropping normalized legacy NAV history.

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

## Prefect Evidence-Pipeline Preview

`backend/orchestration/research_evidence_flow.py` wraps the existing ingestion, parsing, indexing, and retrieval-evaluation entry points. It does not replace GitHub Actions yet.

Install the orchestration-only dependency after the normal backend requirements:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\orchestration\requirements.in
```

Preview the exact stages without touching Supabase, R2, AMC sites, or OpenRouter:

```powershell
.\.venv\Scripts\python.exe -m backend.orchestration.research_evidence_flow --amcs hdfc,axis --parse-only
```

Live execution requires `--execute` plus the same Supabase, R2, AMC acquisition, and OpenRouter secrets used by the existing jobs. GitHub Actions remains authoritative until a Prefect deployment has equivalent retries, parameters, logs, and operator verification.

## Review-Priority Training

Install offline ML dependencies separately from the API runtime:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\ml\requirements.in
```

Export reviewed outcomes without notes or sample contents:

```powershell
.\.venv\Scripts\python.exe -m backend.ml.export_review_labels --output logs\review-labels.jsonl
```

Train and evaluate without MLflow registration:

```powershell
.\.venv\Scripts\python.exe -m backend.ml.train_review_priority --input logs\review-labels.jsonl --verified-reviewer-export
```

Add `--mlflow` to log a successful run. Add `--register-model` only for live reviewer data or an export explicitly confirmed with `--verified-reviewer-export`. Insufficient label volume or class coverage exits without creating a model artifact.
- Deprecated CSV scripts under `backend/scripts/deprecated/` are not scheduled.
- Keepalive workflow pings backend directly; frontend `/api/keepalive` is a separate client-side warm-up route.
- Complete MFAPI histories are cached on demand in server-only `nav_api_cache`; current NAV and derived metrics remain in `mutual_fund_core_snapshot`.
