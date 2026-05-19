# Technical Overview

## 1. Topology
- Frontend: Next.js App Router (`frontend/`) on Vercel
- Backend: FastAPI (`backend/app/`) on Render
- Primary DB: Supabase (PostgreSQL)
- Object storage: Cloudflare R2
- Automation: GitHub Actions workflows

## 2. Runtime Read Path
1. Browser calls Next server routes (`/api/chat`, `/api/quant/*`, `/api/admin/*`).
2. Next routes enforce browser-safe boundaries and admin checks where needed.
3. Backend fetches Supabase-first data and composes deterministic payloads.
4. Frontend renders structured outputs (tables/charts/badges) with explicit limitation states when data is missing.

## 3. Mutual Fund Ingestion Path
- `sync-mf-disclosures.yml` ingests AMC documents for `ppfas,icici,hdfc,sbi`.
- Raw documents are stored in R2-first mode.
- Parser writes:
  - `mf_raw_documents` state updates
  - normalized parsed rows (`mf_scheme_holdings`, `mf_scheme_monthly_metrics`)
  - review queue entries for low-confidence parses
- Derived holdings/sector views sync into runtime MF tables only when validation passes.

## 4. Storage Management
- `migrate-mf-raw-to-r2.yml`: migrates raw docs out of local/Supabase paths to R2 metadata-backed storage.
- `compact-mf-storage.yml`: archives old NAV/holdings slices to R2 and trims hot tables.
- Compaction supports dry-run and scheduled maintenance.

## 5. Admin Platform (Phase 1)
- Route: `/admin` (with `/dashboard/admin` redirect)
- Access model:
  - Supabase session required
  - `user_profiles.role='admin'` required
  - all `/api/admin/*` routes enforce server-side admin checks
- Implemented views:
  - Overview
  - Users
  - AI Usage
  - Data Coverage (includes `needs_review` section)
  - NAV Sync
  - Resolver Debug

## 6. Internal Admin Diagnostics
- Backend provides protected endpoints:
  - `/api/admin/ops-overview`
  - `/api/admin/mf-resolver-debug`
- Next admin resolver route proxies with `MF_INTERNAL_ADMIN_KEY` so secret keys remain server-side.

## 7. Reliability Notes
- Runtime is designed to degrade gracefully with partial responses when data is incomplete.
- MF parser runs may fail intentionally when `needs_review` is treated as strict failure.
- Coverage badges reflect table-level field completeness, not just workflow success.
