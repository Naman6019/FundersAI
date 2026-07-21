# API Contracts

**Last updated:** 2026-07-21

The supported browser boundary is the Next.js `/api/*` surface. Browser code must not call FastAPI directly. Unless noted otherwise, routes return JSON; chat uses Server-Sent Events (SSE).

## Authentication and Security

- `POST /api/chat` and all `/api/chat/sessions*` routes require a Supabase user session.
- `POST /api/feedback` requires a Supabase user session for general and response feedback. Logout feedback is accepted after sign-out with tighter validation and rate limiting.
- When chat receives a `session_id`, the Next.js proxy verifies that the session belongs to the authenticated user before service-role writes.
- Frontend `/api/admin/*` routes require an authenticated user whose `user_profiles.role` is `admin`.
- Internal FastAPI admin and document-ingestion mutations require `X-Admin-Key`; ingestion webhooks may use the configured webhook token where supported.
- `/api/cron/sync-mf` requires `CRON_SECRET`.
- Billing webhooks verify the raw-body Razorpay signature and store event identifiers for idempotency.
- The FastAPI chat route is intended to sit behind the authenticated Next.js proxy. It accepts proxy identity headers and an optional internal proxy key, but it does not independently validate a Supabase bearer token.

## Frontend Server Routes (`frontend/app/api/`)

### Chat and Health

- `POST /api/chat`
  - Requires authentication.
  - Proxies to backend `POST /api/chat`.
  - Validates optional session ownership, applies user/tier rate and token-budget checks, forwards trusted identity headers, and persists owned messages.
  - Returns `text/event-stream` events: `{type:"status",message}`, `{type:"final",payload}`, or `{type:"error",message}`.
  - Persists the owned session and finalizes token accounting before emitting the final event. Browser cancellation does not cancel the proxy's upstream accounting/persistence pump.
  - Removes the server-only `_usage` field before the final payload reaches browser clients.
  - The final payload contains synthesized markdown plus structured `quant_data`, trace/coverage/model metadata, and optional `system_action`.
- `GET /api/chat/history`: returns the authenticated user's legacy saved chat messages.
- `DELETE /api/chat/history`: clears the authenticated user's legacy saved chat messages.
- `GET /api/chat/sessions`: lists owned chat sessions, newest first.
- `POST /api/chat/sessions`: creates an owned chat session; defaults the title to `New Chat`.
- `GET /api/chat/sessions/[sessionId]`: returns messages only after ownership validation.
- `GET /api/keepalive`: proxies backend `GET /health`.
- `GET /api/data-health`: proxies the backend data-health summary.

### Feedback

- `POST /api/feedback`
  - Accepts `feedback_type` (`general`, `response`, or `logout`), a required integer `rating` from 1 to 5, and an optional comment up to 2,000 characters.
  - Requires `application/json`, rejects declared request bodies over 16 KiB, and blocks requests whose supplied `Origin` differs from the API origin.
  - General feedback is linked to the authenticated user.
  - Response feedback can include an owned assistant `message_id`, owned `session_id`, trace ID, page path, and a bounded response excerpt. Supplied message/session IDs are checked against the authenticated user before storage.
  - Logout feedback is intentionally public because Supabase sign-out happens first; chat identifiers and response excerpts are discarded for this type.
  - Writes are rate-limited and performed server-side with the service role.
  - Returns `503 feedback_storage_unavailable` when the production table/schema cache is unavailable; database details are logged server-side and are not returned to the browser.

### Quant Proxy Family

- `GET /api/quant/stocks/compare?symbols=RELIANCE,TCS`
- `GET /api/quant/stocks/[symbol]/profile`
- `GET /api/quant/stocks/[symbol]/financials`
- `GET /api/quant/stocks/[symbol]/price-history`
- `GET /api/quant/stocks/nifty50/ticker`
- `GET /api/quant/providers/status`

These routes proxy to their matching `/api/quant/*` FastAPI endpoints.

### Funds, Search, and Research

- `GET /api/mf/[schemeCode]`: MF snapshot plus NAV history from the server-only Supabase/MFapi cache path.
- `GET /api/search`: searches stock and fund entities.
- `GET /api/funds/category`: category fund list.
- `POST /api/funds/category/compare`: deterministic within-category comparison.
- `POST /api/funds/compare/verdict`: structured comparison summary with coverage and limitations.
- `POST /api/funds/research/answer`: bounded official-document research answer with citations or abstention.
  - Returns `answer_format=field_summary` for concise verified claims, `source_excerpts` when only matching raw evidence is available, or `abstention` when the evidence gate fails.
- `GET /api/funds/research/evaluation`: versioned development evaluation artifact used by the evidence UI.

### Billing and Payments

