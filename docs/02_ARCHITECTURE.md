# Architecture

## System Shape
MarketMind is a split web architecture:
- Next.js frontend for UI + server-side proxy/admin routes
- FastAPI backend for analysis orchestration and internal admin diagnostics
- Supabase as primary structured runtime store
- Cloudflare R2 for raw MF documents and cold archives
- GitHub Actions for recurring sync/ingestion/compaction jobs

## Component Boundaries

### Frontend (`frontend/`)
- `/dashboard` is auth-gated.
- `/admin` is admin-gated with `AdminAccessGate` + server-side `/api/admin/*` role checks.
- `/dashboard/admin` redirects to `/admin` for compatibility.
- Chat submits to `POST /api/chat`.
- Quant panels fetch through `frontend/app/api/quant/*`.
- Admin pages fetch through `frontend/app/api/admin/*`.
- Shared app state uses Zustand (`useCanvasStore`, `useChatStore`).

### Backend (`backend/app/`)
- `main.py` hosts health, chat, quant compatibility endpoints, and internal admin endpoints.
- `routes/quant.py` exposes canonical `/api/quant/*`.
- `routes/indianapi.py` exposes optional `/api/provider/indianapi/*`.
- `repositories/stock_repository.py` centralizes Supabase stock table access.
- `services/quant_service.py` and `services/comparison_reasoning.py` build deterministic compare payloads.
- MF ingestion modules (`mf_ingestion/*`) handle AMC discovery, parsing, validation, review queue, and R2/archive writes.

## Data Paths

### Runtime Chat/Quant Path
1. Frontend calls `/api/chat` or `/api/quant/*`.
2. Proxy forwards to backend.
3. Backend reads Supabase-first tables.
4. Response includes deterministic payloads and limitations where data is missing.

### Admin Path
1. Frontend `/admin` checks `/api/admin/session`.
2. Server validates bearer token and `user_profiles.role`.
3. Admin route handlers query Supabase service-role clients.
4. Resolver Debug proxies to backend `/api/admin/mf-resolver-debug` with `X-Admin-Key`.

### MF Disclosure Ingestion Path
1. Workflow runs `ingest_latest_amc_docs` for selected AMCs.
2. Raw docs are stored in R2-first mode.
3. `parse_pending_documents` extracts factsheet/holdings and writes normalized tables.
4. Invalid/low-confidence parses are marked `needs_review` and queued for review.
5. Compaction/migration workflows move stale or raw-heavy data out of hot Supabase tables.

## Provider Strategy
- Runtime reads are Supabase-first.
- Stock prices are NSE bhavcopy-first in scheduled jobs.
- FinEdge is the primary fundamentals/corporate-events job source.
- MFdata enrichment remains optional/manual fallback.
- IndianAPI endpoints are optional and quota-aware.

## Auth Model
- User auth: Supabase auth session.
- Admin auth: `user_profiles.role='admin'` + server-side checks.
- Internal backend admin diagnostics: `X-Admin-Key` header.
