# Per-fund and per-AMC pages: catalog, metrics, and NAV coverage

**Date:** 2026-09-03
**Status:** Design approved, not implemented
**Scope:** `backend/app/services`, `backend/app/jobs`, `backend/migrations`, `frontend/app/mutual-funds`, `frontend/lib/mf`, `frontend/app/sitemap.ts`, `.github/workflows/mf-sync.yml`

**Decomposition:** this design covers two sequential sub-projects. Steps 1–4 of §7 (the data project) are the first implementation plan. Steps 5–7 (the page project) are a second plan, written only after step 3 has measured actual post-backfill coverage — the prerender count and several §6 decisions depend on numbers that do not exist yet.

---

## 1. Motivation

The request was to build Groww-style per-fund pages (`groww.in/mutual-funds/parag-parikh-long-term-value-fund-direct-growth`) and AMC pages (`groww.in/mutual-funds/amc/bandhan-mutual-funds`).

Those routes already exist:

| Groww | FundersAI today |
| --- | --- |
| `/mutual-funds/<fund>-direct-growth` | `frontend/app/mutual-funds/[amcSlug]/[fundSlug]/page.tsx` |
| `/mutual-funds/amc` | `frontend/app/mutual-funds/page.tsx` ("Browse by AMC" grid) |
| `/mutual-funds/amc/<amc>` | `frontend/app/mutual-funds/[amcSlug]/page.tsx` |

All three read `frontend/lib/fund-registry.ts`, a hand-maintained TypeScript file holding **31 funds and 15 AMCs**. The fund page renders no NAV, no returns, no expense ratio, no holdings and no fund manager — it is a semantic SEO shell with a "run this in the workspace" call to action where Groww puts the numbers.

The gap is therefore depth and coverage, not the existence of routes.

## 2. Measured starting state

All figures measured against the production Supabase project `luzwcyholmyxzcrspzyr` on 2026-09-03.

### 2.1 `mutual_fund_core_snapshot`

14,457 scheme rows across 57 distinct `amc_name` values.

| Field | Non-null rows |
| --- | --- |
| `nav` | 14,456 |
| `nav_date` within 10 days | 2,404 |
| `return_1y` | 2,976 |
| `return_3y` | 2,554 |
| `return_5y` | 1,967 |
| `benchmark` | 3,208 |
| `risk_level` | 2,832 |
| `aum` | 2,067 |
| `expense_ratio` | 1,449 |
| `sharpe_ratio` | 1,170 |
| `fund_manager` | 951 |

`plan_type` and `option_type` are NULL on 12,386 of 14,457 rows, and inconsistent where present (`Growth`, `Growth Option`, `GROWTH`, `GROWTH OPTION`, `Direct Growth`, `Cumulative`). `category` holds 111 distinct values, not a clean SEBI list.

### 2.2 `mutual_fund_nav_history`

3,105,259 rows across 14,401 schemes, `nav_date` spanning 2006-04-01 to 2026-07-19.

The breadth is misleading. Averaged out this is ~215 rows per scheme.

| Check | Schemes |
| --- | --- |
| Present at all | 14,401 |
| >= 250 observations spanning >= 1 year | 2,101 |
| Last NAV row within 60 days | 2,104 |
| Last NAV row within 15 days | **0** |
| **Both >= 1y depth and fresh within 60 days** | **521** |

