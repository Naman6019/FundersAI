# Architecture

## System Shape
MarketMind is a split web architecture:
- Next.js frontend for UI + server-side proxy routes.
- FastAPI backend for analysis orchestration.
- Supabase as persistent storage and primary read path.
- GitHub Actions for recurring data sync jobs.

## Component Boundaries

### Frontend (`frontend/`)
- `app/dashboard/page.tsx` is protected by `AuthGate`.
- Chat submits to `POST /api/chat` via `frontend/app/api/chat/route.ts`.
- Quant panels fetch through `frontend/app/api/quant/*` proxies.
- Canvas state and chat state are kept in Zustand stores (`store/useCanvasStore.ts`, `store/useChatStore.ts`).

### Backend (`backend/app/`)
- `main.py` hosts root, health, chat, quant compatibility endpoints, and provider-usage endpoint.
- `routes/quant.py` exposes canonical `/api/quant/*` routes and provider status.
- `routes/indianapi.py` exposes optional research endpoints under `/api/provider/indianapi/*`.
- `repositories/stock_repository.py` centralizes Supabase stock table access.
- `services/quant_service.py` builds deterministic stock comparison/profile/financials/history payloads.
- `services/comparison_reasoning.py` computes deterministic `why_better` and `verdict_context`.

## Data Paths

### Chat Path
1. Frontend posts user prompt to `/api/chat` proxy.
2. Backend `/api/chat` resolves entity intent and data.
3. Backend returns markdown summary + structured `quant_data` payload.
4. Frontend renders markdown and opens comparison/detail canvas when `system_action` exists.

### Quant Path
1. Frontend GETs `/api/quant/*` proxy routes.
2. Proxy forwards request to backend base URL.
3. Backend reads local Supabase-first data; provider calls are optional/fallback and flag-driven.
4. Response includes compatibility fields (`comparison`) and deterministic reasoning metadata.

### Scheduled Sync Path
1. GitHub Actions runs on cron/manual dispatch.
2. Workflows call Python jobs/scripts.
3. Jobs upsert into source-neutral tables and logs.
4. Runtime API reads from these local tables.

## Provider Strategy
- `STOCK_DATA_PROVIDER` picks active provider (`manual`, `nse`, `indianapi`, `finedge`, `yfinance`).
- If selected provider is unavailable, code falls back to `manual` provider.
- NSE bhavcopy is the default stock price history path for jobs.
- IndianAPI endpoints are used in controlled, quota-aware flows.

## Auth Model
- Dashboard access is gated by Supabase auth in `AuthGate`.
- Sign-in/sign-up flow lives at `/auth`.
- Browser auth depends on `NEXT_PUBLIC_SUPABASE_URL` + `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
