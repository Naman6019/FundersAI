# Agents Guide

This document provides essential context and instructions for AI agents working on the FundersAI project. It is intended to be read by agents to quickly understand the project's structure, tech stack, API routes, and testing conventions.

## Project Tech Stack

**Frontend**
- **Framework**: Next.js 16.2.4 (App Router)
- **Library**: React 19.2.4, TypeScript
- **Styling**: Tailwind CSS 4
- **State Management**: Zustand (`useCanvasStore`, `useChatStore`)
- **Visualizations**: Recharts
- **Hosting**: Deployed on Vercel

**Backend**
- **Framework**: Python, FastAPI
- **Architecture**: Service and Repository layer design
- **Integrations**: YFinance, Groq API, Feedparser
- **Hosting**: Deployed on Render

**Database, Storage & Infrastructure**
- **Database**: Supabase (PostgreSQL) - Serves as the primary datastore and handles authentication.
- **Storage**: Cloudflare R2 - Used for raw AMC (Asset Management Company) documents and cold archives.
- **Automation**: GitHub Actions - Over 12 active workflows for CRON jobs, data syncs, backups, and parser retries.

## API Routes

The project uses a split architecture where the Next.js frontend acts as a proxy for the FastAPI backend.

### Frontend Routes (`frontend/app/api/`)
- **Chat & Health**: `/api/chat` (Proxies to backend), `/api/chat/history`, `/api/keepalive`
- **Quant Proxy**: `/api/quant/stocks/compare`, `/api/quant/stocks/[symbol]/profile`, etc.
- **Direct Supabase Reads**: `/api/mf/[schemeCode]`, `/api/search`
- **Billing**: `/api/create-order`, `/api/verify-payment`, `/api/billing/subscriptions`, `/api/billing/webhook` (Razorpay)
- **Admin**: `/api/admin/session`, `/api/admin/overview`, `/api/admin/users`, `/api/admin/resolver-debug`, etc. (Role enforced server-side)

### Backend Routes (FastAPI)
- **Core**: `/`, `/health`, `/api/v1/providers/usage`
- **Quant**: `/api/quant/stocks/compare`, `/api/quant/stocks/{symbol}/profile`, etc.
- **Chat**: `/api/chat` (Synthesizes markdown and structured `quant_data`)
- **Admin**: `/api/admin/ops-overview`, `/api/admin/mf-resolver-debug` (Requires `X-Admin-Key` header)
- **IndianAPI**: `/api/provider/indianapi/*` (Optional helper endpoints)

## Small Intricacies & Architectural Details

1. **Supabase-First Runtime**: For speed and reliability, query-critical data (`stock_core_snapshot`, `mutual_fund_core_snapshot`, etc.) is read directly from normalized Supabase tables rather than calling external APIs at runtime.
2. **Quota-Safe IndianAPI Usage**: IndianAPI is strictly protected by monthly (`5000`) and daily limits. It is reserved for fundamental and stock enrichment, while MF NAV histories bypass it (using MFapi/AMFI).
3. **Deterministic Comparisons**: The AI comparison endpoints return consistent, additive fields (`metrics`, `fundamentals`, `ratios`, `verdict_context`, `comparison`) and gracefully degrade with partial payloads if some data is unavailable.
4. **Proxy Security**: Admin backend operations from the frontend are proxied securely using an internal `X-Admin-Key` to avoid exposing secrets to the browser.
5. **Data Ingestion States**: The mutual fund ingestion pipeline explicitly tracks states (`pending`, `parsed`, `needs_review`, `failed`) and stores raw heavy payload in Cloudflare R2 to save Supabase limits.
6. **Billing Integration**: Subscriptions and payments are handled securely using standard Razorpay checkouts with webhooks verifying signatures and maintaining idempotency.

## Test Files

There are numerous tracked script and test files in the workspace used for asynchronous execution validation, API tests, and deterministic payload tests. 

- **Root Level**:
  - `test_api.py`, `test_async_execute.py`, `test_async_execute3.py`, `test_async_execute4.py`, `test_compare.py`, `test_execute4.py`, `test_js_logic.js`
- **Backend Level (`backend/`)**:
  - `test_api.py`, `test_api_client.py`, `test_async_execute2.py`, `test_async_execute5.py` to `test_async_execute11.py`, `test_deterministic.py`, `test_regex.py`, `test_unavail.py`

*When writing new tests or validation logic, you may add to these tracked files or follow the existing nomenclature.*
