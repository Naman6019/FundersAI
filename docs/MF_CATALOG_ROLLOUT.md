# Catalog NAV slice: rollout and commit plan

2026-09-05. Implemented locally; migration and production writes have not run.

## Scope and deliberate changes from the September 3 design

- The current registry contains **29** fund URLs, not the older measured 31. The migration reserves all 29, and a test compares every code and slug with the current registry. Existing URLs cannot be renamed by an update. Legacy status does not bypass eligibility.
- NAV readiness uses the complete `nav_api_cache.payload` consumed by the current MFapi service. It does not use cache TTL, freshly fetched timestamps, snapshot returns, or mere row counts as proof of readiness. This slice does **not** repair or drop the older `mutual_fund_nav_history` table.
- Catalog metrics and eligibility live in one atomic `mf_page_catalog` row, with a method-versioned `metrics` JSON object. This avoids a period where eligibility and a separate metrics table disagree. The larger design's separate metrics table, risk/holdings sections, NAV chart and workspace CAGR consolidation remain outside this slice.
- Public fund, AMC and category pages and sitemap read only eligible catalog rows. Server credentials are required; there is no anonymous-client fallback. A failed database lookup throws; a definitive missing/ineligible fund returns `notFound()`.
- Pages use request-time rendering, not daily ISR. That is intentional: an indefinitely retained ISR response during failed revalidation could keep serving an ineligible scheme. Successful catalog membership is rechecked against the current UTC date. No unmeasured prerender count is chosen.
- Category resolution is deliberately limited to the existing eight category labels and their `Equity Scheme - ... Fund` forms. Unknown labels, ambiguous or conflicting share classes, segregated portfolios and missing identities get explicit rejection reasons.
- A candidate requires Direct Growth identity, recognized category, NAV no more than seven calendar days old, a complete one-year window, at least 250 observations per year, and no internal gap over seven calendar days. Dates must not be in the future; NAVs must be finite and positive; duplicate dates must agree. Longer return windows remain null unless independently covered. Annualization uses actual elapsed days / 365.

## Evidence

Read-only production sample: `--after 119000 --limit 30`, 2026-09-05, 16.487 seconds. Scanned 30, identity-eligible 14, NAV-ready **0**, next cursor `119080`. The local report is `catalog-readiness.local.json`. This is a bounded sample, not a total catalog count or a post-backfill result. It measures read latency, not MFapi refresh throughput.

Tests exercise window lengths, gaps, stale/future/invalid NAV, duplicate conflicts, independent 3Y/5Y eligibility, URL preservation, read-only operation, persisted re-read after refresh, deadlines and provider-request avoidance. Frontend execution tests cover pagination, stale/rejected rows and database error versus absence. Existing sitemap and breadcrumb assertions are retained.

Local verification: focused backend tests passed; the broader backend run passed 1,086 tests with 14 skipped before the last three focused tests were added. All 120 frontend tests, TypeScript, production build and lint passed (repository lint has 32 existing warnings). The built app's synthetic HTTP smoke passed eligible 200, absent/rejected/empty AMC/empty category 404, database outage 500, canonical preservation, rendered NAV/returns, and eligible-only sitemap membership. Run it with `node tests/mfCatalogHttpSmoke.mjs` from `frontend` after building. These HTTP fixtures do not verify production database contents. Graphify was refreshed successfully.

## Commit 1: data gate and bounded operations

Suggested title: `feat(mf): add bounded catalog NAV readiness and backfill`

Stage only:

- The two catalog exceptions in `.gitignore`.
- `backend/app/services/mf_catalog_service.py`
- `backend/app/jobs/backfill_catalog_nav_history.py`
- `backend/app/jobs/build_mf_page_catalog.py`
- `backend/config/mf_catalog_legacy_urls.json`
- `backend/migrations/20260905_add_mf_page_catalog.sql`
- `backend/tests/test_mf_catalog.py`
- `.github/workflows/mf-catalog.yml`
- This runbook and only the catalog additions to `docs/CURRENT_STATE.md`, `docs/04_DATABASE_SCHEMA.md`, and `docs/jobs.md`.

