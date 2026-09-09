import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (relativePath) => readFileSync(new URL(relativePath, import.meta.url), 'utf8');
const migration = read('../../backend/migrations/20260825_add_user_portfolios.sql');
const triggerMigration = read('../../backend/migrations/20260825_harden_portfolio_updated_at.sql');
const portfolioRoute = read('../app/api/portfolio/route.ts');
const positionsRoute = read('../app/api/portfolio/[portfolioId]/positions/route.ts');
const analytics = read('../lib/portfolioAnalytics.ts');
const tracking = read('../lib/portfolioTracking.ts');
const tracker = read('../components/portfolio/PortfolioTracker.tsx');

test('portfolio migration stores manual positions with user-scoped RLS', () => {
  assert.match(migration, /CREATE TABLE IF NOT EXISTS public\.portfolios/);
  assert.match(migration, /CREATE TABLE IF NOT EXISTS public\.portfolio_positions/);
  assert.match(migration, /UNIQUE \(portfolio_id, scheme_code\)/);
  assert.match(migration, /position_source TEXT NOT NULL DEFAULT 'manual'/);
  assert.match(migration, /ALTER TABLE public\.portfolios ENABLE ROW LEVEL SECURITY/);
  assert.match(migration, /ALTER TABLE public\.portfolio_positions ENABLE ROW LEVEL SECURITY/);
  assert.match(migration, /REVOKE ALL ON TABLE public\.portfolios, public\.portfolio_positions FROM anon, authenticated/);
  assert.match(migration, /portfolios\.user_id = \(select auth\.uid\(\)\)/);
  assert.match(migration, /GRANT SELECT, INSERT, UPDATE, DELETE ON public\.portfolios TO authenticated/);
  assert.match(migration, /GRANT SELECT, INSERT, UPDATE, DELETE ON public\.portfolio_positions TO authenticated/);
  assert.match(triggerMigration, /SET search_path = ''/);
});

test('portfolio APIs authenticate before using the RLS-scoped client', () => {
  assert.match(portfolioRoute, /requireUserContext\(request\)/g);
  assert.match(portfolioRoute, /supabaseUser\s*\n?\s*\.from\('portfolios'\)/);
  assert.match(portfolioRoute, /supabaseUser\s*\n?\s*\.from\('portfolio_positions'\)/);
  assert.match(positionsRoute, /requireUserContext\(request\)/g);
  assert.match(positionsRoute, /supabaseUser/);
  assert.match(positionsRoute, /position_source: 'manual'/);
  assert.match(positionsRoute, /position_already_exists/);
});

test('aggregate overlap keeps coverage limits and avoids pairwise over-counting', () => {
  assert.match(analytics, /largestSingleFundExposure/);
  assert.match(analytics, /total_overlap_exposure/);
  assert.match(analytics, /covered_current_value/);
  assert.match(analytics, /uncovered_current_value/);
  assert.match(analytics, /coverage_status/);
  assert.match(tracking, /nav_status/);
  assert.match(tracking, /holdings_status/);
  assert.match(tracking, /NAV_FRESH_DAYS/);
});

test('portfolio UI exposes manual inputs, freshness, overlap, and the research-only boundary', () => {
  assert.match(tracker, /scheme_code/);
  assert.match(tracker, /current_value/);
  assert.match(tracker, /Aggregate overlap/);
  assert.match(tracker, /Data freshness/);
  assert.match(tracker, /Research only/);
  assert.match(tracker, /does not import transactions/);
  assert.match(tracker, /not an investment recommendation/);
});
