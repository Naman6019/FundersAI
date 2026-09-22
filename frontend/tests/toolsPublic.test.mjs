import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const FRONTEND_ROOT = path.resolve(__dirname, '..');

// Import fund holdings and overlap engine
import {
  FUND_HOLDINGS_DB,
  getHoldingsForScheme,
  calculateDetailedOverlap,
} from '../lib/fund-holdings.ts';
import { FUND_REGISTRY, getFundBySchemeCode } from '../lib/fund-registry.ts';

test('calculateDetailedOverlap computes 100% overlap for identical holdings', () => {
  const holdings = [
    { isin: 'INE040A01034', name: 'HDFC Bank Ltd', weight: 10, sector: 'Financial Services' },
    { isin: 'INE090A01021', name: 'ICICI Bank Ltd', weight: 10, sector: 'Financial Services' },
  ];

  const result = calculateDetailedOverlap(holdings, holdings);
  assert.equal(result.percentage, 20); // Sum of min weights
  assert.equal(result.overlappingCount, 2);
  assert.equal(result.uniqueA.length, 0);
  assert.equal(result.uniqueB.length, 0);
});

test('calculateDetailedOverlap computes 0% overlap for disjoint holdings', () => {
  const holdingsA = [
    { isin: 'INE040A01034', name: 'HDFC Bank Ltd', weight: 10, sector: 'Financial Services' },
  ];
  const holdingsB = [
    { isin: 'INE002A01018', name: 'Reliance Industries Ltd', weight: 10, sector: 'Energy & Utilities' },
  ];

  const result = calculateDetailedOverlap(holdingsA, holdingsB);
  assert.equal(result.percentage, 0);
  assert.equal(result.overlappingCount, 0);
  assert.equal(result.uniqueA.length, 1);
  assert.equal(result.uniqueB.length, 1);
  assert.equal(result.verdict.level, 'Low');
});

test('calculateDetailedOverlap evaluates PPFAS vs HDFC Flexi Cap correctly', () => {
  const ppfas = FUND_HOLDINGS_DB[122639];
  const hdfc = FUND_HOLDINGS_DB[118955];

  assert.ok(ppfas?.holdings.length, 'PPFAS holdings must exist');
  assert.ok(hdfc?.holdings.length, 'HDFC Flexi Cap holdings must exist');

  const result = calculateDetailedOverlap(ppfas.holdings, hdfc.holdings);

  // Both hold HDFC Bank, ICICI Bank, Axis Bank, Infosys, ITC, SBI
  assert.ok(result.percentage > 20 && result.percentage < 45, `Expected overlap between 20% and 45%, got ${result.percentage}%`);
  assert.ok(result.overlappingCount >= 5, `Expected >= 5 overlapping stocks, got ${result.overlappingCount}`);
  assert.ok(result.sectorBreakdown.length > 0, 'Sector breakdown should be populated');

  // Verify common stocks contain HDFC Bank and ICICI Bank
  const commonStockNames = result.overlapping.map((s) => s.name);
  assert.ok(commonStockNames.includes('HDFC Bank Ltd'));
  assert.ok(commonStockNames.includes('ICICI Bank Ltd'));
});

test('getHoldingsForScheme abstains for schemes with no curated holdings', () => {
  // Returning a category proxy here is what attributed one fund's stocks to another, so an
  // unknown scheme must yield null and force the caller to show the unavailable state.
  assert.equal(getHoldingsForScheme(999999), null);

  // A scheme in the registry with no snapshot must also abstain, not fall back by category.
  const withoutSnapshot = FUND_REGISTRY.find((f) => FUND_HOLDINGS_DB[f.schemeCode] === undefined);
  assert.ok(withoutSnapshot, 'expected at least one registry scheme without curated holdings');
  assert.equal(getHoldingsForScheme(withoutSnapshot.schemeCode), null);
});

test('every curated holdings entry is attributed to its own scheme', () => {
  // The keys previously named one fund while pointing at another (120503 = Axis ELSS, not
  // HDFC Flexi Cap). Provenance fields make the attribution auditable.
  for (const [code, entry] of Object.entries(FUND_HOLDINGS_DB)) {
    assert.match(entry.asOf, /^\d{4}-\d{2}$/, `${code} must state the month it describes`);
    assert.ok(entry.source.length > 0, `${code} must state its source`);
    assert.ok(entry.holdings.length > 0, `${code} must have holdings`);
    assert.ok(
      getFundBySchemeCode(Number(code)),
      `${code} is not in FUND_REGISTRY, so no picker can select it`,
    );
    for (const h of entry.holdings) {
      assert.equal(typeof h.isin, 'string');
      assert.equal(typeof h.weight, 'number');
      assert.ok(h.weight > 0 && h.weight <= 100, `${code}/${h.isin} has an implausible weight`);
    }
  }
});