Do not stage the whole working tree: existing discovery, NAV-sync and Truth Check work belongs to other changes.

1. Apply `20260905_add_mf_page_catalog.sql` in staging first. Verify anonymous and authenticated table reads fail, service-role writes succeed, URL changes fail, and a published row without valid gate fields is rejected. The SQL has not been executed locally against PostgreSQL.
2. Run read-only readiness with explicit bounds:

   ```powershell
   .\.venv\Scripts\python.exe backend/app/jobs/backfill_catalog_nav_history.py --after 119000 --limit 30 --output readiness.json
   ```

3. Run the same selected batch with `--apply --require-ready` to request missing/unready histories, then run the read-only check again. Apply refreshes the existing MFapi cache and its existing snapshot-metric side effect. It never publishes pages. Provider data is re-read from storage before evaluating success. Existing-ready histories are skipped.
4. Inspect each rejection and refresh status. Record elapsed time, successful refresh count and provider failures before increasing the explicit limit. A failure can represent genuine insufficient history; do not lower the quality gate to force a green run.
5. Resume using `next_after`. `--limit` bounds **snapshot rows scanned**, not eligible schemes. Default request-start budget is 300 seconds; the deadline is checked between requests, while the provider owns request timeouts/retries. A partial scan exits nonzero and reports its cursor. Revisit failed scheme batches before advancing past them. Restart from `--after 0` for a new complete freshness cycle.
6. Evaluate the catalog without writes, then inspect its report before applying:

   ```powershell
   .\.venv\Scripts\python.exe backend/app/jobs/build_mf_page_catalog.py --after 119000 --limit 30 --output catalog-dry-run.json
   .\.venv\Scripts\python.exe backend/app/jobs/build_mf_page_catalog.py --after 119000 --limit 30 --apply --output catalog-applied.json
   ```

   The second command writes published and rejected rows together with their computed metrics. Lookup failures abort rather than being treated as empty source data. Re-running a batch is idempotent. Reserved URLs and the database unique key prevent slug reassignment/collisions.
7. Repeat measured batches until the intended scheme set and its 29 reserved URLs are accounted for. Missing snapshot rows remain unpublished reservations. Record ready and rejected counts by AMC. Do not extrapolate coverage from the sample above.

The manual `mf-catalog.yml` workflow exposes these four modes and uploads a report. It uses the existing `SUPABASE_URL` and `SUPABASE_KEY` secrets. There is deliberately no guessed recurring refresh budget: establish a complete-cycle runtime, then schedule the measured batches so they complete comfortably inside seven days. **A sustainable refresh cycle is a production activation prerequisite.**

## Commit 2: catalog page cutover

Suggested title: `feat(web): serve eligible mutual-fund catalog pages`

Stage only `frontend/lib/mf/catalog.ts`, `frontend/components/funds/CatalogDirectory.tsx`, the four existing `frontend/app/mutual-funds/**/page.tsx` files, `frontend/app/sitemap.ts`, `frontend/tests/mfCatalog.test.mjs`, `frontend/tests/mfCatalogHttpSmoke.mjs`, `frontend/tests/fixtures/mfCatalogFetch.cjs`, and `frontend/tests/sitemapValidation.test.mjs`.

Keep local reports and build/lint logs out of both commits. The Graphify refresh includes unrelated concurrent changes, so review its generated diff separately instead of staging it wholesale.

Deploy after commit 1's migration, measured backfill, publication report and refresh schedule are ready. Configure server-only `SUPABASE_SERVICE_ROLE_KEY` on Vercel. No browser API or Cloud Run route is added.

Preview acceptance: verify an eligible reserved URL renders dated values and its unchanged canonical; an unknown URL and a rejected scheme return a real HTTP 404; an empty AMC/category returns 404; a database outage returns a server error rather than a cached 404 or successful empty page. Check a mobile-width page and confirm sitemap membership exactly matches eligible pages. Repeat those checks on `https://www.fundersai.co.in` after production deployment.

Rollback: redeploy the prior frontend commit; leave the additive catalog table and URL reservations intact. Pause catalog workflow dispatches if diagnosing a data issue. Do not drop NAV history or alter the existing factsheet-gated job.
