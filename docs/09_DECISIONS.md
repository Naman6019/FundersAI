# Decisions Log

## Decision Template
**Date:** YYYY-MM-DD
**Decision:** [What was decided]
**Context:** [Why it was decided]
**Consequences:** [Impact on the system or workflow]

---

## Confirmed Decisions

**Date:** 2026-07-21
**Decision:** Keep public read-only data available during rate-limit-storage failures, while preserving fail-closed behavior for costly or mutating routes.
**Context:** An Upstash failure caused public MF/quant requests to return `503` even when the underlying read path was healthy.
**Consequences:** `quant`, `mf-detail`, `category-funds`, and `data-health` may continue when the limiter backend fails. Chat, official-document research, cron triggers, and admin mutations still return `503` when rate-limit protection cannot be established. Failure logs include the group, exception type, provider status where available, and exception representation.

**Date:** 2026-07-21
**Decision:** Persist chat through user-owned sessions and validate ownership before service-role writes.
**Context:** The frontend server uses the Supabase service role for reliable persistence, which bypasses browser RLS if ownership is not checked explicitly.
**Consequences:** `/api/chat` requires frontend authentication, validates any `session_id`, and writes only to `ai_chat_sessions`/`ai_chat_messages` rows owned by that user. The tables also retain RLS as defense in depth.

**Date:** 2026-07-20
**Decision:** Build the Fund Research Evidence Pipeline incrementally, evaluation-first, on the existing Supabase/R2/FastAPI substrate.
**Context:** FundersAI already has official-document ingestion, background indexing, versioned similarity, pgvector schema, retrieval metadata, and abstention. Adding every new infrastructure tool at once would make them decorative and remove the ability to measure which change improved the product.
**Consequences:** The implementation order is golden dataset and baseline, orchestration wrappers, labelled review model and MLflow, measured vector/reranker experiments, bounded LangGraph research workflow, then container/GCP proof and monitoring. Current production infrastructure remains active until a replacement demonstrates value. Each added component must produce visible run, experiment, trace, deployment, or alert evidence.

**Date:** 2026-07-20
**Decision:** Keep lexical rerank v2 as the default even though query-vector retrieval is now wired end to end behind a flag.
**Context:** The repository can embed a query and call the pgvector match function, but the current dataset is a small development seed without reviewer-verified latency, cost, or relevance evidence.
**Consequences:** `MF_RESEARCH_VECTOR_SEARCH_ENABLED=false` remains the default. Vector retrieval, the v3 cross-encoder, and LLM grading are experimental until compared on at least 50 reviewer-verified official-document cases.

### ADR-006: Adopt lexical rerank v2 as the development default
**Status:** Accepted for development; production gate pending reviewer data.
**Decision:** Use deterministic token-set reranking plus a corpus-coverage abstention gate by default. Keep query-vector retrieval behind `MF_RESEARCH_VECTOR_SEARCH_ENABLED=false`.
**Context:** On `fund_research_golden_v1`, the v1 lexical baseline passed 12/14 cases and abstained correctly on 1/3 unsupported questions. V2 passed 14/14 on the same fixture seed. The seed is too small and synthetic to justify a production-quality claim.
**Consequences:** The API exposes retrieval/reranker versions, mode, vector status, and query coverage. Vector cost is explicit and reversible. Production promotion requires at least 50 reviewer-verified cases plus latency/cost measurements.

**Date:** 2026-04-28
**Decision:** Use docs as shared agent memory.
**Context:** Context windows and chat memory often lose crucial details across sessions or when switching between agents (Codex, Antigravity, Gemini CLI).
**Consequences:** All agents MUST read `docs/` before starting and update `docs/` before finishing tasks. Chat history is not trusted as truth.

**Date:** 2026-04-28
**Decision:** Use one active editing agent at a time.
**Context:** Prevents race conditions, git conflicts, and divergent logic when multiple AI agents attempt to solve the same problem concurrently.
**Consequences:** Agents must wait for their turn and confirm they are the active editing agent.

**Date:** (Pre-existing)
**Decision:** Normalized Supabase Local History over Live API.
**Context:** YFinance frequently rate-limits and times out on Render free tiers.
**Consequences:** `stock_prices_daily` remains the local stock-history source. Complete MF NAV requests use server-only `nav_api_cache`; `mutual_fund_nav_history` remains temporarily available until the documented archive/readiness gate permits its manual drop. Older heavy compatibility tables were removed or compacted to reduce free-tier storage usage.

**Date:** (Pre-existing)
**Decision:** Next.js API Proxy Pattern.
**Context:** Calling FastAPI directly from the browser exposes backend URLs and can trigger CORS issues.
**Consequences:** The frontend browser never communicates with FastAPI directly. All requests proxy through `frontend/app/api/`.

**Date:** (Pre-existing)
**Decision:** GitHub Actions for Scheduled Tasks.
**Context:** Vercel serverless environments do not support native Python runtimes required for our fetching scripts.
**Consequences:** Data fetching (`run_fetch.py`, `sync_mf.py`) is triggered via GitHub Actions cron, not Vercel cron.

**Date:** 2026-05-01
**Decision:** Use source-neutral stock tables and provider adapters for fundamentals.
**Context:** CSV exports are not production-ready and paid provider choices may change.
**Consequences:** Active stock comparison and AI chat read `/api/quant` source-neutral data. Paid providers can be added later without rewriting the app.
