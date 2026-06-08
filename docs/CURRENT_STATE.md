# Current State

**Last Updated**: 2026-06-08

## Project Summary
FundersAI is a research-first Indian stocks + mutual funds app with deterministic comparison outputs, Supabase-first runtime reads, and workflow-driven data ingestion.

## Stack Snapshot
- Frontend: Next.js `16.2.4`, React `19.2.4`, Tailwind CSS 4, Zustand, Recharts
- Backend: FastAPI + repository/service layers
- Database: Supabase (PostgreSQL)
- Storage: Cloudflare R2 (raw MF docs + cold archives)
- Automation: GitHub Actions workflows

## Implemented
- Supabase-auth dashboard (`/dashboard`) with `/auth` sign-in/sign-up.
  - Current implementation is one authenticated client workspace powered by `DashboardLayout`.
  - `DashboardLayout` owns the Overview / Research tab state and keeps the chat + comparison canvas flow in the same shell.
- Research-oriented landing page at `/`.
- Deterministic compare responses with `why_better`, structured winner context, and data limitation/freshness metadata.
- Source-neutral stock data model and scheduled stock workflows.
- Mutual-fund NAV sync and metadata pipelines.
- AMC disclosure ingestion pipeline for `ppfas`, `icici`, `hdfc`, `sbi`:
  - raw document ingestion
  - parsing
  - validation / review queue
  - R2-first storage
  - April 2026 holdings parser path verified clean for all four AMCs:
    - HDFC: parsed clean
    - SBI: parsed clean
    - PPFAS: parsed clean
    - ICICI: parsed clean
  - AMC holdings parsers keep stored holdings ISIN-only while using cash/TREPS/reverse-repo allocation rows for total exposure validation where needed.
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
  - `user_profiles` roles (`user|admin|tester`) and tiers (`free|pro|ultra`)
  - RLS policies for profile reads/updates
  - server-side admin checks for `/api/admin/*`
  - compatibility redirect `/dashboard/admin -> /admin`
- Razorpay monthly subscription foundation:
  - Free, Pro, and Ultra tier model
  - billing subscription/event tables
  - webhook-only tier activation
  - tier-aware request limits

## In Progress
- Dashboard-first onboarding flow:
  - users should land on the dashboard Overview first
  - AI Research should remain inside the same `/dashboard` shell for V1
  - dashboard CTAs should hand off into the existing chat/canvas state instead of creating new `/dashboard/research` or `/dashboard/compare` routes
- Increase mutual-fund field coverage depth beyond holdings for PPFAS, ICICI, HDFC, SBI (AUM/TER/benchmark/risk/ratios completeness).
- Reduce historical `needs_review` backlog in `mf_raw_documents` and `mf_parse_review_queue`.
- Improve admin Data Coverage status interpretation for historical parser failures vs latest-run health.
- Monitor scheduled parser retry outcomes for rows that remain in review after cooldown retries.

## Known Gaps
- `backend/render.yaml` references `uvicorn api.index:app`; repo runtime entry is `uvicorn app.main:app`.
- Scheduled fundamentals keep shareholding sparse when `ENABLE_SHAREHOLDING_SYNC=false`.
- Some admin metrics rely on fallback sources when canonical tables are incomplete.
- Data Coverage “fully covered” is strict and currently under-reports AMCs that only have partial field depth.

## Data Architecture Notes
- Runtime query-critical data remains in Supabase.
- Raw MF documents and archival payloads are stored in R2.
- Legacy heavy tables were dropped/compacted to protect Supabase free-tier storage limits.
- MF parse pipeline uses explicit states (`pending`, `downloaded`, `needs_reparse`, `parsed`, `needs_review`, `failed`, `skipped_not_supported`) to support reliability triage.
- `retry-mf-parser-actions.yml` retries cooled-down `needs_review` / `failed` parser rows every 6 hours; it does not replace parser fixes or admin skips for invalid source documents.
- Current parser reliability baseline uses local golden fixtures from the `AMC Data` set plus live April 2026 reparses for HDFC, SBI, and ICICI; PPFAS April 2026 was already clean in live ingestion.

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
- `retry-mf-parser-actions.yml`
- `migrate-mf-raw-to-r2.yml`
- `compact-mf-storage.yml`
- `keepalive.yml`
