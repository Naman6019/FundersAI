# Frontend Guide

**Last updated:** 2026-07-21

## Stack
- Next.js `16.2.4` (App Router)
- React `19.2.4`
- TypeScript
- Tailwind CSS 4
- Zustand
- Recharts

## Key Paths
- `app/page.tsx`: landing page.
- `app/dashboard/page.tsx`: authenticated workspace entry.
- `app/auth/page.tsx`: sign-in/sign-up entry.
- `app/auth/callback/page.tsx`: Supabase OAuth/email callback.
- `app/api/chat/route.ts`: backend chat proxy.
- `lib/chatStream.ts`: shared SSE parser used by full chat and inline copilot.
- `app/api/chat/sessions/**`: authenticated owned-session list/create/restore routes.
- `app/api/data-health/route.ts`: rate-limited backend health proxy.
- `app/api/quant/**`: backend quant proxy routes.
- `app/api/funds/**`: category, comparison-verdict, and official-document research routes.
- `app/api/create-order/route.ts`: Razorpay Standard Checkout order creation.
- `app/api/verify-payment/route.ts`: Razorpay Standard Checkout signature verification.
- `app/api/billing/**`: Razorpay subscription creation and webhook handling.
- `components/chat/`: prompt input + response rendering.
- `components/canvas/`: stock/fund/comparison visual panels.
- `components/billing/`: subscription tiers and Standard Checkout panel.
- `app/dashboard/research-evidence/page.tsx`: judge-facing research trace and evaluation surface.
- `store/useChatStore.ts`, `store/useCanvasStore.ts`: persistent client state.

## Auth Flow
- `AuthGate` wraps dashboard route.
- If user session is missing, client redirects to `/auth?next=<path>`.
- Google sign-in redirects to `/auth/callback`.
- Email verification redirects to `/auth/callback`.
- Callback exchanges the Supabase code with `exchangeCodeForSession`.
- Auth form stores the requested `next` path in `localStorage` and callback redirects there after session exchange.
- Supabase browser auth client is in `lib/supabaseBrowser.ts`.
- Sign-out clears the Supabase session and uses `window.location.replace('/auth')` to avoid a stale protected workspace.

## API Boundary Rules
- Browser should call only frontend routes (`/api/*`).
- `POST /api/chat` requires a Supabase session and validates optional chat-session ownership before service-role persistence.
- Chat consumes `status`, `final`, and `error` SSE events. The proxy strips `_usage`, saves owned history before the final event, and continues finalization if the browser disconnects.
- Backend URL resolution:
  - `chat` proxy uses `NEXT_PUBLIC_API_URL` in production.
  - quant proxy uses `BACKEND_API_URL` first, then `NEXT_PUBLIC_API_URL`.
- Never expose provider secrets in browser code.

## UI Behavior Notes
- On dashboard load, frontend triggers `/api/keepalive`.
- Chat and canvas stay in one workspace; canvas overlay should not clear chat state.
- Comparison/detail canvas relies on structured `quant_data` payload shape.
- Overview is the first post-login dashboard experience.
- AI Research is reached through the existing tab/CTA handoff, not a separate `/dashboard/research` route in V1.
- `pendingQuery` is the handoff mechanism from dashboard prompts into chat.
- Intermediate chat text resets for each request and follows backend intent, data-loading, and synthesis stages.
- Billing UI opens Razorpay Checkout from server-created orders/subscriptions; frontend never receives `RAZORPAY_KEY_SECRET`.

## Local Run
```bash
cd frontend
npm install
npm run dev
```

## Known Frontend Gaps
- Error surfaces are mostly generic (502/500) and can be made more user-specific.
- Provider-backed explanations can take tens of seconds; the UI needs a measured completion boundary or clearer long-running state.
