# Project Overview

FundersAI is a research-first web app for Indian stocks and mutual funds.

## Purpose
- Help users compare and analyze assets using deterministic metrics plus AI summaries.
- Keep provider/API volatility away from the UI by using a Supabase-first data layer.
- Run scheduled ingestion jobs outside request-time paths.

## What Is In Scope
- Research workflows (not order execution/trading).
- Stock and mutual fund comparison in chat + canvas UI.
- Data freshness, source transparency, and partial-result tolerance.
- Admin-only operations dashboard for workflow/data-quality visibility.

## High-Level Stack
- Frontend: Next.js `16.2.4` (App Router), React `19.2.4`, TypeScript, Zustand, Recharts.
- Backend: FastAPI, provider adapters, Supabase repository layer.
- Database: Supabase/PostgreSQL.
- Object storage: Cloudflare R2 for MF raw files and cold archives.
- Automation: GitHub Actions workflows in `.github/workflows/`.

## Repo Layout
- `frontend/`: UI, auth gate, and Next.js API proxy routes.
- `backend/`: FastAPI routes/services/providers/jobs/repositories.
- `docs/`: project operating docs and status memory.
- `prompts/`: system and workflow prompt assets.

## Primary Runtime Paths
1. User query -> `frontend/app/api/chat/route.ts` -> `POST /api/chat` on backend.
2. Structured data routes -> `frontend/app/api/quant/*` proxy -> `GET /api/quant/*` on backend.
3. MF details/search -> frontend server routes query Supabase via `frontend/lib/supabase.ts`.
4. Scheduled updates -> GitHub Actions -> Python jobs under `backend/app/jobs` and `backend/scripts`.
5. Admin ops -> `frontend/app/admin/*` + `/api/admin/*` with role checks against `user_profiles`.

## Ground Rules
- Frontend browser clients should never call backend URLs directly.
- Provider keys stay server-side only.
- Additive contracts only; avoid breaking existing chat/canvas payload consumers.
