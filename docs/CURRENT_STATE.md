# Current State

**Last Updated**: 2026-05-17

## Project Summary
MarketMind is a research-only Indian equities and mutual fund platform.

## Stack Snapshot
- Frontend: Next.js `16.2.4`, React `19.2.4`, TypeScript, Zustand, Recharts
- Backend: FastAPI + provider/service/repository layers
- Database: Supabase (PostgreSQL)
- Automation: GitHub Actions workflows

## Implemented
- Supabase-auth-gated dashboard (`/dashboard`) with sign-in/sign-up flow under `/auth`.
- Frontend API proxy boundary for chat and quant endpoints.
- Deterministic stock comparison payload with:
  - `why_better`
  - structured winner object
  - `verdict_context`
  - source freshness and data limitation fields
- Source-neutral stock data architecture with repository + provider adapters.
- Stock EOD and price history jobs using NSE bhavcopy.
- Mutual-fund sync chain (AMFI + MFapi NAV/history + MFdata enrichment + local metrics write path).
- Provider usage endpoint support (`/api/v1/providers/usage`) behind feature flag.

## In Progress
- Frontend route-level rate limiting for `/api/chat` and `/api/quant/*` proxies.
- Broader stock coverage tuning (`NIFTY500` / `NIFTYTOTALMARKET` / enrichment limits).
- Mutual-fund holdings completeness via monthly MFdata enrichment.

## Known Gaps
- `backend/render.yaml` references `uvicorn api.index:app`, but `backend/api/index.py` is not in this repo; deployment command source-of-truth needs alignment.
- `ENABLE_SHAREHOLDING_SYNC=false` in scheduled fundamentals workflow keeps shareholding coverage sparse unless targeted manually.
- YFinance remains fallback and may rate-limit on hosted environments.
- News ingestion is RSS-based and can be slow.
- Frontend proxy error messages are mostly generic and can be improved.

## Data Architecture Notes
- Source-neutral migrations and tables are active under `backend/migrations/` and Supabase.
- `mutual_fund_history`, `stock_history`, and `stock_fundamentals` were removed to keep Supabase storage within the free tier.
- `nifty_stocks` remains as a small search/fallback table until stock search is fully moved to `stocks`.
- Stock comparison/chat flows are expected to return partial results with explicit limitations instead of blocking on missing fields.

## Workflows In Use
- `sync-stock-universe.yml`
- `sync-prices-daily.yml`
- `sync-price-history.yml`
- `sync-fundamentals-weekly.yml`
- `sync-corporate-events.yml`
- `backfill-stock-core-snapshot.yml`
- `sync-mf-enrichment.yml`
- `mf-sync.yml`
- `keepalive.yml`
