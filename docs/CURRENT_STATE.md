# Current State

**Last Updated**: 2026-07-20

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
  - `/dashboard` now opens the Overview tab by default.
  - `DashboardLayout` owns the Overview / Research tab state and keeps the chat + comparison canvas flow in the same shell.
  - Dashboard CTAs hand off into existing chat/canvas state instead of using `/dashboard/research` or `/dashboard/compare` routes.
- Supabase Google OAuth callback flow:
  - Google and email verification redirects use `/auth/callback`.
  - The callback exchanges the Supabase OAuth code and returns users to stored `next` path or `/dashboard`.
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
  - Standard Checkout order creation and signature verification routes
- Admin Data Coverage actions for parse triage:
  - reparse
  - resolve
  - skip
- Mutual-fund AUM/TER data health diagnostics read `mutual_fund_core_snapshot` enrichment rows and report AUM rows, TER rows, both, and supported AMC coverage.
- Exposed mutual fund `risk_level` and `fund_manager` on the UI dashboard based on successful AMC factsheet parsing.
- Backfilled 10 years of NIFTY 50 EOD history via a manual yfinance pipeline, fixing the alpha/beta metric calculations for older mutual funds.
- Explainable ML foundations:
  - `mf_similarity_numeric_holdings_v2`: numeric mutual-fund similarity and deterministic clustering, scoped to a fund category and backed by stored snapshot data, with holdings overlap exposed as separate supporting evidence;
  - admin-only, non-mutating parser-review prioritization with explicit score reasons;
  - feature/priority version markers and focused automated tests.
- Official-document research foundation:
  - pgvector-backed `amc_document_chunks` schema with parser, embedding, source, and report metadata;
  - explicit background indexing for parsed/partially parsed official AMC documents;
  - OpenRouter embeddings using the existing `OPENROUTER_API_KEY` boundary;
  - `POST /api/funds/research/search` returning citable excerpts and explicit abstention;
  - provider-free retrieval evaluation helper.
- Evidence-pipeline implementation foundation:
  - versioned `fund_research_golden_v1` development-seed dataset, runner, per-case results, and recorded lexical baseline;
  - Prefect 3.7.8 flow wrappers for existing ingestion, parsing, indexing, and evaluation jobs, with dry-run as the CLI default;
  - guarded `mf_review_logistic_v1` offline trainer with chronological validation and rule-baseline comparison;
  - MLflow 3.14 integration that logs only trained models and blocks registry aliases for unverified exports;
  - `amc_lexical_rerank_v2`, whose relevance gate improves the fixture seed from 12/14 to 14/14 passing cases while preserving seeded retrieval recall;
  - opt-in query-vector RPC integration with explicit lexical fallback and cost visibility;
  - bounded `fund_research_graph_v2` with deterministic/optional LLM relevance grading, one official-corpus rewrite, claim-level citation support validation, and abstention;
  - opt-in `amc_hybrid_cross_encoder_v3` using reciprocal-rank fusion plus a Cohere cross-encoder adapter with deterministic RRF fallback;
  - provider-free v2/v3 comparison artifact, optional live-embedding/cross-encoder benchmark flags, Langfuse experiment runner, and judge-facing `/dashboard/research-evidence` trace/evaluation view;
  - separate API/Prefect-worker containers, GCP deployment and alert-setup scripts, workflow telemetry, and offline review-feature drift checks.

## In Progress
- Replace the development-seed retrieval fixtures with at least 50 reviewer-verified official-document cases before enabling a production regression gate.
- Validate a Prefect deployment with equivalent parameters, retries, logs, and operator evidence before replacing any GitHub Actions scheduling.
- Increase mutual-fund field coverage depth beyond AUM/TER/holdings for PPFAS, ICICI, HDFC, SBI (benchmark/risk/ratios completeness).
- Reduce historical `needs_review` backlog in `mf_raw_documents` and `mf_parse_review_queue`.
- Improve admin Data Coverage status interpretation for historical parser failures vs latest-run health.
- Monitor scheduled parser retry outcomes for rows that remain in review after cooldown retries.

## Known Gaps
- The first golden dataset is a development seed rather than a production gate. V2 passes it completely, but that does not establish quality on real official-document questions.
- V3 vector retrieval, the cross-encoder, and the LLM relevance grader are implemented behind independent flags and remain disabled by default until reviewer-verified quality, latency, and provider-cost evidence exists.
- The committed v2/v3 judge report is provider-free and shows benchmark plumbing, not live cross-encoder quality; run the explicit live flags only with configured provider credentials.
- No persisted production evaluation-run history, Prefect deployment, Cloud Run proof, or production-trained review-priority model/registry alias is active yet.
- Docker/GCP files are reproducible proof scaffolding only; the current production topology is still Vercel + Render + Supabase + R2 + GitHub Actions.
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
- Cleanup and parser triage classification now recognizes known irrelevant documents, including ICICI quant files and legacy PPFAS pre-2026 `.xls` portfolio rows.

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
