# Architecture

## System Shape
FundersAI is a split web architecture:
- Next.js frontend for UI + server-side proxy/admin routes
- FastAPI backend for analysis orchestration and internal admin diagnostics
- Supabase as primary structured runtime store
- Cloudflare R2 for raw MF documents and cold archives
- GitHub Actions for recurring sync/ingestion/compaction jobs

The next infrastructure work extends this shape rather than replacing it. The target is a versioned Fund Research Evidence Pipeline built on the existing Supabase, R2, FastAPI, and background-job boundaries.

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

### Fund Research Evidence Path
1. Only parsed or partially parsed official AMC documents are eligible for indexing.
2. `index_parsed_documents` resolves the R2-backed document and creates deterministic text chunks in a background job.
3. `DocumentIndexingService` creates versioned OpenRouter embeddings and stores source, parser, embedding, and report-month metadata with every chunk.
4. `POST /api/funds/research/search` returns citable official-document excerpts and an explicit abstention state.
5. The default `amc_lexical_rerank_v2` path applies a deterministic reranker and evidence-coverage gate; optional query embeddings call the pgvector RPC only when `MF_RESEARCH_VECTOR_SEARCH_ENABLED=true`.
6. `POST /api/funds/research/answer` runs a bounded LangGraph workflow that produces cited excerpts or abstains.
7. `evaluate_retrieval` compares fixed retrieval variants on a provider-free, versioned dataset.

The recorded v1 seed baseline passed 12 of 14 cases and had `0.3333` abstention accuracy. The v2 development experiment passed 14 of 14 and reached `1.0` abstention accuracy without reducing seeded retrieval recall. These are fixture results, not production-quality claims. Vector mode remains opt-in until it is evaluated on reviewer-verified official-document cases and its latency and embedding cost are measured.

### Ordered Evidence-Pipeline Additions
1. Versioned golden retrieval dataset and baseline evaluation.
2. Prefect wrappers around existing ingestion, parsing, indexing, and evaluation entry points.
3. Reviewer-labelled training data and a supervised review-priority model, tracked in MLflow only when labels are sufficient.
4. Measured vector retrieval and reranker experiments.
5. A LangGraph workflow limited to official-document research questions.
6. Container/GCP deployment proof and end-to-end monitoring, drift checks, alerts, and runbooks.

The implementation scaffolds for all six additions now exist, including separate API/worker containers, a GCP deployment script, log-derived alert setup, and offline feature-drift checks. GitHub Actions and the existing Render deployment remain production until Prefect and Cloud Run are exercised with live proof artifacts.

## Provider Strategy
- Runtime reads are Supabase-first.
- Stock prices are NSE bhavcopy-first in scheduled jobs.
- FinEdge is the primary fundamentals/corporate-events job source.
- Mutual-fund enrichment uses AMFI + AMC disclosures only.
- IndianAPI endpoints are optional and quota-aware.

## Auth Model
- User auth: Supabase auth session.
- Admin auth: `user_profiles.role='admin'` + server-side checks.
- Internal backend admin diagnostics: `X-Admin-Key` header.
