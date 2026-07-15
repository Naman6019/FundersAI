# API Contracts

## Frontend Proxy Routes (`frontend/app/api/`)

### Chat and Health
- `POST /api/chat` -> backend `POST /api/chat`.
- `GET /api/chat/history` -> authenticated user's saved chat messages.
- `DELETE /api/chat/history` -> clear authenticated user's saved chat messages.
- `GET /api/keepalive` -> backend `GET /health`.

### Quant Proxy Family
- `GET /api/quant/stocks/compare?symbols=RELIANCE,TCS` -> `/api/quant/stocks/compare`.
- `GET /api/quant/stocks/[symbol]/profile` -> `/api/quant/stocks/{symbol}/profile`.
- `GET /api/quant/stocks/[symbol]/financials` -> `/api/quant/stocks/{symbol}/financials`.
- `GET /api/quant/stocks/[symbol]/price-history` -> `/api/quant/stocks/{symbol}/price-history`.
- `GET /api/quant/stocks/nifty50/ticker` -> `/api/quant/stocks/nifty50/ticker`.
- `GET /api/quant/providers/status` -> `/api/quant/providers/status`.

### Frontend Server Routes With Direct Supabase Reads
- `GET /api/mf/[schemeCode]`: MF snapshot + history.
- `GET /api/search`: search across stock/fund entities.
- `GET /api/cron/sync-mf`: protected trigger route.

### Billing And Payments
- `POST /api/create-order`: Razorpay Standard Checkout order creation.
  - Request: `{ "amount": number, "currency"?: string, "receipt"?: string }`
  - Amount is paise and must be at least `100`.
  - Returns `{ "order_id": string, "amount": number, "currency": string }`.
- `POST /api/verify-payment`: Razorpay Standard Checkout HMAC verification.
  - Requires `razorpay_payment_id`, `razorpay_order_id`, and `razorpay_signature`.
  - Returns success only when `HMAC_SHA256(order_id + "|" + payment_id, RAZORPAY_KEY_SECRET)` matches.
- `GET /api/billing/subscriptions`: authenticated user's current billing state.
- `POST /api/billing/subscriptions`: create Razorpay subscription checkout payload for `pro` or `ultra`.
- `POST /api/billing/webhook`: Razorpay subscription webhook receiver.
  - Verifies raw-body webhook signature.
  - Stores event ids for idempotency.
  - Updates `billing_subscriptions` and paid tier state only from verified events.

### Admin Routes (`/api/admin/*`, admin-role enforced server-side)
- `GET /api/admin/session`
- `GET /api/admin/overview`
- `GET /api/admin/users`
- `GET /api/admin/ai-usage`
- `GET /api/admin/data-coverage`
- `GET /api/admin/nav-sync`
- `GET /api/admin/resolver-debug`
- `GET /api/admin/ops-overview` (proxy to backend admin ops endpoint)
- `POST /api/admin/data-coverage/documents/[documentId]/reparse`
- `POST /api/admin/data-coverage/documents/[documentId]/resolve`
- `POST /api/admin/data-coverage/documents/[documentId]/skip`

Auth behavior:
- Missing bearer token -> `401`
- Authenticated but non-admin -> `403`
- Admin check uses `user_profiles.role='admin'`

## Backend FastAPI Routes

### Core
- `GET /`: status message.
- `GET /health`: health probe.
- `GET /api/v1/providers/usage`: provider usage logs (feature-flag gated).

### Quant
- `GET /api/quant/stocks/compare`
- `GET /api/quant/stocks/{symbol}/profile`
- `GET /api/quant/stocks/{symbol}/financials`
- `GET /api/quant/stocks/{symbol}/price-history`
- `GET /api/quant/stocks/nifty50/ticker`
- `GET /api/quant/providers/status`

### Chat
- `POST /api/chat`: synthesized markdown plus structured `quant_data` / optional `system_action`.

### Mutual-Fund ML Research
- `GET /api/funds/{scheme_code}/similar?limit=5`: category-scoped, numeric peer discovery.
  - Returns `feature_version`, method, target cluster, peers with `similarity_score` and matching factors, plus explicit limitations.
  - Returns `not_found` or `insufficient_data` with no peers when the target/pool cannot support the calculation.
  - This is a research similarity signal, not a forecast or recommendation; it uses the existing `mf-detail` rate-limit group.

### Admin Internal Backend Endpoints (X-Admin-Key required)
- `GET /api/admin/ops-overview`
- `GET /api/admin/mf-resolver-debug?query=...&horizon=1Y|3Y|5Y`
- `GET /api/admin/mf-review-priorities?limit=1..500`: ranks `pending_review` parser items with explicit rule-based reasons. It is read-only and never performs a review action.

### Optional IndianAPI Helper Endpoints
Prefix: `/api/provider/indianapi`
- Stock search/profile/fundamentals/corporate-actions/recent-announcements/historical-data
- Analyst target/forecast endpoints
- Mutual fund search/list/details endpoints

## Contract Notes
- Compare responses keep additive fields (`metrics`, `fundamentals`, `ratios`, `data_quality`, `source_summary`, `why_better`, `verdict_context`, `comparison`).
- If local data is missing, endpoints return partial payloads with explicit limitations where possible.
- Admin resolver debug frontend route calls backend admin endpoint using `MF_INTERNAL_ADMIN_KEY` so internal secrets are not exposed to the browser.
- Public/high-cost routes are rate-limited. Over-limit responses return `429` with `{ "error": "rate_limited", "retry_after_seconds": number }` and standard rate-limit headers. In production, protected routes return `503 rate_limit_unconfigured` if Upstash Redis env vars are missing.
