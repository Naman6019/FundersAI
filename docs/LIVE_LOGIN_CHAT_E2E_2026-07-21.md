# FundersAI Live Login-to-Chat E2E Report

**Date:** 2026-07-21  
**Frontend tested:** `https://fundersai.co.in`  
**Backend:** `https://marketmind-hz03.onrender.com`  
**Production commit:** `ea5d98fbecbb3c87801db60929ad540ede972f77`

## Rerun after applied fixes

The production flow was rerun with the bundled Browser against the supported `.co.in` deployment. `https://fundersai.co.in` redirects to `https://www.fundersai.co.in`; `.com` is not part of the supported deployment and is no longer treated as a release blocker.

Render is live on deployment `dep-d9fiesb7uimc73eoq3bg`, still using commit `ea5d98fbecbb3c87801db60929ad540ede972f77`. This was an environment/service redeploy rather than a new code revision.

### Rerun matrix

| Check | Result | Evidence |
| --- | --- | --- |
| Login | Pass | Supplied account reached `/dashboard` in `2.06 s` |
| Deterministic SIP | Pass | `/api/chat` `200`; ₹12,000 invested, ₹809 gain, ₹12,809 estimated value |
| Expense-ratio explanation | Partial | `/api/chat` `200`, `model_status=completed`; backend `35.4 s`, UI observed rendering at about `75 s` |
| Expense-ratio wording | Pass for this response | No `research further` or technical-rating corruption appeared in the exact expense-ratio answer |
| Sanitizer regression probe | Fail | Defining `invest` returned `research further means...`; the global replacement is still active |
| Mutual-fund comparison | Partial | `/api/chat` `200`; comparison completed with partial coverage and low confidence |
| `GET /api/mf/122639` | Pass | `200`; Parag Parikh data and NAV cache hit returned |
| NIFTY price history | Pass | `GET /api/quant/stocks/NIFTY/price-history?days=2200` returned `200` |
| `GET /api/mf/118955` | Fail | `503 {"error":"rate_limit_unavailable"}`; HDFC side of canvas did not load |
| Chat persistence | Pass | Sessions list returned `200`; selecting the newest session after reload restored all messages |
| Sign-out | Fail | Session cleared, but UI stayed on `/dashboard` with `Loading workspace…`; reload redirected to `/auth?next=%2Fdashboard` |
| Browser console | Pass | No warning or error entries captured |

### Production-log findings from the rerun

- SIP completed without model use in `2.37 ms` backend time.
- The general expense-ratio request completed with `model=completed` in `35,403 ms`.
- The comparison completed in `6,763 ms` with `coverage=partial` and no model call.
- Render logged `NAV cache refresh scheme_code=122639`, followed by `NAV cache hit scheme_code=122639`.
- No `nav_api_cache`, `provider_response_cache`, Langfuse, OpenRouter `401`, or Groq fallback warning appeared in the rerun window. This confirms the missing-table errors stopped, but it does not identify which model provider served the completed response.
- Render still logged `event=rate_limit_check_failed path=/api/mf/118955 reason=` and returned `503`.
- Vercel recorded the matching `GET /api/mf/118955 503`; it reported no grouped runtime exception.

### Repository/deployment gap at rerun time

The production redeploy still references the same commit, and the requested code hardening is not present in the repository:

- the sanitizer still globally replaces `buy`, `sell`, and `invest`;
- read-only `quant`, `mf-detail`, and `category-funds` requests still fail closed when the rate-limit backend throws;
- rate-limit exception logging still records only the often-empty `str(exc)`;
- the follow-up `provider_response_cache` RLS/revoke migration is absent;
- sign-out still uses competing client-router redirects;
- SEO metadata, sitemap, robots, structured data, and backend CORS still reference `.com` instead of the supported `.co.in` host.

Remote RLS state could not be proved through the UI test. The schema/cache migrations are now visible to the live application, but the security migration must be tracked in the repository even if equivalent SQL was run manually.