Two defects stack: the table is stale everywhere (nothing newer than 2026-07-19, roughly six weeks behind the snapshot's 2026-09-02), and the schemes that are deep are largely not the schemes that are fresh.

### 2.3 The 521 are the wrong funds

AMCs in the gated set, by count: Bandhan 72, Baroda BNP Paribas 51, Axis 46, Aditya Birla Sun Life 38, DSP 32, ICICI Prudential 23, HSBC 22, Canara Robeco 22, Bajaj Finserv 18, Franklin Templeton 14, UTI 14, Nippon India 13, Bank of India 12, Tata 12, PGIM India 12.

HDFC, SBI, PPFAS, Mirae Asset, Kotak and quant are absent from the top 15. PPFAS — the AMC in the original request — holds 28 schemes in the snapshot, 6 with a `return_1y`.

Sampling the 2,430 schemes whose snapshot `nav_date` is within 15 days returns mostly ETFs, overnight and credit-risk debt funds, weekly-IDCW share classes, and segregated portfolios. These are not the instruments retail search traffic looks for.

### 2.4 Related tables

- `mutual_fund_holdings`: 1,241 distinct schemes. Columns include `as_of_date`, `source`, `security_name`, `isin`, `sector`, `weight_pct`.
- `mutual_fund_sectors`: 1,031 distinct schemes, with `sector`, `weight_pct`, `stock_count`, `source`.

## 3. Root cause of the NAV coverage ceiling

Nothing is broken. The cron fires, and `archive_mf_nav_history.py` does not prune rows after archiving to R2 (verified: the job contains no delete or retention logic). The ceiling is structural.

`backend/app/jobs/refresh_mf_metric_inputs.py` is the only job that deepens `mutual_fund_nav_history`. Its target list comes from `prioritized_metric_targets`, which wraps `supported_metric_targets` in `backend/app/services/mf_metric_target_service.py:40`. That function requires, per scheme:

- an `mf_factsheet_candidates` row with `mapping_status = 'mapped'`
- `mapping_confidence >= 90`
- `promotion_status != 'rejected'`
- and the AMC's source entry in `backend/app/mf_ingestion/sources/registry.py` having `runtime_enabled = True` (17 of the registered sources)

Measured result: **881 eligible schemes across 14 AMCs**, out of 1,994 candidate rows (1,445 mapped).

`.github/workflows/mf-sync.yml` then runs the job as `--limit 100`, on `cron: '30 17 * * 1-5'` — weekdays only. 881 targets at 100 per run is a ~9 weekday full cycle, against `MF_METRIC_HISTORY_MAX_AGE_DAYS = 14`. The pipeline is operating at the boundary of its own freshness SLA, which explains both the zero-schemes-fresh-within-15-days result and the 521 overlap.

**The defect is a conflation of two different evidence standards.**

- "This fund's portfolio held 4.2% HDFC Bank as of July 2026" requires an official AMC document. The factsheet gate is correct and must stay.
- "This fund returned 14.1% CAGR over three years" requires NAV, which AMFI publishes freely for all 14,457 schemes. The factsheet gate buys nothing here and costs roughly 94% of the available coverage.

## 4. Decisions taken

| Decision | Choice | Rationale |
| --- | --- | --- |
| Coverage model | Quality-gated catalog | Publishing all 14,457 would ship thousands of thin pages with stale NAV, conflicting with the research-only evidence invariant |
| Render mode | ISR with partial prerender | Top ~300 prerendered at build, rest on demand, all revalidating daily. Fast builds, static HTML for crawlers, freshness bounded at 24h |
| URL shape | Keep nested `/mutual-funds/<amc>/<fund>` | 31 URLs are already indexed; breadcrumbs and the AMC parent already exist; hierarchy beats a flat namespace for crawlers |
| Share classes | One page per Direct + Growth scheme | Regular and IDCW variants would be near-duplicate content, and `plan_type` is NULL on 86% of rows so variant inference is guesswork |
| Sequencing | NAV backfill before page work | 521 publishable schemes skewed to Bandhan and Baroda BNP Paribas will not rank; the pipeline is the bottleneck, not the template |
| Page sections | All four (NAV/returns, risk, holdings, facts/peers) | Approved in full |
| Separate `/mutual-funds/amc` route | No | Duplicate-content split against the existing hub; contrary to recent commits bounding generated routes |

## 5. Architecture

### 5.1 Decouple NAV history from factsheet evidence

Add a **second, independent** target selector. `supported_metric_targets` keeps its strict contract unchanged and keeps serving the factsheet-evidenced surfaces; nothing that depends on it is touched.

New in `backend/app/services/mf_metric_target_service.py`:

```python
def catalog_nav_targets(client) -> list[dict]:
    """Schemes eligible for a public fund page, independent of factsheet mapping."""
```

Selection criteria:

- present in `mutual_fund_core_snapshot`
- `amc_name` non-null and not `'Unknown'` (78 rows are NULL, 10 are `'Unknown'`)
- resolves to a Direct + Growth share class via the normalizer in §5.3
- excludes segregated portfolios, IDCW and dividend share classes

Naive name matching (`scheme_name ILIKE '%direct%'` and a growth signal, minus IDCW/dividend/segregated/unknown-AMC) sizes this at **803 schemes**. 4,869 rows carry "Direct" in the name but most do not spell out the option, so a real normalizer should reach roughly **1,000–1,500 schemes spread across all 57 AMCs** rather than 14.

**Open item:** the mfapi request budget is unmeasured. The backfill's runtime and the sustainable steady-state limit are unestimated until the first dispatch run measures them. Do not hardcode a limit before that measurement.

**Cache interaction:** `nav_api_cache` drives freshness ranking in `prioritized_metric_targets`. The catalog selector needs its own ordering over the same cache rows, or the two jobs will thrash against each other re-fetching the same schemes. Prefer a distinct ordering function over mutating the shared one.

### 5.2 Migration: two new tables

New file `backend/migrations/20260903_add_mf_page_catalog.sql`, following the existing convention (explicit `BEGIN`/`COMMIT`, `IF NOT EXISTS`, RLS enabled, `REVOKE ALL ... FROM anon, authenticated`).

Both tables are read server-side through the service-role client in `frontend/lib/supabase.ts`. Neither needs Data API exposure, so `anon` and `authenticated` are revoked outright.

#### `mf_page_catalog`

```sql
CREATE TABLE IF NOT EXISTS public.mf_page_catalog (
  scheme_code        TEXT PRIMARY KEY,
  amc_slug           TEXT NOT NULL,
  fund_slug          TEXT NOT NULL,
  scheme_name        TEXT NOT NULL,
  display_name       TEXT NOT NULL,
  amc_name           TEXT NOT NULL,
  category           TEXT,
  category_slug      TEXT,
  benchmark          TEXT,
  is_published       BOOLEAN NOT NULL DEFAULT false,
  is_grandfathered   BOOLEAN NOT NULL DEFAULT false,
  gate_reasons       JSONB   NOT NULL DEFAULT '[]'::jsonb,
  prerender_rank     INTEGER,
  first_published_at TIMESTAMPTZ,
  last_evaluated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (amc_slug, fund_slug)
);

CREATE INDEX IF NOT EXISTS mf_page_catalog_published_rank_idx
  ON public.mf_page_catalog (prerender_rank ASC) WHERE is_published;
CREATE INDEX IF NOT EXISTS mf_page_catalog_amc_idx
  ON public.mf_page_catalog (amc_slug) WHERE is_published;
```

Three properties that matter:

**Rejected candidates get rows.** `is_published = false` with populated `gate_reasons` (e.g. `["nav_stale", "history_lt_1y"]`) makes the gate auditable by query. "Why is Parag Parikh Flexi Cap not live?" must be answerable with a `SELECT`, not a job re-run. It also gives `/admin/data-coverage` a backlog view at no extra cost.

**Slugs freeze on first publish.** Once `first_published_at` is set, the nightly job must never re-slug that row. If the normalizer would now produce a different slug — because the AMC renamed the scheme, which happens — the job writes a conflict record for human review rather than rewriting an indexed URL. This is the most dangerous failure mode in the design: a silent re-slug is an unannounced 404 on a page that was ranking.

**Collisions resolve by age.** On a `(amc_slug, fund_slug)` clash, the row with the older `first_published_at` keeps the slug and the newcomer takes a `-<scheme_code>` suffix. Deterministic and stable across re-runs, which alphabetical or insertion ordering is not.

#### `mf_scheme_computed_metrics`

Deliberately a separate table rather than new columns on `mutual_fund_core_snapshot`. The snapshot holds provider-supplied values; these are FundersAI-computed from AMFI NAV. Merging them makes it impossible for the page to state where a number came from, which the research-only invariant requires it to state.

```sql
CREATE TABLE IF NOT EXISTS public.mf_scheme_computed_metrics (
  scheme_code       TEXT PRIMARY KEY,
  nav               NUMERIC,
  nav_date          DATE,
  return_1m         NUMERIC,
  return_3m         NUMERIC,
  return_6m         NUMERIC,
  cagr_1y           NUMERIC,
  cagr_3y           NUMERIC,
  cagr_5y           NUMERIC,
  volatility_1y     NUMERIC,
  max_drawdown_1y   NUMERIC,
  max_drawdown_3y   NUMERIC,
  sharpe_1y         NUMERIC,
  sharpe_3y         NUMERIC,
  alpha_1y          NUMERIC,
  beta_1y           NUMERIC,
  benchmark_code    TEXT,
  history_start     DATE,
  history_end       DATE,
  observation_count INTEGER,
  risk_free_rate    NUMERIC,
  method_version    TEXT NOT NULL,
  computed_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

`risk_free_rate` and `method_version` are stored per row so any published Sharpe figure remains reproducible after a formula change. `/methodology/formulas` already promises deterministic reproducibility; without these two columns that promise cannot be kept.

Returns under one year are absolute; one year and above are annualized. The column names encode this (`return_*` vs `cagr_*`) so a caller cannot mix them up.

**Every metric is NULL unless its window is fully covered by the NAV series.** A 3Y CAGR computed from 2.5 years of history is a fabricated number. The page renders "insufficient history" rather than a plausible-looking figure.

### 5.3 Slug normalizer

New module, `backend/app/services/mf_slug_service.py`, pure functions, no I/O — so it is directly unit-testable.

Responsibilities:

- `amc_slug(amc_name)` — canonical AMC slug. Must handle lowercase `quant Mutual Fund`, legacy names (`Reliance Mutual Fund` vs `Nippon India Mutual Fund`, `IDFC` vs `Bandhan`, `BOI AXA` vs `Bank of India`, `DHFL Pramerica` vs `PGIM India`, `Baroda Pioneer` vs `Baroda BNP Paribas`), and reject NULL / `'Unknown'`. Legacy names map to the current entity's slug so that history does not fragment the AMC page.
- `fund_slug(scheme_name)` — strip plan and option suffixes, punctuation, and segregated-portfolio parentheticals; produce a stable kebab-case slug.
- `display_name(scheme_name)` — the H1 form, with plan/option noise removed but the fund's identity intact.
- `share_class(scheme_name, plan_type, option_type)` — returns Direct/Regular and Growth/IDCW, using the name as primary evidence and the columns as a weak secondary signal (they are NULL on 86% of rows).
- `sebi_category(category)` — collapse the 111 observed values onto the `CATEGORY_LIST` used elsewhere; unmapped values yield NULL and a gate reason.

### 5.4 Jobs

#### `backend/app/jobs/build_mf_page_catalog.py` (nightly)

1. Read `catalog_nav_targets`.
2. Normalize each to slugs, display name, share class, SEBI category.
3. Evaluate the publish gate, accumulating `gate_reasons`:
   - resolvable AMC slug and fund slug
   - Direct + Growth share class
   - SEBI category resolved
   - NAV history depth >= 1 year with >= 250 observations
   - NAV history recency: last row within `CATALOG_NAV_MAX_AGE_DAYS` (default 7)
4. Upsert catalog rows. Respect the freeze rule from §5.2 — never rewrite `amc_slug`/`fund_slug` on a row with a non-null `first_published_at`; record a conflict instead.
5. Recompute `prerender_rank`, ordered by AUM where known, then by NAV-history depth.
6. Emit a `ProviderRun` telemetry row, matching the sibling jobs.

#### `backend/app/jobs/backfill_catalog_nav_history.py` (`workflow_dispatch` only)

One-time, resumable, chunked. Walks `catalog_nav_targets` filling `mutual_fund_nav_history` to full depth at a rate mfapi tolerates. Manual dispatch only, matching the established convention that promotion and bulk-mutation jobs are never scheduled. The first run establishes the mfapi rate ceiling that §5.1 leaves open.

#### `backend/app/jobs/refresh_catalog_metrics.py` (nightly)

Reads published catalog rows, pulls NAV history, computes, writes `mf_scheme_computed_metrics`, records a `ProviderRun`. Added to `mf-sync.yml` after the NAV refresh step.

The math extends `compute_nav_metrics` in `backend/app/services/mf_metrics_service.py` rather than starting fresh.

#### Workflow change

`.github/workflows/mf-sync.yml` gains a catalog NAV refresh step, separate from the existing factsheet-gated `refresh_mf_metric_inputs --limit 100`, with its own larger limit and a 7-day window. The existing step is unchanged.

### 5.5 Duplicate CAGR implementation

`frontend/lib/mf/returns.ts` contains an independent `calculateCAGR` and `calculateRiskMetrics`, separate from the backend's. After this work both would feed the same page, and they can disagree.

The backend becomes authoritative; the frontend copy is pointed at `mf_scheme_computed_metrics`. This touches the live workspace path, so it is called out as an explicit spec item and must not be done as a drive-by refactor during page work.

### 5.6 Alpha and beta will mostly be NULL

`sync_nifty_benchmark` supplies NIFTY history. Only 3,208 schemes carry a benchmark string at all, and it must resolve to an index we hold history for, across the full window. In practice v1 computes alpha and beta for NIFTY-benchmarked equity funds and NULLs the rest. A blank cell is correct; a beta against the wrong index is not.

## 6. Page layer

### 6.1 Data access

New `frontend/lib/mf/catalog.ts`, server-only, reading through the service-role client in `frontend/lib/supabase.ts` — **not** through `/api/*`. The BFF exists to put auth and rate limiting in front of browser calls; these are server components rendering at build or ISR time, and an HTTP hop to our own backend would add a failure mode for no benefit.

```
getPublishedFund(amcSlug, fundSlug)  -> catalog + computed_metrics + snapshot facts
getPublishedFundsByAmc(amcSlug)
getPrerenderTargets(limit)           -> top N by prerender_rank
getPublishedAmcs()                   -> slug + published count
```

### 6.2 Route changes

`frontend/app/mutual-funds/[amcSlug]/[fundSlug]/page.tsx` replaces `getFundBySlug` with the catalog lookup and adds:

```ts
export const dynamicParams = true;
export const revalidate = 86400;
// generateStaticParams -> top ~300 by prerender_rank
```

### 6.3 The 31 existing pages are grandfathered permanently

`FUND_REGISTRY`'s 31 funds have live, indexed URLs. The migration seeds the catalog from them with their **current** `amc_slug` and `fund_slug`, `is_grandfathered = true`, and a backdated `first_published_at`, so the freeze rule protects them from the first migration onward.

Several will fail the gate — PPFAS holds 28 schemes with 6 carrying a `return_1y`, so the fund from the original request is a likely casualty.

**A grandfathered row is never unpublished.** It keeps `is_published = true`, records its `gate_reasons` for visibility, and renders with whatever data exists plus honest empty states. Removing a page that is currently indexed is strictly worse than serving a thin one.

### 6.4 Page sections

Each renders independently and conditionally.

| Section | Source | Renders when |
| --- | --- | --- |
| NAV chart + returns table | `computed_metrics` + downsampled NAV series | Any window covered |
| Risk metrics | `computed_metrics` | Per-metric; NULL renders "insufficient history" |
| Holdings + sectors | `mutual_fund_holdings` / `mutual_fund_sectors`, citing `as_of_date` and `source` | Rows exist (~1,241 schemes) |
| Fund facts + peers | Snapshot fields, catalog peers, `/compare/<pair>` links | Always; NULL reads "not disclosed in our sources" |

The NAV series is passed as props to a client chart component, downsampled to ~250 points. It is **not** fetched client-side — a crawler must see the numbers in the HTML for any of this to be worth building.

Every figure carries its as-of date. A page whose `nav_date` is older than `CATALOG_NAV_MAX_AGE_DAYS` renders a visible staleness notice rather than presenting the number as current.

The two thresholds are the same constant but serve different roles, and both are needed. The gate decides whether a page may be *published* at the nightly catalog run; the banner catches a page whose data *drifted* past the threshold between runs. A page that goes stale is never unpublished — it keeps its URL and says plainly that its NAV is out of date.

### 6.5 AMC pages

`AMC_REGISTRY` demotes to **editorial metadata only** — `shortName` and the hand-written `description`. It stops deciding which funds exist; counts and fund lists come from the catalog. The ~40 AMCs with no editorial copy get a neutral generated description.

No separate `/mutual-funds/amc` route. `/mutual-funds` already carries the AMC grid, and a second URL with the same content is a duplicate-content split — contrary to the recent commits pinning hosts and bounding generated routes.

### 6.6 Sitemap

`frontend/app/sitemap.ts` becomes async and catalog-driven for sections 3c (AMC pages) and 3d (fund pages). At 1,000–1,500 URLs a single file stays well inside the 50,000 limit, so no sitemap-index split is needed yet.

The pinned `RELEASE_DATE` for `lastmod` stays. The file's own comment explains the reasoning, and the alternative — `computed_at` — would churn every URL's `lastmod` nightly on a metric recompute that changed nothing a reader would notice. Revisit when per-fund content genuinely changes.

`frontend/tests/sitemapValidation.test.mjs:29-30` asserts the sitemap source matches `/FUND_REGISTRY/` and `/AMC_REGISTRY/`. Making the sitemap catalog-driven breaks those two assertions by design. **Rewrite them to pin the catalog query; do not delete them** — the sitemap must keep having a guard.

### 6.7 Structured data

`FundJsonLd` in `frontend/components/seo/JsonLd.tsx` widens to carry real metrics, emitting only fields we actually hold. No `AggregateRating` and no review markup — we have no ratings, and inventing them is exactly the class of claim the project forbids.

### 6.8 Failure handling

Prerendered pages are unaffected by Supabase outages: ISR keeps serving the last good HTML while revalidation fails in the background.

The non-obvious case is Supabase being unavailable during on-demand generation of a page that was not prerendered. `notFound()` would be wrong — Next would cache a 404 for a fund that exists. The lookup must distinguish:

- **definitively absent from catalog** -> `notFound()`, cached, renders `frontend/app/not-found.tsx`
- **lookup failed** -> throw, uncached 500, a retry succeeds

Getting this backwards silently deindexes real pages.

## 7. Build order

1. Migration — both tables, RLS on, `anon`/`authenticated` revoked, grandfather seed for the 31
2. `mf_slug_service.py` + `catalog_nav_targets` + `build_mf_page_catalog.py`
3. `backfill_catalog_nav_history.py` — dispatch once, measure the mfapi ceiling
4. `refresh_catalog_metrics.py`, wired into `mf-sync.yml`
5. Page layer: `catalog.ts`, route changes, four sections, AMC pages
6. Sitemap, JSON-LD, and the `sitemapValidation` test rewrite
7. Frontend/backend CAGR consolidation (§5.5)

Steps 1–4 are the data project; step 5 onward only becomes worthwhile once step 3 has actually raised coverage.

## 8. Testing

**Backend (`pytest`)** carries the load:

- slug normalizer: determinism, legacy-AMC mapping, collision tiebreak, freeze enforcement (a renamed scheme must produce a conflict, not a rewrite)
- gate evaluation: correct `gate_reasons` for each failure mode
- metric windows: a scheme with 2.5 years of history yields NULL `cagr_3y`, not an extrapolation
- golden values: one known fund's `cagr_1y`/`cagr_3y` pinned against a hand-checked figure
- grandfathering: a seeded row failing the gate stays `is_published = true`

**Frontend** has no RTL or Playwright, so this is source-contract tests in the existing `frontend/tests/*.test.mjs` style:

- the grandfather seed list is present in the migration
- `dynamicParams` and `revalidate` are set on the fund route
- `sitemapValidation.test.mjs` pins the catalog query rather than `FUND_REGISTRY`

**Pre-merge full check** per `Agents.md`: `pytest backend/tests`, `node --test tests/*.test.mjs`, `npx tsc --noEmit`, `npm run lint`, `npm run build`, `git diff --check`.

## 9. Documentation to update on landing

- `docs/CURRENT_STATE.md` — coverage numbers and what is deployed vs planned
- `docs/04_DATABASE_SCHEMA.md` — the two new tables
- `docs/03_API_CONTRACTS.md` — only if any route handler surface changes
- `docs/jobs.md` — the three new jobs and the `mf-sync.yml` step

## 10. Open items

1. **mfapi rate ceiling is unmeasured.** Backfill runtime and the sustainable steady-state limit are unknown until the first dispatch run. Do not hardcode a limit beforehand.
2. **`nav_api_cache` contention** between the factsheet-gated job and the catalog job needs a distinct ordering function, not a mutation of the shared one.
3. **Post-backfill catalog size is an estimate.** 1,000–1,500 is projected from normalizer behaviour, not measured. Re-measure after step 3 and revisit the prerender count before step 5.
4. **The six-week `mutual_fund_nav_history` staleness** (max `nav_date` 2026-07-19 against a snapshot at 2026-09-02) is a live defect independent of this feature and should be confirmed fixed by the backfill, not assumed.