- `POST /api/create-order`: creates a Razorpay Standard Checkout order.
  - Request: `{ "amount": number, "currency"?: string, "receipt"?: string }`
  - Amount is in paise and must be at least `100`.
  - Returns `{ "order_id": string, "amount": number, "currency": string }`.
- `POST /api/verify-payment`: verifies `HMAC_SHA256(order_id + "|" + payment_id, RAZORPAY_KEY_SECRET)`.
- `GET /api/billing/subscriptions`: returns the authenticated user's billing state.
- `POST /api/billing/subscriptions`: creates a subscription checkout payload for `pro` or `ultra`.
- `POST /api/billing/webhook`: verifies and processes Razorpay subscription events idempotently.

### Admin Routes (`/api/admin/*`)

- Read routes: session, overview, users, AI usage, data coverage, NAV sync, resolver debug, and operations overview.
- Parser actions:
  - `POST /api/admin/data-coverage/documents/[documentId]/reparse`
  - `POST /api/admin/data-coverage/documents/[documentId]/resolve`
  - `POST /api/admin/data-coverage/documents/[documentId]/skip`

Missing authentication returns `401`; an authenticated non-admin returns `403`.

### Cron

- `GET /api/cron/sync-mf`: protected mutual-fund sync trigger.

## Backend FastAPI Routes

### Core and Providers

- `GET /`: service status.
- `GET /health`: health probe.
- `GET /api/data-health`: runtime data-health summary.
- `GET /api/v1/providers/usage`: feature-flagged provider usage logs.
- `GET /api/trigger-fetch`: rate-limited background fetch trigger.

### Chat

- `POST /api/chat`: SSE stream with intermediate orchestration status and a deterministic or provider-backed final research payload. Worker failures are logged server-side and returned as a generic safe error event.

### Quant

- `GET /api/quant/stocks/compare`
- `GET /api/quant/stocks/{symbol}/profile`
- `GET /api/quant/stocks/{symbol}/financials`
- `GET /api/quant/stocks/{symbol}/price-history`
- `GET /api/quant/stocks/nifty50/ticker`
- `GET /api/quant/providers/status`

### Funds

- `GET /api/funds/search`
- `GET /api/funds/category`
- `POST /api/funds/category/compare`
- `GET /api/funds/{scheme_code}/similar`
- `POST /api/funds/research/search`
- `POST /api/funds/research/answer`
- `GET /api/funds/research/evaluation`
- `GET /api/mf/{scheme_code}`
- `POST /api/funds/compare/verdict`

Similarity and research responses expose version/coverage metadata and remain research signals, not forecasts or recommendations.

`POST /api/funds/research/answer` also returns additive `model_usage` entries. Each entry identifies the processing stage, provider, model or deterministic component, purpose, and runtime status. The list contains only components used for that response and explicitly distinguishes OpenAI query embeddings from deterministic cited-answer construction.

### Internal MF Ingestion (`/api/internal/mf/*`)

- `GET /api/internal/mf/schemes/{scheme_name}/holdings`
- `POST /api/internal/mf/acquire-documents`
- `POST /api/internal/mf/upload-document`
- `GET /api/internal/mf/documents/{source_document_id}/signed-url`

Mutation and signed-object routes require the configured internal admin key or supported ingestion token.

### Internal Admin (`/api/admin/*`)

- `GET /api/admin/ops-overview`
- `GET /api/admin/mf-review-priorities?limit=1..500`
- `GET /api/admin/mf-resolver-debug?query=...&horizon=1Y|3Y|5Y`
- `POST /api/admin/mf-documents/{document_id}/request-reparse`
- `POST /api/admin/mf-documents/{document_id}/resolve`
- `POST /api/admin/mf-documents/{document_id}/skip`

All require `X-Admin-Key`.

### Optional IndianAPI Helpers

Prefix: `/api/provider/indianapi`

- Stock search, profile, fundamentals, corporate actions, recent announcements, and historical data
- Analyst target and forecast endpoints
- Mutual-fund search, list, and detail endpoints

## Rate Limits and Errors

- Configured over-limit responses return `429` with `error=rate_limited`, `retry_after_seconds`, `Retry-After`, and rate-limit headers.
- Public read-only backend groups `quant`, `mf-detail`, `category-funds`, and `data-health` continue when the Upstash rate-limit backend is unavailable.
- `chat`, `fund-research`, `cron-sync-mf`, and `admin-mutation` remain fail-closed and return `503 rate_limit_unavailable` or `503 rate_limit_unconfigured` when protection cannot be established.
- Non-stream service failures use FastAPI `detail` responses; streamed chat failures use `{type:"error",message}` and frontend proxies normalize their wording.
- Compare responses remain additive and include explicit coverage, freshness, source, and limitation metadata when data is partial.