## Local fixes implemented after the rerun

The following changes are now implemented locally and require migration application plus new Vercel/Render deployments before another live Browser verification:

- public read-only rate-limit groups (`quant`, `mf-detail`, `category-funds`, and `data-health`) continue to their route when Upstash throws or is unavailable;
- chat, fund research, cron, and admin mutation groups remain fail-closed;
- rate-limit failures now log the group, exception type, provider HTTP status when available, and `repr` of the exception;
- neutral `invest`, `investment`, `buying`, and `selling` language is preserved while contextual recommendation phrases are rewritten;
- `20260721_harden_provider_response_cache_rls.sql` enables RLS, revokes `public`/`anon`/`authenticated`, and grants CRUD to `service_role`;
- canonical metadata, sitemap, robots, JSON-LD, and backend CORS now use the live `.co.in` hosts, with `https://www.fundersai.co.in` as the canonical destination;
- sign-out now handles Supabase errors and uses `window.location.replace('/auth')` after the session is cleared.

Verification completed:

- full backend suite: `382 passed, 6 skipped`;
- all frontend contract tests: `30 passed`;
- TypeScript: passed;
- focused ESLint: no errors, with two pre-existing custom-font warnings in `app/layout.tsx`;
- Next.js production build: passed;
- `git diff --check`: no whitespace errors in the changed files. The command also encountered the pre-existing inaccessible/deleted `.pytest_temp/test_nippon_factsheet_parser_a0/small-cap.html`, which was not modified.

## Initial run outcome (historical)

The Browser login-to-chat flow completed against production. Authentication, deterministic chat, provider-backed chat, comparison, and persisted history work, but the application is **not release-ready** because:

- `fundersai.com` is a parked GoDaddy domain;
- OpenRouter returns `401` and Groq must recover every model stage;
- two comparison-canvas requests return `503`;
- `nav_api_cache` and `provider_response_cache` are missing in Supabase;
- the general explanation contains corrupted research-language substitutions;
- sign-out remains on `Loading workspace…` until reload.

## Deployment verification

| Deployment | Result |
| --- | --- |
| Vercel `fundersai` | `READY`, deployment `dpl_7sWoREU6meYo8WdWQiLHkmxYjRvX` |
| Render `FundersAI` | `live`, deployment `dep-d9fhofbtqb8s73d4ein0` |
| Git revision | Both deployments reference `ea5d98fbecbb3c87801db60929ad540ede972f77` |

## Domain verification from the initial run

`https://fundersai.com/dashboard` displays a GoDaddy parked-domain page. It is not the deployed FundersAI application.

Vercel reports these production aliases:

- `fundersai.co.in`
- `www.fundersai.co.in`
- `market-mind-eight.vercel.app`

The application test therefore used `https://fundersai.co.in`. The rerun treats `.co.in` as the only supported domain; `.com` is out of scope.

## Final test matrix

| Check | Result | Evidence |
| --- | --- | --- |
| Signed-out dashboard guard | Pass with UX issue | Reloading `/dashboard` redirected to `/auth?next=%2Fdashboard` |
| Login | Pass | Supplied account reached `/dashboard` in about `2.1 s` |
| Deterministic SIP | Pass | HTTP `200`; estimated value ₹232,339 |
| Expense-ratio explanation | Functional but quality failure | HTTP `200`, about `6.5 s`, `model_status=completed` |
| Mutual-fund comparison | Partial pass | HTTP `200`, about `10.3 s`; backend about `6.0 s` |
| Comparison canvas | Partial pass | Opened successfully, but two auxiliary requests returned `503` |
| Reload/history | Pass with extra click | Recent session restored all messages after selection |
| Browser console | Pass | No app-domain warning/error entries |
| Browser network | Fail | Two HTTP `503` responses |
| Vercel chat/session routes | Pass | Session create/read and four chat requests returned `200` |
| Langfuse authentication | Pass in tested window | No Langfuse warning/error appeared during the run |

