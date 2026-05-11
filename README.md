# MarketMind

MarketMind is an AI-orchestrated financial research platform for the Indian stock and mutual fund markets. It provides retail-investor-friendly insights by synthesizing quantitative metrics, news sentiment, and historical trends through a multi-agent pipeline.

## Features
- **AI Chat & Intent Routing**: Routes queries to Quant, News, Screener, or Comparison pipelines.
- **Interactive Canvas**: Deep-dive UI for side-by-side Mutual Fund comparisons (NAV charts, returns, alpha, beta, Sharpe).
- **Automated Data Pipelines**: Daily EOD stock data fetches and mutual fund syncs.
- **Quota-Safe Provider Layer**: Supabase-first reads with guarded IndianAPI enrichment.

## Tech Stack
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS, Zustand, Recharts (Deployed on Vercel)
- **Backend**: Python FastAPI, YFinance, Groq API, Feedparser (Deployed on Render)
- **Database**: Supabase (PostgreSQL)
- **Automation**: GitHub Actions

## Project Structure
```
MarketMind/
├── .github/workflows/      # Data synchronization cron jobs
├── backend/                # FastAPI application & fetching scripts
├── frontend/               # Next.js web application
├── docs/                   # Shared agent memory & architectural docs
└── prompts/                # AI Agent instructions
```

## Setup & Development

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

## Documentation
For agents and contributors, read the `AGENTS.md` file and the `docs/` folder. The primary source of truth is `docs/CURRENT_STATE.md`.

## Provider Architecture (Quota-Safe)
- Supabase normalized tables are the primary read path for app/chat/comparison:
  - `stock_core_snapshot`
  - `mutual_fund_core_snapshot`
  - `mutual_fund_nav_history`
- IndianAPI is restricted to stock enrichment/fundamentals and protected by monthly/daily quota guard.
- Mutual fund NAV/history uses MFapi/AMFI paths, not IndianAPI.
- Provider attempts (cache hit, live success/failure, quota skip) are logged in `provider_usage_logs`.

## IndianAPI Quota Strategy
- `INDIANAPI_MONTHLY_LIMIT=5000`
- `INDIANAPI_MONTHLY_RESERVE=500`
- Scheduled jobs target max `4000` monthly usage.
- If quota is low/exhausted, backend returns cached stale data with freshness warnings.

## Manual Sync Commands
```bash
python -m backend.app.jobs.sync_stock_universe
python -m backend.app.jobs.sync_latest_prices
python -m backend.app.jobs.sync_price_history --days 365
python -m backend.app.jobs.sync_fundamentals --scope watchlist
python -m backend.app.jobs.calculate_ratios
python -m backend.app.jobs.sync_mf_nav
python backend/scripts/sync_mf.py
python backend/scripts/sync_mf_history.py
python backend/scripts/sync_mf_metadata.py
```

## Provider Usage Debug
- Enable endpoint: `ENABLE_PROVIDER_USAGE_ENDPOINT=true`
- Read usage: `GET /api/v1/providers/usage`
