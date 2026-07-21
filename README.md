<div align="center">

# 📈 FundersAI
**AI-Orchestrated Financial Research Platform for Indian Markets**

[![Next.js](https://img.shields.io/badge/Next.js-16.2.4-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS_4-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)

</div>

---

## 🚀 Overview

FundersAI empowers retail investors with professional-grade insights by synthesizing quantitative metrics, news sentiment, and historical trends through a powerful multi-agent pipeline. It brings institutional-level research capabilities to individual investors with a clean, workflow-driven interface.

Designed with a **Supabase-first runtime**, **deterministic AI comparisons**, and **automated data ingestion**, FundersAI is built for scale, reliability, and precision.

## ✨ Key Features

- 🤖 **AI Chat & Intent Routing**: An intelligent agent system that analyzes your query and automatically routes it to specialized pipelines (Quant, News, Screener, or Comparison).
- 📊 **Interactive Comparison Canvas**: A deep-dive UI for side-by-side Mutual Fund comparisons, visualizing NAV charts, returns, alpha, beta, and Sharpe ratios with deterministic AI-generated winners.
- ⚙️ **Automated Data Pipelines**: Robust backend pipelines powered by GitHub Actions for daily EOD stock data fetches, mutual fund metadata syncs, and raw AMC disclosure ingestion.
- 🔒 **Quota-Safe Architecture**: Designed for resilience. Query-critical data is served directly from normalized Supabase tables, protected by intelligent quota guards for third-party enrichments (IndianAPI).
- 💼 **Auth & Subscriptions**: Secure workspace powered by Supabase Auth (Email & Google OAuth) with a Razorpay-backed subscription foundation for tiered access (Free, Pro, Ultra).
- 🛠️ **Comprehensive Admin Controls**: Built-in Admin Dashboard for tracking AI usage, data coverage triage, parser diagnostics, and user management.
- 🧠 **Explainable ML Foundations**: Numeric mutual-fund similarity/clustering and human-in-the-loop parser-review prioritization, both grounded in stored data rather than investment recommendations.
- 📚 **Official-Document Research Foundation**: Background indexing of parsed AMC documents, versioned chunks and embeddings, citable research search, and explicit abstention when evidence is unavailable.

## 🛠️ Tech Stack

**Frontend**
- Next.js 16.2.4 (App Router), React 19.2.4, TypeScript
- Tailwind CSS 4 for styling
- Zustand for state management
- Recharts for data visualization
- *Deployed on Vercel*

**Backend**
- Python, FastAPI
- Service & Repository layer architecture
- NSE and FinEdge scheduled stock providers with YFinance fallback paths
- AMFI, MFapi, and official AMC documents for mutual-fund data
- OpenRouter and Groq model providers, with optional Langfuse tracing
- *Deployed on Render*

**Database, Storage & Infra**
- **Supabase (PostgreSQL)**: Primary datastore and authentication
- **Cloudflare R2**: Object storage for raw AMC documents and cold archives
- **GitHub Actions**: 15 active workflows for sync, ingestion, retry, archive, migration, and compaction jobs

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
4. **Self-Healing Data**: Automated cooldown retries and scheduled cron jobs continuously attempt to resolve missed parses and sync pricing history.
5. **Evaluation-First Research Retrieval**: The recorded lexical baseline and deterministic v2 reranker use the same fixed dataset. Query-vector retrieval stays opt-in, and the bounded LangGraph path returns cited official-document excerpts or abstains.

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
