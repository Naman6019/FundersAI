import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import ts from 'typescript';

/**
 * Loads JsonLd.tsx and returns its `fundFaqs` export. The component file is TSX, so it is
 * transpiled rather than imported. React is stubbed because these tests exercise the pure
 * schema builders, not the rendered script tag.
 */
function loadJsonLd() {
  const source = ts.transpileModule(readFileSync('components/seo/JsonLd.tsx', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.React },
  }).outputText;
  const exports = {};
  vm.runInNewContext(source, {
    exports,
    require: (name) => (name === 'react' ? { default: {} } : {}),
    JSON,
  });
  return exports;
}

function catalogFund(overrides = {}) {
  return {
    schemeCode: '118955',
    schemeName: 'HDFC Flexi Cap Fund',
    amcSlug: 'hdfc',
    amcName: 'HDFC Mutual Fund',
    fundSlug: 'hdfc-flexi-cap-fund',
    category: 'Flexi Cap',
    plan: 'Direct',
    option: 'Growth',
    benchmark: 'BSE 500 TRI',
    metrics: {
      nav: 2076.1234,
      nav_date: '2026-09-17',
      cagr_1y: 28.4,
      cagr_3y: 22.1,
      cagr_5y: null,
      history_start: '2013-01-02',
      observation_count: 3300,
    },
    ...overrides,
  };
}

test('fundFaqs emits only answers supported by held data', () => {
  const { fundFaqs } = loadJsonLd();
  const faqs = fundFaqs(catalogFund());
  const joined = faqs.map((f) => `${f.q} ${f.a}`).join(' ');

  // Returns FAQ reports the windows we hold and omits the one we do not, rather than
  // extrapolating a 3-year figure from partial history.
  assert.match(joined, /1 year: 28\.40%/);
  assert.match(joined, /3 years: 22\.10%/);
  assert.doesNotMatch(joined, /5 years:/);
  assert.match(joined, /omitted rather than estimated/);
});

test('fundFaqs omits the benchmark answer when no benchmark is held', () => {
  const { fundFaqs } = loadJsonLd();
  const withBenchmark = fundFaqs(catalogFund()).map((f) => f.q);
  const withoutBenchmark = fundFaqs(catalogFund({ benchmark: undefined })).map((f) => f.q);

  assert.ok(withBenchmark.some((q) => /benchmark index/.test(q)));
  assert.ok(!withoutBenchmark.some((q) => /benchmark index/.test(q)));
  // The universal answers must survive either way.
  assert.ok(withoutBenchmark.some((q) => /Direct and Regular/.test(q)));
  assert.ok(withoutBenchmark.some((q) => /NAV data/.test(q)));
});

test('fundFaqs answers the former-name question that search demand still uses', () => {
  const { fundFaqs } = loadJsonLd();
  const faqs = fundFaqs(catalogFund({ formerName: 'HDFC Top 100 Fund' }));
  const answer = faqs.find((f) => /same as/.test(f.q));

  assert.ok(answer, 'renamed funds must answer the former-name query');
  assert.match(answer.q, /HDFC Top 100 Fund/);
  assert.match(answer.a, /renamed to HDFC Flexi Cap Fund/);
  // Continuity of the AMFI code is the reason the rename is safe to state.
  assert.match(answer.a, /118955/);
});

test('fundFaqs drops the returns answer entirely when the window is uncovered', () => {
  const { fundFaqs } = loadJsonLd();
  const faqs = fundFaqs(catalogFund({
    metrics: { nav: null, nav_date: null, cagr_1y: null, cagr_3y: null, cagr_5y: null },
  }));
  assert.ok(!faqs.some((f) => /annualised returns/.test(f.q)));
});

// ─── Source contracts: the schema must stay wired to the routes ──────────────
// These components existed unused for months, so a change that silently unwires one is the
// exact regression worth pinning.

test('catalog routes render their structured-data components', () => {
  const detail = readFileSync('app/mutual-funds/[amcSlug]/[fundSlug]/page.tsx', 'utf8');
  assert.match(detail, /FundJsonLd/, 'fund detail must emit FundJsonLd');
  assert.match(detail, /fundFaqs/, 'the visible FAQ must share the schema source');
  assert.match(detail, /getFundBySchemeCode/, 'benchmark/formerName come from the registry');
  assert.match(detail, /getPeerFunds/, 'peers provide internal links into the registry');

  const directory = readFileSync('app/mutual-funds/page.tsx', 'utf8');
  assert.match(directory, /DirectoryJsonLd/, 'directory must emit DirectoryJsonLd');

  const category = readFileSync('app/mutual-funds/category/[categorySlug]/page.tsx', 'utf8');
  assert.match(category, /CategoryJsonLd/, 'category pages must emit CategoryJsonLd');
});

test('structured data is withheld when the catalog read fails', () => {
  // An outage must not assert an ItemList of funds that could not be verified.
  const directory = readFileSync('app/mutual-funds/page.tsx', 'utf8');
  assert.match(directory, /funds !== null && funds\.length > 0/);
  const category = readFileSync('app/mutual-funds/category/[categorySlug]/page.tsx', 'utf8');
  assert.match(category, /if \(funds === undefined\)/);
});

test('fund detail page never asserts unheld performance data', () => {
  const detail = readFileSync('app/mutual-funds/[amcSlug]/[fundSlug]/page.tsx', 'utf8');
  // The page states the absence of factsheet-gated fields rather than filling them in.
  assert.match(detail, /coverage limit/);
  assert.doesNotMatch(detail, /AggregateRating|aggregateRating|ratingValue/);
});
