<div align="center">

# 📈 FundersAI
**Research-first workspace for Indian stocks and mutual funds**

[![Next.js](https://img.shields.io/badge/Next.js-16.2.11-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS_4-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)

[Live App](https://www.fundersai.co.in) · [Code Repository](https://github.com/Naman6019/FundersAI)

</div>

---

## 🚀 Overview

FundersAI is a research-first web app for Indian stocks and mutual funds. It combines deterministic comparison metrics, Supabase-first runtime reads, official AMC-document evidence, and workflow-driven ingestion in one workspace.

FundersAI is research-only: it does not execute trades or provide personalized investment advice or buy/sell/hold calls.

## ✨ Key Features

- 🤖 **Research Chat & Intent Routing**: Routes questions to structured stock, mutual-fund, market-current-events, and comparison paths with visible status and limitation metadata.
- 📊 **Interactive Comparison Canvas**: Side-by-side NAV, returns, alpha, beta, Sharpe, drawdown, cost, AUM, holdings, risk, and freshness data where available.
- 📚 **Official-Document Evidence**: Indexes official AMC documents and returns citable excerpts, readable supported claims, or explicit abstention when evidence is insufficient.
- ⚙️ **Automated Data Pipelines**: GitHub Actions workflows handle stock data, mutual-fund metadata, NAV sync, AMC disclosure ingestion, retries, indexing, archiving, and storage maintenance.
- 🔒 **Quota-Safe Architecture**: Designed for resilience. Query-critical data is served directly from normalized Supabase tables, protected by intelligent quota guards for third-party enrichments (IndianAPI).
- 💼 **Auth & Subscriptions**: Secure workspace powered by Supabase Auth (Email & Google OAuth) with a Razorpay-backed subscription foundation for tiered access (Free, Pro, Ultra).
- 🛠️ **Admin Controls**: Dashboard surfaces AI usage, data coverage, parser diagnostics, resolver debugging, NAV sync, and bounded review actions.
- 🧠 **Explainable ML Foundations**: Numeric mutual-fund similarity/clustering and human-in-the-loop parser-review prioritization, both grounded in stored data rather than investment recommendations.
- 🔎 **Trust Metadata**: Freshness, missing fields, resolver confidence, partial coverage, research boundaries, and reasoning summaries remain visible around results.

## 🛠️ Tech Stack

**Frontend**
- Next.js 16.2.11 (App Router), React 19.2.4, TypeScript
- Tailwind CSS 4 for styling
- Zustand for state management
- Recharts for data visualization
- *Deployed on Vercel*

**Backend**
- Python, FastAPI
- Service & Repository layer architecture
- NSE and FinEdge scheduled stock providers with YFinance fallback paths
- AMFI, MFapi, and official AMC documents for mutual-fund data
- OpenRouter and Groq chat/extraction providers, direct OpenAI `text-embedding-3-small` document/query embeddings, and optional feature-flagged Langfuse tracing
- *Deployed on Render*

**Database, Storage & Infra**
- **Supabase (PostgreSQL)**: Primary datastore and authentication
- **Cloudflare R2**: Object storage for raw AMC documents and cold archives
- **GitHub Actions**: 17 workflows for sync, ingestion, retry, indexing, discovery, archive, migration, and compaction jobs

## 📁 Project Structure

```text
FundersAI/
├── .github/workflows/      # Automated CRON jobs for data sync and storage compaction
├── backend/                # Python/FastAPI app, fetching scripts, & parsers
├── frontend/               # Next.js web application & dashboard UI
├── docs/                   # Project documentation, architecture decisions, current state
└── prompts/                # AI Agent instructions and routing logic
```

## 📐 Data Architecture & Ingestion

FundersAI is built to handle complex, high-volume financial data efficiently without breaking the bank on provider quotas:

1. **Supabase-First Reads**: Runtime query-critical data lives in `stock_core_snapshot`, `mutual_fund_core_snapshot`, and the server-only `nav_api_cache` used for complete MFAPI histories.
2. **Cold Storage Strategy**: To protect database limits, raw Mutual Fund documents (AMC holdings, portfolios) and archival payloads are routed to Cloudflare R2.
3. **Resilient Ingestion Parsers**: Enabled AMC sources cover PPFAS, HDFC, ICICI, SBI, Axis, Motilal Oswal, and Nippon, with explicit tracking states (`pending`, `downloaded`, `needs_reparse`, `parsed`, `parsed_partial`, `needs_review`, `failed`, `skipped_not_supported`).
4. **Reviewable Ingestion**: Scheduled retries and admin review actions handle missed parses without hiding states such as `parsed_partial`, `needs_review`, or `failed`.
5. **Evaluation-First Research Retrieval**: The deterministic lexical baseline and v2 reranker use a versioned development seed. OpenAI vector retrieval and hybrid ranking have lexical fallback and remain separately gated by quality, latency, and cost evidence. The bounded evidence path returns cited official-document claims or abstains.

---

## 🤖 How Codex & GPT-5.6 Were Used

Codex with GPT-5.6 was used as FundersAI's primary engineering collaborator during development. It was used for repository-wide reasoning and implementation—not as an unreviewed source of financial facts or investment recommendations.

### Main contributions

- **Architecture and planning:** Mapped the existing Next.js, FastAPI, Supabase, R2, ingestion, and retrieval paths before extending them. This kept new work attached to real product flows instead of creating disconnected demo infrastructure.
- **Implementation:** Helped build and refine official-document retrieval, OpenAI vector search with lexical fallback, deterministic reranking and abstention, the bounded LangGraph evidence workflow, golden-set evaluation, Prefect job wrappers, MLflow training guards, Docker/GCP deployment scaffolding, monitoring, authentication, feedback, and chat persistence.
- **Debugging and hardening:** Traced failures across frontend, backend, migrations, provider configuration, and scheduled jobs; proposed focused fixes; and added regression coverage for the changed behavior.
- **Verification:** Ran targeted Pytest and Node contract tests, TypeScript checks, ESLint, production builds, retrieval evaluations, and safe orchestration dry runs. Failed checks were treated as blockers or documented limitations rather than hidden.
- **Documentation and demo preparation:** Updated architecture, API, deployment, ML, and current-state documentation and produced judge-facing walkthroughs that distinguish implemented, locally verified, deployed, and planned work.

### Human oversight

The developer defined the product scope, research-only boundary, official-source policy, provider budget, and deployment decisions; reviewed proposed changes; supplied authorized credentials; and retained control over production data and external actions. Codex did not autonomously execute trades, provide investment advice, apply destructive migrations, or promote unverified models.

### Runtime boundary

GPT-5.6 was used through Codex for software engineering, debugging, review, and documentation. It is not claimed as FundersAI's default production chat model. The deployed application uses its separately configured OpenRouter/Groq chat and extraction providers, while official-document and query embeddings use OpenAI `text-embedding-3-small`. Deterministic financial calculations and citation checks remain in application code.

---

## 🚀 Setup & Development

### 1. Environment Variables
Copy the `.env.example` file to create your local environments:
- `.env` (or `.env.local` inside `frontend/`)
- Backend `.env` inside `backend/`
See `.env.example` for required keys.

### 2. Run the Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Or .venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Run the Frontend
```bash
cd frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## 📖 Documentation
For agents and contributors, read [`Agents.md`](Agents.md) and the [documentation index](docs/README.md). The primary source of truth is [`docs/CURRENT_STATE.md`](docs/CURRENT_STATE.md); see [the API contracts](docs/03_API_CONTRACTS.md), [database schema](docs/04_DATABASE_SCHEMA.md), [ML guide](docs/11_ML_SYSTEMS.md), and [interviewer guide](docs/12_INTERVIEW_GUIDE.md) for focused explanations.

## 🧭 Current status boundaries

- The production AMC evidence corpus has verified vector backfills for six AMC corpora; hosted semantic-query verification is still a separate deployment check.
- The retrieval result of `14/14` is a development-seed benchmark, not a production-quality claim.
- Prefect, MLflow, Docker, and GCP files provide implementation foundations and reproducible scaffolding; the active production topology remains Vercel, Render, Supabase, Cloudflare R2, and GitHub Actions.
- FundersAI shows missing, partial, and stale data as limitations and does not convert them into investment recommendations.

## 📝 OpenAI Build Week submission note

If the submission form asks for the `/feedback` Session ID, use the alphanumeric session/task ID of the Codex conversation where most of FundersAI was built. Open that Codex task, use its task menu or feedback flow to copy the Session ID, and paste that value into Devpost. Do not use a Git commit hash, repository ID, Supabase project ID, or deployment ID.

## 🛡️ Provider Architecture (Quota-Safe)
- Supabase normalized tables are the primary read path for app/chat/comparison:
  - `stock_core_snapshot`
  - `mutual_fund_core_snapshot`
  - `nav_api_cache` (server-only, on-demand mutual-fund NAV history cache)
- IndianAPI is restricted to stock enrichment/fundamentals and protected by monthly/daily quota guard.
- Mutual fund NAV/history uses MFapi/AMFI paths, not IndianAPI.
- Provider attempts (cache hit, live success/failure, quota skip) are logged in `provider_usage_logs`.

## 📉 IndianAPI Quota Strategy
- `INDIANAPI_MONTHLY_LIMIT=5000`
- `INDIANAPI_MONTHLY_RESERVE=500`
- Scheduled jobs target max `4000` monthly usage.
- If quota is low/exhausted, backend returns cached stale data with freshness warnings.

## 🤖 Manual Sync Commands
```bash
python -m backend.app.jobs.sync_stock_universe
python -m backend.app.jobs.sync_latest_prices
python -m backend.app.jobs.sync_price_history --days 365
python -m backend.app.jobs.sync_fundamentals --scope watchlist
python -m backend.app.jobs.calculate_ratios
python -m backend.app.jobs.sync_mf_nav
python backend/scripts/sync_mf.py
python backend/scripts/sync_mf_metadata.py
```

## 🔍 Provider Usage Debug
- Enable endpoint: `ENABLE_PROVIDER_USAGE_ENDPOINT=true`
- Read usage: `GET /api/v1/providers/usage`
