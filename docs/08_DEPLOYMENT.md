# Deployment

## Current Topology
- Frontend: Vercel project rooted at `frontend/`.
- Backend: Render web service rooted at `backend/`.
- Data store: Supabase project used by both runtime and jobs.
- Scheduler: GitHub Actions workflows in `.github/workflows/`.

## Frontend (Vercel)
- Runtime: Next.js App Router.
- API routes under `frontend/app/api/*` act as the browser-safe backend boundary.
- Required envs:
  - `NEXT_PUBLIC_API_URL`
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
  - `CRON_SECRET` (for protected sync trigger route)

## Backend (Render)
- App entry for local dev: `uvicorn app.main:app --reload --port 8000`.
- Health endpoint: `GET /health`.
- Provider usage endpoint: `GET /api/v1/providers/usage` (flag-gated).
- Note: `backend/render.yaml` currently references `uvicorn api.index:app`, but `backend/api/index.py` is not present in this repo. Verify and align Render dashboard start command before relying on `render.yaml` as source of truth.

## Scheduled Workflows (GitHub Actions)

| Workflow | Schedule (UTC) | Purpose |
|---|---|---|
| `sync-stock-universe.yml` | `0 1 1 * *` | Monthly stock universe sync |
| `sync-prices-daily.yml` | `30 12 * * 1-5` | Weekday EOD price sync |
| `sync-price-history.yml` | Manual | Historical EOD backfill |
| `sync-fundamentals-weekly.yml` | `0 2 * * 6` + `0 2 1 * *` + manual | Fundamentals sync + ratio calc |
| `sync-corporate-events.yml` | `0 3 * * *` | Corporate action sync |
| `mf-sync.yml` | `30 13 * * 1-5` | MF NAV/history/metadata/snapshot pipeline |
| `sync-mf-enrichment.yml` | `0 4 2 * *` | MFdata holdings/sector/enrichment pipeline |
| `keepalive.yml` | `*/10 * * * *` | Direct Render `/health` ping |

## Secrets and Variables
- Repository secrets used by workflows:
  - `SUPABASE_URL`
  - `SUPABASE_KEY`
  - `FINEDGE_API_KEY` (stock universe/fundamentals/corporate events)
  - `INDIAN_API_KEY` (only for explicitly enabled IndianAPI fallback/research workflows)
- Optional repo variable:
  - `FUNDAMENTALS_WATCHLIST_SYMBOLS`

## Operational Checks
- Verify frontend proxies can reach backend URL.
- Verify backend `/health` and `/api/chat` latency after idle periods.
- Verify cron workflow last-run status and row-write counts in Supabase.
- Verify provider quotas/flags before enabling live enrichment paths.
