# Tasks

## Todo
- [x] Add a dedicated `/api/quant` backend endpoint to separate stock lookup from chat synthesis.
- [x] Add rate limiting for frontend proxy routes (`/api/chat`, `/api/cron/sync-mf`).
- [ ] Improve Data Coverage parser status logic to distinguish latest-run failures from historical failures.

## Future Features
- [ ] Advanced charting: add richer stock/fund chart controls, date ranges, indicators, and mobile-friendly comparison views before considering WebGL.
- [ ] Document analysis: support annual report/PDF upload, extraction, summaries, and cited answers.
- [ ] Basic strategy backtesting: simulate simple rules against clean historical EOD data with fees, slippage, benchmark comparison, and result charts.
- [ ] Historical anomaly detection: flag unusual price, volume, valuation, or fundamentals changes with evidence; avoid predictive wording until models are validated.
- [ ] Route-based dashboard split: consider dedicated `/dashboard/research`, `/dashboard/compare`, portfolio, reports, watchlist, and learn pages after the V1 dashboard-first shell is validated.

## FundersAI Product Improvement Roadmap

### 1. Research Scorecard
- [ ] Add a clear scorecard for each stock and mutual fund.
- [ ] Stocks: include valuation, growth, profitability, debt risk, price trend, news sentiment, and data confidence.
- [ ] Mutual funds: include return consistency, risk, expense ratio, AUM health, benchmark outperformance, alpha/beta/Sharpe, and category fit.
- [ ] Keep score explainable with visible reasons; avoid black-box scoring.
- Acceptance Criteria:
  - Scorecard is available in stock and mutual fund analysis views.
  - Every score dimension shows the underlying metric/value and reason.
  - Missing inputs reduce confidence and are labeled, not fabricated.
- Why this matters:
  - Makes analysis easier to trust and compare quickly.

### 2. Data Freshness and Source Badges
- [ ] Show which data sources were used in each answer/analysis.
- [ ] Show last-updated timestamps for price data, fundamentals, mutual fund data, news, and corporate actions.
- [ ] Include confidence states: High, Medium, Low.
- [ ] Clearly label missing, stale, estimated, or fallback-provider metrics.
- Acceptance Criteria:
  - All major metric blocks show source + timestamp badges.
  - Stale/fallback states are visible in chat and canvas.
  - Confidence state is included in deterministic analysis payloads.
- Why this matters:
  - Improves transparency and reduces false confidence.

### 3. Beginner / Advanced Explanation Mode
- [ ] Add a user-facing explanation depth toggle.
- [ ] Beginner mode uses plain-language explanations of financial terms.
- [ ] Advanced mode uses precise metrics and technical terminology.
- [ ] Apply mode across AI summaries, metric explanations, and research canvas descriptions.
- Acceptance Criteria:
  - Mode toggle is persisted per user/session.
  - Same query returns different depth output while keeping the same facts.
  - Glossary-like plain explanations are shown in beginner mode.
- Why this matters:
  - Supports both first-time and experienced users without splitting products.

### 4. Risk Analysis Section
- [ ] Add a dedicated risk section for stock and mutual fund analysis.
- [ ] Stocks: valuation risk, debt risk, margin pressure, sector slowdown, weak earnings, negative news, and data-availability risk.
- [ ] Mutual funds: volatility, high expense ratio, underperformance, concentration, drawdown, fund manager change, and category risk.
- [ ] Keep risk language balanced and non-promotional.
- Acceptance Criteria:
  - Risk section appears in stock and mutual fund analysis flows.
  - Risk bullets are backed by deterministic data points where available.
  - When data is unavailable, show "Not available" with low confidence.
- Why this matters:
  - Prevents one-sided analysis and improves research quality.

### 5. Watchlist
- [ ] Add logged-in user watchlist support for stocks and mutual funds.
- [ ] Allow users to add/remove assets.
- [ ] Design for future alerts, daily summaries, and personalized research history.
- [ ] Document required frontend, backend, and Supabase changes before rollout.
- Acceptance Criteria:
  - Users can create and edit a watchlist from the UI.
  - Watchlist assets are persisted and returned via API.
  - Roadmap includes schema/API/task breakdown for alerts and history follow-ups.
- Why this matters:
  - Creates repeat-user workflows and personalized context.

### 6. Daily FundersAI Brief
- [ ] Add a daily market summary experience.
- [ ] Include market mood, Nifty/Sensex trend, top/weak sectors, important news, watchlist changes, and MF NAV updates.
- [ ] Keep structure beginner-friendly: What happened, why it matters, what to watch next.
- Acceptance Criteria:
  - Daily brief can be generated from deterministic data snapshots.
  - Brief format is consistent and readable on mobile and desktop.
  - Watchlist-aware section is supported when user watchlist exists.
- Why this matters:
  - Gives users a clear daily reason to return.

