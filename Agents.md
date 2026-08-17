# Agents Guide

**Last updated:** 2026-08-16

Use this guide for repository conventions and quick orientation. For the authoritative implementation snapshot, read `docs/CURRENT_STATE.md`; use the focused documents under `docs/` for API, schema, deployment, and ML details.

## Project Tech Stack

**Frontend**

- Next.js `16.2.11` App Router, React `19.2.4`, and TypeScript
- Tailwind CSS 4, shadcn/ui, and Base UI
- Zustand (`useCanvasStore`, `useChatStore`)
- Recharts for data visualization; Three.js for 3D graphics
- Animations & Scrolling: Framer Motion, GSAP, and Lenis
- Vercel production hosting

**Backend**

- Python, FastAPI, and Uvicorn
- Route, service, and repository layers
- Data processing: Pandas, NumPy, PyArrow
- PDF Parsing & Scraping: PyMuPDF, pdfplumber, pypdf, Playwright, BeautifulSoup4
- Supabase-first runtime reads
- NSE/FinEdge scheduled stock data with YFinance, nsetools, and jugaad-data fallback paths
- AMFI, MFapi, and official AMC documents for mutual-fund data
- OpenRouter and Groq chat/extraction paths; direct OpenAI `text-embedding-3-small` document/query embeddings
- AI Orchestration & Tracing: LangGraph for agent workflows; Langfuse tracing is optional and feature-flagged
- Google Cloud Run production hosting

**Database, storage, and automation**

- Supabase PostgreSQL for structured data and authentication
- Cloudflare R2 for raw AMC documents and cold archives
- 22 GitHub Actions workflows for discovery, acquisition, parsing, indexing, promotion, retry, archive, migration, and compaction jobs
- Razorpay for subscription and payment flows

## Runtime Boundaries

- The browser calls Next.js `/api/*` routes, not FastAPI directly.
- Query-critical data comes from normalized Supabase tables and server-only caches.
- OpenAI/OpenRouter/Groq provider keys, the Supabase service-role key, Razorpay secrets, and internal proxy keys stay server-side.
- The supported production domain is `https://www.fundersai.co.in`; `https://fundersai.co.in` redirects to it.
- `https://synthesis.fundersai.co.in` is a dedicated Synthesis Studio subdomain. `frontend/middleware.ts` rewrites its root request to `/reports` and issues an HTTP 308 redirect from `www.fundersai.co.in/synthesis` to the subdomain.
- FundersAI is research-only. Deterministic metrics and official-source evidence must not be presented as personalized investment advice.

## API Routes

### Frontend routes (`frontend/app/api/`)

- **Chat:** `/api/chat`, `/api/chat/history`, `/api/chat/sessions`, `/api/chat/sessions/[sessionId]`
- **Health:** `/api/keepalive`, `/api/data-health`
- **Feedback:** `/api/feedback` (authenticated app/response ratings; post-sign-out logout ratings)
- **Quant:** `/api/quant/stocks/*`, `/api/quant/providers/status`
- **Funds:** `/api/mf/[schemeCode]`, `/api/search`, `/api/funds/category`, `/api/funds/category/compare`, `/api/funds/compare/verdict`, `/api/funds/research/answer`, `/api/funds/research/evaluation`
- **Billing:** `/api/create-order`, `/api/verify-payment`, `/api/billing/subscriptions`, `/api/billing/webhook`
- **Admin:** `/api/admin/session`, overview/usage/coverage routes, resolver diagnostics, and document reparse/resolve/skip actions
- **Reports (Synthesis Studio):** `/api/reports/stream`, `/api/reports/pdf`, `/api/reports/supported-funds` — served under `/reports` and its dedicated `synthesis.fundersai.co.in` subdomain
- **Cron:** `/api/cron/sync-mf`

`POST /api/chat` requires an authenticated Supabase user and returns `status`, `final`, or `error` SSE events. When a `session_id` is supplied, the proxy validates ownership, persists the owned exchange before final delivery, and strips server-only usage metadata.

### Backend routes (FastAPI)

- **Core:** `/`, `/health`, `/api/data-health`, `/api/v1/providers/usage`, `/api/trigger-fetch`
- **Chat:** `POST /api/chat` (SSE status/final/error stream)
- **Quant:** `/api/quant/stocks/*`, `/api/quant/providers/status`
- **Funds:** search, category, category comparison, similarity, research search/answer/evaluation, MF detail, and comparison-verdict routes under `/api/funds/*` or `/api/mf/*`
- **MF ingestion:** holdings, document acquisition/upload, and signed-document URLs under `/api/internal/mf/*`
- **Admin:** operations, parser-review priorities, resolver diagnostics, and parser mutation routes under `/api/admin/*`; internal backend admin routes require `X-Admin-Key`
- **IndianAPI:** optional quota-aware helpers under `/api/provider/indianapi/*`

