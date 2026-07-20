# Deployment

## Current Topology
- Frontend: Vercel project rooted at `frontend/`
- Backend: Render web service rooted at `backend/`
- Database: Supabase
- Object Storage: Cloudflare R2 (raw docs + cold archives)
- Scheduler: GitHub Actions workflows in `.github/workflows/`

This remains the production topology. Prefect and GCP artifacts are implemented as deployment proof, but they are not current production claims.

## Reproducible Deployment Proof

The repository now contains:

- `backend/Dockerfile` for the FastAPI service;
- `backend/Dockerfile.worker` for the Prefect evidence job;
- `deploy/gcp/deploy.ps1` for Artifact Registry images, a private Cloud Run service, and a Cloud Run Job;
- `deploy/gcp/configure-monitoring.ps1` for log-based failure/fallback counters and alert policies.

These files are reproducible configuration, not evidence of a successful deployment. A production claim requires image digests, the Cloud Run revision/job execution, health output, an evaluation result, and a triggered test alert.

Prerequisites are Docker with a running daemon, Google Cloud CLI, billing, the referenced Secret Manager secrets, and a Monitoring notification channel. From the repository root:

```powershell
.\deploy\gcp\deploy.ps1 -ProjectId <project-id> -Tag <git-sha>
.\deploy\gcp\configure-monitoring.ps1 -ProjectId <project-id> -NotificationChannel <channel-resource-name>
```

Do not migrate business data to Cloud SQL or raw documents to GCS solely to match a cloud diagram. Revisit storage only when cost, latency, compliance, or operational evidence justifies the migration.

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
  - `RAZORPAY_KEY_ID`
  - `RAZORPAY_KEY_SECRET`
  - `NEXT_PUBLIC_RAZORPAY_KEY_ID`
  - `RAZORPAY_WEBHOOK_SECRET`
  - `RAZORPAY_PLAN_PRO_MONTHLY_ID`
  - `RAZORPAY_PLAN_ULTRA_MONTHLY_ID`

## Auth Provider Configuration
- Supabase Site URL should be the production app origin, for example `https://www.fundersai.co.in`.
- Supabase Redirect URLs should include:
  - `http://localhost:3000/auth/callback`
  - `https://www.fundersai.co.in/auth/callback`
  - `https://fundersai.co.in/auth/callback`
- Google OAuth authorized redirect URI should use the Supabase provider callback URL:
  - `https://<supabase-project-ref>.supabase.co/auth/v1/callback`
- Google OAuth client id and client secret are configured in Supabase Auth provider settings, not in frontend code.

## Razorpay Configuration
- Use Razorpay Dashboard API keys:
  - `RAZORPAY_KEY_ID`: server routes
  - `RAZORPAY_KEY_SECRET`: server routes only
  - `NEXT_PUBLIC_RAZORPAY_KEY_ID`: browser Checkout key id only
- Create monthly subscription plans in Razorpay first, then set:
  - `RAZORPAY_PLAN_PRO_MONTHLY_ID`
  - `RAZORPAY_PLAN_ULTRA_MONTHLY_ID`
- Webhook endpoint:
  - `https://www.fundersai.co.in/api/billing/webhook`
- Webhook secret goes in `RAZORPAY_WEBHOOK_SECRET`.
- Never expose `RAZORPAY_KEY_SECRET` or `RAZORPAY_WEBHOOK_SECRET` in `NEXT_PUBLIC_*` env vars.

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
- `backend/render.yaml` starts `uvicorn app.main:app`.

### NAV Cache Cutover
- Apply `backend/migrations/20260717_nav_api_cache.sql` before deploying the NAV-cache runtime.
- The legacy-table drop is intentionally outside `backend/migrations/` at `backend/manual_migrations/drop_mutual_fund_nav_history_after_readiness.sql`.
- Run the manual drop only after the archive workflow and `check_nav_cache_drop_readiness.py` report `drop_ready=true`; the SQL also requires an explicit session acknowledgement.

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
- Verify `/auth/callback` works for Google sign-in and email verification.
- Verify `/api/create-order` returns a Razorpay order when Razorpay env vars are set.
- Verify `/api/verify-payment` rejects bad signatures.