### 7. Peer and Sector Comparison
- [ ] Add sector and peer comparison for stocks.
- [ ] Compare against sector median or close competitors.
- [ ] Include valuation, profitability, growth, debt, margin, and price performance.
- [ ] Keep future scope for dedicated sector overview pages.
- Acceptance Criteria:
  - Stock analysis can display peer/sector-relative metrics.
  - Comparison highlights over/under-performance vs peer baseline.
  - Sector data model supports future sector overview screens.
- Why this matters:
  - Adds market context beyond standalone stock snapshots.

### 8. Verteal Aesthetic Redesign Tasks
- [x] Global Theming
  - [x] Update `globals.css` to pure black dark mode variables.
  - [x] Update `layout.tsx` to `bg-black` and remove serif font imports.
- [x] Landing Page UI Overhaul
  - [x] Swap `font-serif-display` for crisp sans-serif fonts in `PremiumLandingPage.jsx`.
  - [x] Replace flat borders with `bg-white/[0.02] border-white/10 backdrop-blur-md` (Glassmorphism).
  - [x] Add animated, glowing `<AmbientGlow />` background components.
  - [x] Convert Intelligence and Proof sections into asymmetrical Bento Grids.
  - [x] Update Hero Section text to use metallic gradients.
- [x] Verification
  - [x] Check hover states for inner glows.
  - [x] Verify contrast and readability on deep black.

### 9. Saved Reports and PDF Export
- [ ] Allow users to save stock/fund analysis reports.
- [ ] Add exportable PDF research reports.
- [ ] Include summary, key metrics, charts, risks, news sentiment, data sources, freshness, and disclaimer.
- [ ] Keep future support for shareable research links.
- Acceptance Criteria:
  - User can save and reopen a report snapshot.
  - PDF export matches key on-screen analysis sections.
  - Saved report includes source/freshness/disclaimer metadata.
- Why this matters:
  - Improves research continuity and shareability.

### 10. Suggested Questions and Research Templates
- [ ] Add clickable suggested questions in chat, stock pages, MF pages, and comparison pages.
- [ ] Include prompts like: expensive now, key risks, competitor compare, benchmark compare, SIP research fit.
- [ ] Add templates: Stock Deep Dive, Mutual Fund Deep Dive, Risk Analysis, News Impact Analysis, Long-Term Investor View.
- Acceptance Criteria:
  - Suggested questions are context-aware by page/entity type.
  - Template selection pre-builds deterministic analysis request payloads.
  - Templates do not generate recommendation language.
- Why this matters:
  - Helps users ask better research questions faster.

### 10. SEO Learning Pages
- [ ] Add public educational pages for organic discovery.
- [ ] Include topics: P/E ratio, MF comparison, Alpha vs Beta vs Sharpe, large cap vs flexi cap, reading stock fundamentals.
- [ ] Add future public pages for stocks, mutual funds, and comparisons.
- [ ] Keep all content aligned to research-only positioning.
- Acceptance Criteria:
  - Educational pages are published with consistent disclaimers and citations.
  - SEO pages link to in-app research workflows without advice wording.
  - Content quality checks ensure research-only language.
- Why this matters:
  - Builds top-of-funnel discovery and trust with educational content.

### 11. Scale and System Architecture Upgrades
- [ ] Data Caching Layer: Implement Redis/Memcached to cache heavy calculations (CAGR, Alpha, Beta) at EOD to reduce DB load.
- [ ] Message Queues & Workers: Implement Celery/RabbitMQ/Kafka to process PDF parsing and data ingestion asynchronously and in parallel.
- [ ] Database Read Replicas: Separate read/write queries in PostgreSQL to prevent ingestion pipelines from slowing down user queries.
- [ ] Search Engine: Implement Elasticsearch/Typesense/Algolia for fast, fuzzy searching across a growing universe of stocks and funds.
- [ ] Proper Observability & APM: Integrate Datadog/Sentry for application performance monitoring and real-time alerts.
- [ ] Edge Caching: Utilize Cloudflare/Vercel Edge to cache common API responses physically closer to users.
- Acceptance Criteria:
  - System performance remains stable during data ingestion spikes.
  - Search queries return in under 50ms with typo tolerance.
  - PDF parsing completes in under 30 minutes utilizing parallel workers.
- Why this matters:
  - Ensures the platform remains fast, reliable, and cost-effective as traffic and data volume grows.

## Recommended Release Order

### Phase 1: Trust and Clarity
1. Data Freshness and Source Badges
2. Risk Analysis Section
3. Beginner / Advanced Explanation Mode
4. Suggested Questions and Research Templates

### Phase 2: Differentiation
5. Research Scorecard
6. Peer and Sector Comparison

### Phase 3: Retention
7. Watchlist
8. Daily FundersAI Brief
9. Saved Reports and PDF Export