See `docs/03_API_CONTRACTS.md` for the complete route inventory and security behavior.

## Architectural Details

1. **Supabase-first runtime:** `stock_core_snapshot`, `mutual_fund_core_snapshot`, and server-only caches are preferred over request-time provider calls.
2. **NAV cache:** `nav_api_cache` serves complete MFapi histories. `mutual_fund_nav_history` must not be dropped until the documented archive/readiness gate passes.
3. **Rate limits:** public read-only groups (`quant`, `mf-detail`, `category-funds`, `data-health`) fail open only when the rate-limit backend is unavailable. Chat, fund research, cron, and admin mutations fail closed.
4. **Deterministic comparisons:** response fields are additive and return explicit coverage/limitation metadata when data is partial.
5. **Owned chat persistence:** `ai_chat_sessions` and `ai_chat_messages` are user-owned, RLS-protected tables; frontend service-role writes require an authenticated ownership check.
6. **Feedback:** `user_feedback` is service-role-only; general/response feedback requires authentication, response targets are ownership-checked, and post-sign-out feedback is anonymous and metadata-limited. The JSON endpoint enforces same-origin browser requests, bounded payloads, and a dedicated rate-limit bucket.
7. **MF ingestion states:** `pending`, `downloaded`, `needs_reparse`, `parsed`, `parsed_partial`, `needs_review`, `failed`, and `skipped_not_supported`.
8. **Official-document research:** deterministic lexical rerank v2 remains the fallback with abstention. Direct OpenAI vector retrieval is configured separately from optional v3 cross-encoder/LLM grading and must use the same 1,536-dimension embedding model for documents and queries.
9. **R2-first storage:** raw AMC documents stay in R2; Supabase stores query-critical structured rows and metadata.
10. **Subdomain routing:** `frontend/middleware.ts` inspects the request `host` header to route `synthesis.fundersai.co.in` traffic to the `/reports` Synthesis Studio surface, separate from the main `www.fundersai.co.in` app shell.

## Testing Conventions

- Backend tests live under `backend/tests/` (`98` tracked `test_*.py` modules at this update).
- Frontend contract tests live under `frontend/tests/` (`16` tracked `*.test.mjs` files at this update).
- Run focused tests for touched behavior first, followed by the relevant full suite.
- Typical full checks from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests
Set-Location frontend
node --test tests/*.test.mjs
npx tsc --noEmit
npm run lint
npm run build
```

- Also run `git diff --check`. Do not modify unrelated dirty-worktree files or temporary artifacts.

## Documentation Maintenance

- Update `docs/CURRENT_STATE.md` when implemented or deployed behavior changes.
- Update `docs/03_API_CONTRACTS.md` and `docs/04_DATABASE_SCHEMA.md` when routes or migrations change.
- Keep implemented, locally verified, deployed, and planned work clearly separated.
- Never claim a provider, migration, deployment, or live result without matching evidence.

## graphify

This project has a knowledge graph at `graphify-out/` with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, invoke the `graphify` skill before doing anything else.

Rules:

- Always use the published `graphifyy` distribution through `uvx`; it exposes the `graphify` command. The correct form is `uvx --from graphifyy graphify`, not `uvx graphify`.
- In sandboxed Windows sessions, point uv at a writable temporary cache before invoking Graphify:

  ```powershell
  $env:UV_CACHE_DIR = Join-Path ([System.IO.Path]::GetTempPath()) 'fundersai-uv-cache'
  uvx --from graphifyy graphify --version
  ```

  If the first run cannot download the package because network access is restricted, rerun the exact `uvx --from graphifyy graphify ...` command with the required sandbox escalation. Do not treat the misleading global-cache `os error 183` as graph corruption.
- For codebase questions, first run `uvx --from graphifyy graphify query "<question>"` when `graphify-out/graph.json` exists. Use `uvx --from graphifyy graphify path "<A>" "<B>"` for relationships and `uvx --from graphifyy graphify explain "<concept>"` for focused concepts.
- Dirty `graphify-out/` files are expected after hooks or incremental updates and are not a reason to skip Graphify.
- If Graphify cannot run, report the tooling error and continue with direct source inspection.
- Use `graphify-out/wiki/index.md` for broad navigation when it exists. Read `graphify-out/GRAPH_REPORT.md` only for broad architecture review or when targeted queries are insufficient.
- After modifying code, run `uvx --from graphifyy graphify update .` to keep the graph current. Documentation-only changes do not require an AST graph refresh.
