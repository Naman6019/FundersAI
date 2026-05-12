# Current State

**Last Updated**: 2026-05-12

## Project Summary
MarketMind is a research-only Indian equities and mutual fund app.

**Tech Stack**: 
- Next.js 16 frontend
- FastAPI backend
- Supabase (PostgreSQL)
- Groq API (LLM)
- YFinance & NSE data
- GitHub Actions cron jobs

## Implemented
- AI chat with asset mode toggle: `Auto`, `Stocks`, `Mutual Funds`.
- Mutual fund comparison canvas with NAV charts, returns, alpha, beta, Sharpe.
- MF sync for NAV, TER, and AUM.
- Stock EOD fetch pipeline using NSE CSVs and Supabase.
- Stock name resolver for broader NSE names and typo tolerance.
- Fixed MF/NIFTY timezone mismatch in risk metrics.
- Fixed MF comparison routing so it does not fall back to stock tickers.
- Chat responses now render deterministic data tables from structured `quant_data`, including unavailable comparison entities and news fallback text.
- `/api/chat` stock comparisons reuse the source-neutral stock comparison payload and tolerate missing risk periods in deterministic tables.
- `/api/chat` synthesis sends compact table facts to Groq while still returning full `quant_data` for frontend canvas rendering.
- Stock-to-stock comparison has a metric-only canvas panel driven by `/api/chat` `system_action` data.
- Stock fundamentals now use a source-neutral provider architecture with `/api/quant/stocks/*` endpoints. CSV fundamentals are no longer required for active app paths.
- Legacy CSV tooling is isolated under `backend/scripts/deprecated/` and is not used by routes or GitHub Actions.
- Stock price-history comparison charts render when `stock_prices_daily` or fallback history exists.
- Next.js `/api/*` proxy pattern is the required frontend/backend boundary.
- GitHub Actions handles scheduled fetch jobs, not Vercel cron.
- Mobile dashboard layout keeps chat mounted behind comparison overlays, and chat state lives in a shared store so query/messages survive canvas-to-chat switches.
- Landing page (`/`) has been redesigned for research-first positioning with proof cards, a live Nifty 50 strip, and prompt handoff into `/dashboard`.
- `IndianAPIProvider` is now restricted to stock profile/fundamental enrichment (`/stock` and `/statement`) with quota guard and usage logging.
- `FinEdgeProvider` remains a fallback only; free keys should not be relied on for fundamentals.
- `sync_corporate_events.py` uses IndianAPI with `INDIANAPI_KEY`/`INDIAN_API_KEY`.
- Stock EOD and historical price backfill use NSE CM-UDiFF bhavcopy zip files and write `stock_prices_daily` with source `nse_bhavcopy`.
- Scheduled stock EOD and historical price jobs stay on NSE CM-UDiFF bhavcopy; IndianAPI historical endpoint is disabled by default.
- Mutual fund NAV/history sync now uses AMFI + MFapi and writes `mutual_fund_nav_history` / `mutual_fund_core_snapshot` for Supabase-first reads.

## In Progress
- Expanding stock coverage beyond the current Nifty-focused list.
- Testing `NIFTY500` vs `NIFTYTOTALMARKET`.
- Tuning `STOCK_INFO_ENRICH_LIMIT` and `STOCK_YFINANCE_FALLBACK_LIMIT`.
- Mutual fund missing data cleanup after stock historical backfill.

## Known Gaps
- IndianAPI fundamentals use `/statement` plus `/stock` only. Disallowed endpoints are feature-flagged off by default.
- Frontend proxy route rate limiting still pending.
- YFinance rate limits often on Render.
- Portfolio overlap is partial because AMFI holdings often returns `Nil`.
- News uses Google News RSS and can be slow.

## Stock Data Architecture
- Source-neutral tables are defined in `backend/migrations/20260501_source_neutral_stock_data.sql`.
- Stock data DTOs live in `backend/app/models/stock_models.py`.
- Supabase stock repository access lives in `backend/app/repositories/stock_repository.py`.
- Provider adapters live in `backend/app/providers/`.
- Ratio calculation lives in `backend/app/services/ratio_engine.py`.
- Provider sync issue logging uses optional `data_quality_issues`; apply `backend/migrations/20260503_add_data_quality_issues.sql` if the table is missing.
- NSE bhavcopy value traded needs `backend/migrations/20260503_add_stock_price_value_traded.sql` on older Supabase schemas.
- GitHub Actions runs 7 workflows: stock universe, daily EOD prices, historical price backfill, fundamentals + ratios (weekly), corporate events, MF sync, and keepalive. See `docs/jobs.md` for the full schedule.
