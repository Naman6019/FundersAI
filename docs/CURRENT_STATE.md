# Current State

**Last Updated**: 2026-05-20

## Project Summary
MarketMind is a research-first Indian stocks + mutual funds app with deterministic comparison outputs, Supabase-first runtime reads, and workflow-driven data ingestion.

## Stack Snapshot
- Frontend: Next.js `16.2.4`, React `19.2.4`, Tailwind CSS 4, Zustand, Recharts
- Backend: FastAPI + repository/service layers
- Database: Supabase (PostgreSQL)
- Storage: Cloudflare R2 (raw MF docs + cold archives)
- Automation: GitHub Actions workflows

## Implemented
- Supabase-auth dashboard (`/dashboard`) with `/auth` sign-in/sign-up.
- Research-oriented landing page at `/`.
- Deterministic compare responses with `why_better`, structured winner context, and data limitation/freshness metadata.
- Source-neutral stock data model and scheduled stock workflows.
- Mutual-fund NAV sync and metadata pipelines.
- AMC disclosure ingestion pipeline for `ppfas`, `icici`, `hdfc`, `sbi`:
  - raw document ingestion
  - parsing
  - validation / review queue
  - R2-first storage
- MF storage controls:
  - `migrate-mf-raw-to-r2.yml`
  - `compact-mf-storage.yml`
- Admin dashboard Phase 1 at `/admin`:
  - Overview
  - Users (read-only actions in Phase 1)
  - AI Usage
  - Data Coverage
  - NAV Sync
  - Resolver Debug
- Admin security foundation:
  - `user_profiles` roles (`user|admin|tester`) and tiers (`free|pro`)
  - RLS policies for profile reads/updates
  - server-side admin checks for `/api/admin/*`
  - compatibility redirect `/dashboard/admin -> /admin`

## In Progress
- Increase mutual-fund field coverage depth for PPFAS, ICICI, HDFC, SBI (especially holdings/sector/ratios completeness).
- Reduce `needs_review` backlog in `mf_raw_documents` and `mf_parse_review_queue`.
- Improve admin Data Coverage status interpretation for historical parser failures vs latest-run health.

## Known Gaps
- `backend/render.yaml` references `uvicorn api.index:app`; repo runtime entry is `uvicorn app.main:app`.
- Scheduled fundamentals keep shareholding sparse when `ENABLE_SHAREHOLDING_SYNC=false`.
- Some admin metrics rely on fallback sources when canonical tables are incomplete.
- Data Coverage “fully covered” is strict and currently under-reports AMCs that only have partial field depth.

## Data Architecture Notes
- Runtime query-critical data remains in Supabase.
- Raw MF documents and archival payloads are stored in R2.
- Legacy heavy tables were dropped/compacted to protect Supabase free-tier storage limits.
- MF parse pipeline uses explicit states (`pending`, `downloaded`, `needs_reparse`, `parsed`, `needs_review`, `failed`) to support reliability triage.

## Workflows In Use
- `sync-stock-universe.yml`
- `sync-prices-daily.yml`
- `sync-price-history.yml`
- `sync-fundamentals-weekly.yml`
- `sync-corporate-events.yml`
- `backfill-stock-core-snapshot.yml`
- `mf-sync.yml`
- `sync-mf-enrichment.yml` (optional fallback/manual)
- `sync-mf-disclosures.yml`
- `migrate-mf-raw-to-r2.yml`
- `compact-mf-storage.yml`
- `keepalive.yml`