## Authentication flow

The test account was already authenticated when Browser reached the correct domain, so the run signed out before verifying the guard.

After clicking **Sign out**, the dashboard remained on `Loading workspace…` for more than three seconds. Reloading then correctly redirected to:

```text
https://www.fundersai.co.in/auth?next=%2Fdashboard
```

Login with the supplied account succeeded and returned to the dashboard. The password is not stored in this report.

## Deterministic SIP

Query:

```text
Calculate SIP returns for 1000 monthly for 10 years at 12%.
```

Result:

- Monthly SIP: ₹1,000
- Duration: 120 months
- Expected annual return: 12%
- Total invested: ₹120,000
- Estimated gain: ₹112,339
- Estimated value: ₹232,339

Render recorded `intent=sip_calculator`, `model=not_used`, and HTTP `200`.

## Provider-backed explanation

Query:

```text
Explain mutual fund expense ratio in simple terms.
```

The captured response contained:

```text
HTTP 200
model_status=completed
answer_mode=general_education
coverage_status=not_applicable
```

Render shows OpenRouter returned `401 Unauthorized` on each model stage. Groq succeeded on attempt 2 and produced the completed response. Provider fallback works, but OpenRouter remains unauthorized.

The answer also contains corrupted language, including:

```text
research further in a mutual fund
positive technical rating a variety of assets
```

The research-only sanitizer must not perform broad word replacement inside ordinary educational prose.

## Mutual-fund comparison

Query:

```text
Compare HDFC Flexi Cap and Parag Parikh Flexi Cap.
```

The main response returned:

```text
HTTP 200
model_status=not_used
coverage_status=partial
confidence=Low (0.15)
system_action=COMPARE
scheme IDs=118955, 122639
```

Both funds resolved and the canvas opened. The deterministic backend response took approximately `5.97 s`; total network time was approximately `10.29 s`.

The response correctly disclosed incomplete data: both funds were missing their fund benchmark, and return/risk coverage was only 50%.

## Comparison-canvas failures

Browser captured:

```text
GET /api/mf/122639                                      503
GET /api/quant/stocks/NIFTY/price-history?days=2200    503
```

Render logged `rate_limit_check_failed` for both paths. The production middleware converts a failed rate-limit backend call into `503 rate_limit_unavailable`. This indicates a failing Upstash call or configuration, not an intentional limit rejection.

Render also repeatedly reported missing Supabase tables:

```text
public.nav_api_cache
public.provider_response_cache
```

The associated repository migrations are:

- `backend/migrations/20260717_nav_api_cache.sql`
- `backend/migrations/20260505_indianapi_v1_cache_health.sql`

## History persistence

Vercel recorded:

- `POST /api/chat/sessions` → `200`
- four `POST /api/chat` requests → `200`
- `GET /api/chat/sessions` → `200`
- `GET /api/chat/sessions/{session_id}` → `200`

After reload, the dashboard defaulted to an empty new-chat view. Selecting the latest recent-chat entry restored the SIP, both explanation responses, and comparison. The new owned-message migration is working in production.

The run created one additional chat session and repeated the expense-ratio question once to capture response metadata.

## Console and production logs — initial run

- No app-domain console warning/error entries were captured.
- No Vercel runtime error group appeared during the test window.
- Langfuse emitted no missing-key warning during the test window.
- OpenRouter `401` errors remain active, followed by successful Groq fallback.
- Missing cache-table and rate-limit-backend warnings remain active during comparison.

## Current release assessment

**Status: locally fixed, not yet production-verified.**

Fix in this order:

1. Apply `20260721_harden_provider_response_cache_rls.sql` to the production Supabase project.
2. Commit and deploy the backend and frontend changes.
3. Reduce provider-backed explanation latency or add a deterministic completion boundary.
4. Rerun login, explanation, sanitizer probe, comparison canvas, history restore, sign-out, and production-log checks against the new deployments.
