# MarketMind: Technical Overview

This document provides a comprehensive technical breakdown of **MarketMind**, an AI-orchestrated financial research platform tailored for the Indian stock and mutual fund markets. It is intended for technical stakeholders, engineers, and architects looking to understand the system's architecture, data orchestration pipelines, and AI integration.

## 1. System Architecture & Topology

MarketMind utilizes a decoupled, serverless-friendly architecture that separates presentation, AI orchestration, and data persistence into distinct, scalable layers.

### Frontend (Presentation & Proxy)
- **Framework:** Next.js 16 (App Router) with React 19.
- **State Management:** Zustand for global states like chat history (`useChatStore.ts`) and interactive UI canvas states (`useCanvasStore.ts`).
- **Styling & UI:** Tailwind CSS 4, Framer Motion for transitions, and Recharts for dynamic data visualization (e.g., NAV charts, performance history).
- **Hosting:** Vercel.
- **Role:** Handles UI rendering, authentication (Supabase Auth in `AuthGate`), and acts as a proxy layer. Instead of direct external API calls, the frontend posts to Next.js API routes (e.g., `/api/chat`, `/api/quant/*`), which then forward requests securely to the backend.

### Backend (Orchestration & AI)
- **Framework:** FastAPI (Python), utilizing Pydantic for strict data validation.
- **Data Processing:** Pandas and NumPy for quantitative metric calculations and data transformations.
- **AI Engine:** Groq SDK (utilizing Llama 3 / Mixtral models) for low-latency LLM inference.
- **Hosting:** Render.
- **Role:** The analytical brain of the application. It exposes endpoints for chat intent routing, deterministic data fetching (quant endpoints), and reasoning processing. It orchestrates the flow between the user's prompt, the database, and the LLMs.

### Database (Persistence)
- **Database:** Supabase (PostgreSQL).
- **Role:** Serves as the primary, highly-normalized read path for the application. To ensure fast latency and protect against third-party API rate limits, the backend primarily reads from Supabase tables rather than fetching live data per request.

---

## 2. Data Flow & Orchestration

MarketMind relies on a "Source-Neutral" data architecture. This means the application code reads from normalized database tables and is agnostic to where the data originated. The data ingestion is handled asynchronously via automated pipelines.

### Asynchronous Data Ingestion (GitHub Actions)
Data freshness is maintained through a series of scheduled CRON jobs executed via GitHub Actions. These jobs run Python scripts (`backend/app/jobs/*`) that upsert data into Supabase.
- **Stock Prices:** EOD (End of Day) OHLCV data is synced daily using official NSE CM-UDiFF Bhavcopy zip files.
- **Mutual Funds:** Daily NAV updates are pulled from MFapi (AMFI data), while monthly enrichments (AUM, TER, Holdings) use MFdata.
- **Fundamentals & Corporate Events:** Weekly/Monthly scheduled pulls via FinEdge API (or fallbacks) for metrics like P/E, EPS, dividends, and splits.

### Runtime Application Data Path (Synchronous)
1. **User Request:** Frontend calls a proxy route (e.g., `GET /api/quant/stock?symbol=RELIANCE`).
2. **Backend Retrieval:** FastAPI receives the request and queries the local Supabase instance (e.g., `stock_core_snapshot`, `ratios_snapshot`).
3. **Deterministic Output:** The backend formats the relational data into structured, deterministic JSON payloads. Live provider calls are explicitly feature-flagged and generally avoided during the runtime read-path to ensure sub-second latency.

---

## 3. AI Agent Workflow & Intent Routing

MarketMind does not just use LLMs as a wrapper; it uses them as orchestrators for deterministic data.

1. **Intent Resolution:** When a user submits a prompt via `/api/chat`, the backend uses an LLM to classify the intent (e.g., *Quant/Metrics*, *News Sentiment*, *Screener*, or *Comparison*).
2. **Tool Execution:** Based on the resolved intent, the backend fetches the required deterministic data from Supabase.
3. **Synthesis & Formatting:** 
   - The LLM receives the raw deterministic data as context and generates a synthesized markdown response.
   - Concurrently, the backend computes deterministic reasoning (e.g., `why_better`, `verdict_context` for comparisons).
4. **Hybrid Rendering:** The frontend receives the response, rendering the LLM's markdown narrative alongside deterministic, interactive UI components (like Recharts and data tables) triggered by `system_action` flags in the payload.

---

## 4. Provider & Quota Strategy

To manage costs and API rate limits, MarketMind implements a strict Quota-Safe architecture.

- **Primary Read Path:** Supabase tables (`stock_core_snapshot`, `mutual_fund_core_snapshot`).
- **Free/Official Sources:** NSE India (Bhavcopy) for stock prices; MFapi for mutual fund NAVs.
- **Paid API Guarding:** Paid APIs like IndianAPI and FinEdge are heavily guarded. They are primarily used by the asynchronous CRON jobs to update the database, rather than serving live user traffic.
- **Quota Management:** Hard limits (`INDIANAPI_MONTHLY_LIMIT=5000`) and soft reserves are configured via environment variables. If quotas are exhausted, the backend degrades gracefully, serving stale cached data with freshness warnings rather than failing. All provider hits, cache hits, and quota skips are logged in a `provider_usage_logs` table for observability.

---

## 5. Database Schema (Key Tables)

The PostgreSQL database is highly normalized to support complex analytical queries:

- **Entity Metadata:** `stocks`
- **Time-Series Data:** `stock_prices_daily`, `mutual_fund_nav_history`
- **Fundamentals:** `financial_statements`, `ratios_snapshot`, `shareholding_pattern`
- **Read-Optimized Snapshots:** `stock_core_snapshot`, `mutual_fund_core_snapshot` (Materialized-style tables that aggregate data for ultra-fast frontend retrieval).
- **Telemetry:** `data_provider_runs`, `provider_usage_logs` (Audit logs for data jobs and API costs).
