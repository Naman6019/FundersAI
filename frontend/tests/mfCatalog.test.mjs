import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import ts from 'typescript';

function loadCatalog(responses = []) {
  const calls = [];
  const query = new Proxy({}, { get: (_, key) => {
    if (key === 'then') return (resolve) => resolve(responses.shift());
    return (...args) => { calls.push([key, ...args]); return query; };
  } });
  const exports = {};
  const source = ts.transpileModule(readFileSync('lib/mf/catalog.ts', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  vm.runInNewContext(source, { exports, process: { env: { NEXT_PUBLIC_SUPABASE_URL: 'https://test.invalid', SUPABASE_SERVICE_ROLE_KEY: 'test' } },
    require: name => name === 'react' ? { cache: fn => fn } : name === '@supabase/supabase-js' ? { createClient: () => ({ from: () => query }) } : {},
  });
  return { ...exports, calls };
}
function fund() {
  return { scheme_code: '120503', amc_slug: 'hdfc', fund_slug: 'hdfc-flexi-cap-fund', category: 'Flexi Cap',
    is_published: true, gate_reasons: [], metrics: { method_version: 'catalog_nav_v1', nav: 100,
      nav_date: new Date().toISOString().slice(0, 10), cagr_1y: 10 } };
}

test('catalog rejects stale, missing, future and rejected metrics', () => {
  const { isEligible } = loadCatalog();
  assert.equal(isEligible(fund()), true);
  for (const change of [{ nav_date: '2000-01-01' }, { nav_date: '2099-01-01' }, { nav: null },
    { cagr_1y: null }, { nav: Infinity }, { method_version: 'old' }]) {
    assert.equal(isEligible({ ...fund(), metrics: { ...fund().metrics, ...change } }), false);
  }
  assert.equal(isEligible({ ...fund(), is_published: false }), false);
  assert.equal(isEligible({ ...fund(), gate_reasons: ['incomplete'] }), false);
});

test('database failure throws, definitive absence and ineligibility return null', async () => {
  await assert.rejects(loadCatalog([{ data: null, error: { message: 'offline' } }]).getPublishedFund('a', 'b'), /Catalog lookup failed/);
  assert.equal(await loadCatalog([{ data: null, error: null }]).getPublishedFund('a', 'b'), null);
  assert.equal(await loadCatalog([{ data: { ...fund(), is_published: false }, error: null }]).getPublishedFund('a', 'b'), null);
  const api = loadCatalog([{ data: fund(), error: null }]);
  assert.equal((await api.getPublishedFund('hdfc', 'hdfc-flexi-cap-fund')).scheme_code, '120503');
  assert.ok(api.calls.some(c => c[0] === 'eq' && c[1] === 'amc_slug' && c[2] === 'hdfc'));
});

test('directory pagination keeps all eligible rows and fails on partial lookup failure', async () => {
  const page = Array.from({ length: 500 }, fund);
  const api = loadCatalog([{ data: page, error: null }, { data: [fund(), { ...fund(), is_published: false }], error: null }]);
  assert.equal((await api.getPublishedFunds()).length, 501);
  assert.ok(api.calls.some(c => c[0] === 'range' && c[1] === 500 && c[2] === 999));
  await assert.rejects(loadCatalog([{ data: page, error: null }, { data: null, error: {} }]).getPublishedFunds(), /Catalog lookup failed/);
});

test('public fund routes use catalog lookups without handwritten fallback or stale ISR', () => {
  for (const route of ['page.tsx', '[amcSlug]/page.tsx', '[amcSlug]/[fundSlug]/page.tsx', 'category/[categorySlug]/page.tsx']) {
    const source = readFileSync(`app/mutual-funds/${route}`, 'utf8');
    assert.match(source, /@\/lib\/mf\/catalog/);
    assert.match(source, /force-dynamic/);
    assert.doesNotMatch(source, /FUND_REGISTRY|getFundBySlug|StaticFundDisplay/);
  }
});
