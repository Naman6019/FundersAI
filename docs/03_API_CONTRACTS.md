# API Contracts

## Frontend Proxy Routes (`frontend/app/api/`)

### Chat and Health
- `POST /api/chat` -> proxies to backend `POST /api/chat`.
- `GET /api/keepalive` -> pings backend `/health`.

### Quant Proxy Family
- `GET /api/quant/stocks/compare?symbols=RELIANCE,TCS` -> `/api/quant/stocks/compare`.
- `GET /api/quant/stocks/[symbol]/profile` -> `/api/quant/stocks/{symbol}/profile`.
- `GET /api/quant/stocks/[symbol]/financials` -> `/api/quant/stocks/{symbol}/financials`.
- `GET /api/quant/stocks/[symbol]/price-history` -> `/api/quant/stocks/{symbol}/price-history`.
- `GET /api/quant/stocks/nifty50/ticker` -> `/api/quant/stocks/nifty50/ticker`.
- `GET /api/quant/providers/status` -> `/api/quant/providers/status`.

### Frontend Server Routes With Direct Supabase Reads
- `GET /api/mf/[schemeCode]`: reads MF snapshot + history from Supabase tables.
- `GET /api/search`: search endpoint across stock/fund entities.
- `GET /api/cron/sync-mf`: protected trigger route for AMFI sync helper.

## Backend FastAPI Routes

### Core
- `GET /`: basic API status message.
- `GET /health`: backend health probe.
- `GET /api/v1/providers/usage`: provider usage logs (flag-gated by `ENABLE_PROVIDER_USAGE_ENDPOINT`).

### Quant
- `GET /api/quant/stocks/compare`
- `GET /api/quant/stocks/{symbol}/profile`
- `GET /api/quant/stocks/{symbol}/financials`
- `GET /api/quant/stocks/{symbol}/price-history`
- `GET /api/quant/stocks/nifty50/ticker`
- `GET /api/quant/providers/status`

### Chat
- `POST /api/chat`: returns synthesized markdown plus structured `quant_data` and optional `system_action`.

### Optional IndianAPI Helper Endpoints
Prefix: `/api/provider/indianapi`
- Stock search/profile/fundamentals/corporate-actions/recent-announcements/historical-data.
- Analyst target/forecast endpoints.
- Mutual fund search/list/details endpoints.

## Contract Notes
- Compare responses keep additive fields (`metrics`, `fundamentals`, `ratios`, `data_quality`, `source_summary`, `why_better`, `verdict_context`, `comparison`).
- If local data is missing, endpoints return partial payloads with explicit limitations instead of hard failing whenever possible.
- Route-level rate limiting for frontend proxy endpoints is still pending.
