# MarketMind / Mooliq Codex Guide

This file is the working guide for agents in this repo.
Keep changes scoped, additive, and backward-compatible.

## Current Product State (May 2026)

- Product focus: research-only app for Indian stocks + mutual funds.
- Frontend: Next.js `16.2.4` + React `19.2.4` (`frontend/`).
- Backend: FastAPI (`backend/`).
- Primary data store: Supabase.
- Raw AMC document storage: R2-first pipeline (with metadata in Supabase).
- Admin dashboard Phase 1 is live at `/admin` with role checks.

## Hard Rules

1. Next.js version is `16.2.4`.
   - Before changing route handlers/caching conventions, read local Next docs:
   - `frontend/node_modules/next/dist/docs/`
2. Do not expose secrets in frontend.
   - Keep service-role/admin keys server-side only.
3. Keep compare/chat deterministic and Supabase-first for normal requests.
   - Do not add live third-party provider calls inside standard compare/chat flows.
4. Use additive schema/API changes only unless explicitly asked otherwise.

## Canonical App Paths

### Frontend Pages

- `/` landing
- `/auth` auth page
- `/dashboard` main app
- `/admin` admin dashboard (canonical)
- `/dashboard/admin` compatibility redirect to `/admin`

### Frontend Admin APIs (`frontend/app/api/admin/*`)

- `GET /api/admin/session`
- `GET /api/admin/overview`
- `GET /api/admin/ops-overview`
- `GET /api/admin/users`
- `GET /api/admin/ai-usage`
- `GET /api/admin/data-coverage`
- `GET /api/admin/nav-sync`
- `GET /api/admin/resolver-debug`

All admin APIs require bearer session auth and enforce role check server-side.

### Backend Endpoints (important)

- `GET /health`
- `GET /api/data-health`
- `GET /api/admin/ops-overview` (internal admin key protected)
- `GET /api/admin/mf-resolver-debug` (internal admin key protected)
- `GET /api/quant/stocks/compare`
- `GET /api/quant/stocks/{symbol}/profile`
- `GET /api/quant/stocks/{symbol}/financials`
- `GET /api/quant/stocks/{symbol}/price-history`
- `GET /api/mf/{scheme_code}`
- `POST /api/chat`

## Admin Access Model

- Role source: `user_profiles` table.
- Allowed roles: `user | admin | tester`.
- Tier field: `free | pro`.
- Admin route behavior:
  - Unauthenticated => redirect to `/auth`.
  - Authenticated non-admin => access denied.
- Do not rely on hidden links for access control.

## Mutual Fund Ingestion State

### Active AMC parser scope

- `ppfas`
- `icici`
- `hdfc`
- `sbi`

### Workflows currently in repo

- `sync-stock-universe.yml`
- `sync-prices-daily.yml`
- `sync-price-history.yml`
- `sync-fundamentals-weekly.yml`
- `sync-corporate-events.yml`
- `backfill-stock-core-snapshot.yml`
- `mf-sync.yml`
- `sync-mf-enrichment.yml`
- `sync-mf-disclosures.yml`
- `migrate-mf-raw-to-r2.yml`
- `compact-mf-storage.yml`
- `keepalive.yml`

### MF workflow behavior note

- `mf-sync.yml` and `sync-mf-disclosures.yml` can technically overlap but both may touch `mutual_fund_core_snapshot`.
- Prefer sequential execution to avoid write-order races.

## Core Tables Used (current)

### Admin and usage

- `user_profiles`
- `provider_usage_logs` (AI usage fallback source)
- `data_provider_runs`

### Mutual funds

- `mutual_funds`
- `mutual_fund_core_snapshot`
- `mutual_fund_nav_history`
- `mutual_fund_holdings`
- `mutual_fund_sectors`

### AMC disclosure pipeline

- `mf_amc_sources`
- `mf_raw_documents`
- `mf_schemes`
- `mf_scheme_holdings`
- `mf_scheme_monthly_metrics`
- `mf_parse_review_queue`
- `mf_r2_archive_manifests`

Note: legacy `mutual_fund_history` was removed in prior storage cleanup.

## Environment Variables (where they belong)

### Backend / jobs

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `GROQ_API_KEY`
- `MF_INTERNAL_ADMIN_KEY`
- `R2_ENDPOINT`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_RAW_BUCKET`
- `R2_COLD_BUCKET`

### Frontend

- `NEXT_PUBLIC_API_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY` (server-side usage in Next routes)
- `MF_INTERNAL_ADMIN_KEY` (server-side Next admin proxy usage)

## Local Commands

### Backend

```powershell
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```powershell
cd frontend
npm run dev
```

### Quick checks

```powershell
python -m py_compile backend/app/main.py
cd frontend; npm run lint
cd frontend; npm run build
cd frontend; node node_modules/typescript/bin/tsc --noEmit
```

## Known Practical Constraints

- MFdata endpoint reliability has been inconsistent; AMC document ingestion is the reliability-first path.
- `provider_usage_logs` is used as fallback for AI usage in admin pages when `ai_usage_events` is absent.
- `sync-mf-disclosures.yml` with very high `max_documents` and `parse_limit` can approach job timeout on GitHub-hosted runners (6 hours/job).
- Duplicate raw docs are skipped by checksum, so reruns are safe and incremental.
