# Deployment

## Current Topology
- Frontend: Vercel project rooted at `frontend/`
- Backend: Render web service rooted at `backend/`
- Database: Supabase
- Object Storage: Cloudflare R2 (raw docs + cold archives)
- Scheduler: GitHub Actions workflows in `.github/workflows/`

## Frontend (Vercel)
- Runtime: Next.js App Router
- Browser-safe backend boundary: `frontend/app/api/*`
- Required envs:
  - `NEXT_PUBLIC_API_URL`
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
  - `CRON_SECRET` (protects `/api/cron/sync-mf`)
  - `SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_KEY` (server routes needing admin Supabase access)
  - `MF_INTERNAL_ADMIN_KEY` (server-to-backend admin resolver debug proxy)
  - `RATE_LIMIT_ENABLED=true`
  - `UPSTASH_REDIS_REST_URL`
  - `UPSTASH_REDIS_REST_TOKEN`

## Backend (Render)
- Local dev entry: `uvicorn app.main:app --reload --port 8000`
- Health: `GET /health`
- Required rate-limit envs in production:
  - `RATE_LIMIT_ENABLED=true`
  - `UPSTASH_REDIS_REST_URL`
  - `UPSTASH_REDIS_REST_TOKEN`
- Internal admin endpoints:
  - `GET /api/admin/ops-overview`
  - `GET /api/admin/mf-resolver-debug`
  - Require `X-Admin-Key` = `MF_INTERNAL_ADMIN_KEY`
- Note: `backend/render.yaml` currently references `uvicorn api.index:app`, but repo code uses `app.main:app`. Align before relying on `render.yaml`.

## Workflow Secrets (GitHub Actions)
- Base:
  - `SUPABASE_URL`
  - `SUPABASE_KEY`
- R2:
  - `R2_ENDPOINT`
  - `R2_ACCESS_KEY_ID`
  - `R2_SECRET_ACCESS_KEY`
  - `R2_RAW_BUCKET`
  - `R2_COLD_BUCKET`
- Providers:
  - `FINEDGE_API_KEY`
  - `INDIAN_API_KEY` (only for explicitly enabled fallback/research paths)
- Optional MF source URL overrides:
  - `MF_HDFC_FACTSHEET_PAGE_URL`
  - `MF_HDFC_PORTFOLIO_PAGE_URL`
  - `MF_SBI_FACTSHEET_PAGE_URL`
  - `MF_SBI_PORTFOLIO_PAGE_URL`
  - `MF_HDFC_FACTSHEET_DOCUMENT_URLS`
  - `MF_HDFC_PORTFOLIO_DOCUMENT_URLS`
  - `MF_SBI_FACTSHEET_DOCUMENT_URLS`
  - `MF_SBI_PORTFOLIO_DOCUMENT_URLS`

## Admin Access Provisioning
Add/update a row in `user_profiles`:
- `user_id` = `auth.users.id` (UUID, not email or text label)
- `role` = `admin`
- `tier` = `pro` (optional but recommended for admin accounts)

## Operational Checks
- Verify frontend proxy routes can reach backend URL.
- Verify backend `/health` and `/api/chat`.
- Verify rate limits on `/api/chat`; production protected routes require Upstash Redis env vars.
- Verify latest workflow run status and row-write counts.
- Verify R2 credentials before MF disclosure sync/compaction jobs.
- Verify `/admin`:
  - unauthenticated -> redirect to `/auth`
  - non-admin -> access denied
  - admin -> dashboard loads