### Phase 4: Growth
10. SEO Learning Pages

## Implementation Notes
- Do not make FundersAI look like a stock tips or recommendation platform.
- Keep the product positioning as research-only.
- Every AI-generated insight should be backed by deterministic data where possible.
- Add disclaimers where financial interpretation is shown.
- Prefer incremental implementation behind feature flags where possible.
- Each feature should eventually include frontend, backend, database, API, and testing tasks.
- Do not break the current deployed app.
- Do not modify production environment variables.
- Do not make database-destructive changes.

## In Progress
- [ ] Expanding stock coverage beyond the current Nifty-focused list.
- [ ] Testing `NIFTY500` vs `NIFTYTOTALMARKET`.
- [ ] Tuning `STOCK_INFO_ENRICH_LIMIT` and `STOCK_YFINANCE_FALLBACK_LIMIT`.
- [ ] Fill mutual fund missing data gaps beyond AUM/TER/holdings for PPFAS, ICICI, HDFC, SBI (benchmark/risk/ratios).
- [ ] Reduce historical `mf_raw_documents` + `mf_parse_review_queue` backlog (`needs_review` and failed rows).

## Done
- [x] Admin dashboard Phase 1 at `/admin` with server-side role enforcement (`user_profiles.role=admin`).
- [x] Added admin APIs: session, overview, users, AI usage, data coverage, NAV sync, resolver debug.
- [x] Added `/dashboard/admin` compatibility redirect to `/admin`.
- [x] Added R2-first MF raw document ingestion path and optional SBI portfolio URL dispatch input.
- [x] Made April 2026 AMC holdings parsing production-ready for HDFC, SBI, PPFAS, and ICICI with golden fixture tests and live clean reparses.
- [x] Added MF raw migration and MF storage compaction workflows.
- [x] Added Data Coverage "Needs Review Entries" section for parser triage visibility.
- [x] Added admin Data Coverage actions for parser triage: reparse, resolve, and skip.
- [x] Dashboard-first onboarding flow.
  - `/dashboard` opens Overview first.
  - Overview CTAs hand off to existing AI Research/chat/canvas state.
  - No dashboard route split in V1.
- [x] Added Google/email auth callback at `/auth/callback`.
- [x] Added Razorpay Standard Checkout order creation and signature verification routes.
- [x] Quota-aware fundamentals cadence: monthly NIFTY500, weekly watched stocks, and on-demand compared symbols.
- [x] AI chat with asset mode toggle: `Auto`, `Stocks`, `Mutual Funds`.
- [x] Mutual fund comparison canvas with NAV charts, returns, alpha, beta, Sharpe.
- [x] MF sync for NAV, TER, and AUM.
- [x] Stock EOD fetch pipeline using NSE CSVs and Supabase.
- [x] Stock name resolver for broader NSE names and typo tolerance.
- [x] Fixed MF/NIFTY timezone mismatch in risk metrics.
- [x] Fixed MF comparison routing so it does not fall back to stock tickers.
- [x] Added deterministic `/api/chat` response tables with missing-entity notes, news fallback text, and safer research wording.
- [x] Fixed `/api/chat` stock comparison table crash when risk period data is missing.
- [x] Added metric-only stock-to-stock comparison canvas.
- [x] Added legacy CSV import foundation and premium fundamental comparison charts.
- [x] Replaced active CSV dependency with source-neutral stock provider architecture.
- [x] Moved legacy CSV tooling under `backend/scripts/deprecated/`.
- [x] Added stock price-history comparison charts for source-neutral quant data.
- [x] Next.js `/api/*` proxy pattern enforced as frontend/backend boundary.
- [x] GitHub Actions handles scheduled fetch jobs, not Vercel cron.
- [x] Fixed mobile dashboard clipping by using a single active chat/comparison workspace and compact comparison chart spacing.
- [x] Fixed mobile chat positioning so the header stays visible and the input stays at the bottom.
- [x] Fixed mobile comparison canvas state loss by keeping chat mounted behind the canvas overlay and moving chat state into a shared store.
- [x] Fixed landing page wide-screen right-side void by removing fixed hero width caps and using full-width sections.
- [x] Redesigned landing page (`/`) for AI research positioning with proof cards, live Nifty 50 strip, and direct prompt handoff to `/dashboard`.
- [x] Added internal stock DTOs and a Supabase repository layer for source-neutral stock data.
- [x] Added NSE CM-UDiFF bhavcopy daily price sync and manual historical backfill into `stock_prices_daily`.

## Blocked
- None currently.

## Known Issues
- YFinance rate limits often on Render deployments.
- [ ] Portfolio overlap is partial for schemes/months not yet covered by AMC disclosure parser outputs.
- News uses Google News RSS and can be slow.

##Fund manager Past positions and performance