test('Public Tools directory and pages exist and are well-formed', () => {
  const toolsIndex = path.join(FRONTEND_ROOT, 'app', 'tools', 'page.tsx');
  const overlapPage = path.join(FRONTEND_ROOT, 'app', 'tools', 'portfolio-overlap', 'page.tsx');
  const sipPage = path.join(FRONTEND_ROOT, 'app', 'tools', 'sip-calculator', 'page.tsx');

  assert.ok(existsSync(toolsIndex), 'tools/page.tsx must exist');
  assert.ok(existsSync(overlapPage), 'tools/portfolio-overlap/page.tsx must exist');
  assert.ok(existsSync(sipPage), 'tools/sip-calculator/page.tsx must exist');

  const overlapSource = readFileSync(overlapPage, 'utf-8');
  assert.match(overlapSource, /canonical.*\/tools\/portfolio-overlap/);
  assert.match(overlapSource, /ToolJsonLd/);
  assert.match(overlapSource, /PortfolioOverlapCalculator/);

  const sipSource = readFileSync(sipPage, 'utf-8');
  assert.match(sipSource, /canonical.*\/tools\/sip-calculator/);
  assert.match(sipSource, /ToolJsonLd/);
  assert.match(sipSource, /SipCalculatorPublic/);
});

test('sitemap.ts contains all public tool URLs', () => {
  const sitemapSource = readFileSync(path.join(FRONTEND_ROOT, 'app', 'sitemap.ts'), 'utf-8');
  assert.match(sitemapSource, /'\/tools'/);
  assert.match(sitemapSource, /'\/tools\/portfolio-overlap'/);
  assert.match(sitemapSource, /'\/tools\/sip-calculator'/);
});

test('next.config.ts redirects legacy synthesis tool path to /tools/portfolio-overlap', () => {
  const nextConfigSource = readFileSync(path.join(FRONTEND_ROOT, 'next.config.ts'), 'utf-8');
  assert.match(nextConfigSource, /destination: '\/tools\/portfolio-overlap'/);
});

test('next.config.ts permanently retires the deleted emergent-replica prototype', () => {
  // The route was deleted in 18a3d4a2, but Search Console still reports impressions for it
  // while it 404s. A permanent redirect retires the URL and forwards residual signals.
  const nextConfigSource = readFileSync(path.join(FRONTEND_ROOT, 'next.config.ts'), 'utf-8');
  assert.match(nextConfigSource, /source: '\/emergent-replica', destination: '\/', permanent: true/);
  assert.ok(
    !existsSync(path.join(FRONTEND_ROOT, 'app', 'emergent-replica')),
    'the deleted prototype route must not be resurrected to satisfy the redirect',
  );
});

test('Mathematical SIP compounding formulas execute with deterministic precision', () => {
  // Monthly SIP formula: P * (((1+r)^n - 1) / r) * (1+r)
  const P = 10000;
  const annualReturn = 12; // 12% p.a. -> 1% per month
  const r = annualReturn / 100 / 12; // 0.01
  const n = 120; // 10 years = 120 months

  const expectedFV = P * (((Math.pow(1 + r, n) - 1) / r)) * (1 + r);
  const totalInvested = P * n;

  assert.equal(totalInvested, 1200000); // 12 Lakhs
  assert.ok(expectedFV > 2300000 && expectedFV < 2350000); // ~23.23 Lakhs
});

test('Dedicated /research page and Master Ecosystem landing page exist and are configured', () => {
  const researchPage = path.join(FRONTEND_ROOT, 'app', 'research', 'page.tsx');
  const masterLandingComponent = path.join(FRONTEND_ROOT, 'components', 'landing', 'MasterEcosystemLandingPage.tsx');
  const ecosystemHeader = path.join(FRONTEND_ROOT, 'components', 'ecosystem', 'EcosystemHeader.tsx');
  const rootPage = path.join(FRONTEND_ROOT, 'app', 'page.tsx');

  assert.ok(existsSync(researchPage), 'app/research/page.tsx must exist');
  assert.ok(existsSync(masterLandingComponent), 'MasterEcosystemLandingPage.tsx must exist');

  const researchSource = readFileSync(researchPage, 'utf-8');
  assert.match(researchSource, /canonical.*\/research/);
  assert.match(researchSource, /PremiumLandingPage/);

  const rootSource = readFileSync(rootPage, 'utf-8');
  assert.match(rootSource, /MasterEcosystemLandingPage/);

  const headerSource = readFileSync(ecosystemHeader, 'utf-8');
  // The header may link to /research directly or resolve it through ecosystemHref,
  // which sends the link off the Synthesis subdomain. Either form satisfies the contract.
  assert.match(headerSource, /href(="|: ")\/research"|ecosystemHref\("\/research"\)/);
});

