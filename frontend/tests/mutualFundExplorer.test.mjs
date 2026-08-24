import assert from 'node:assert/strict';
import test from 'node:test';
import { FUND_REGISTRY, AMC_REGISTRY, CATEGORY_LIST } from '../lib/fund-registry.ts';

// Pure filtering logic mirror for isolated unit verification
function filterFunds(funds, { amc = 'all', category = 'all', query = '' }) {
  return funds.filter((fund) => {
    if (amc !== 'all' && fund.amcSlug !== amc) return false;
    if (category !== 'all' && fund.category.toLowerCase() !== category.toLowerCase()) return false;
    if (query.trim()) {
      const q = query.toLowerCase().trim();
      const matchesName = fund.schemeName.toLowerCase().includes(q);
      const matchesAmc = fund.amcName.toLowerCase().includes(q);
      const matchesCat = fund.category.toLowerCase().includes(q);
      const matchesBenchmark = fund.benchmark.toLowerCase().includes(q);
      const matchesCode = fund.schemeCode.toString().includes(q);
      return matchesName || matchesAmc || matchesCat || matchesBenchmark || matchesCode;
    }
    return true;
  });
}

test('Screener returns all funds when no filters or queries are applied', () => {
  const result = filterFunds(FUND_REGISTRY, { amc: 'all', category: 'all', query: '' });
  assert.equal(result.length, FUND_REGISTRY.length);
});

test('Screener filters correctly by AMC family', () => {
  const hdfcFunds = filterFunds(FUND_REGISTRY, { amc: 'hdfc', category: 'all', query: '' });
  assert.ok(hdfcFunds.length >= 3);
  assert.ok(hdfcFunds.every((f) => f.amcSlug === 'hdfc'));

  const sbiFunds = filterFunds(FUND_REGISTRY, { amc: 'sbi', category: 'all', query: '' });
  assert.ok(sbiFunds.length >= 3);
  assert.ok(sbiFunds.every((f) => f.amcSlug === 'sbi'));
});

test('Screener filters correctly by SEBI category', () => {
  const smallCapFunds = filterFunds(FUND_REGISTRY, { amc: 'all', category: 'Small Cap', query: '' });
  assert.ok(smallCapFunds.length >= 4);
  assert.ok(smallCapFunds.every((f) => f.category === 'Small Cap'));

  const flexiCapFunds = filterFunds(FUND_REGISTRY, { amc: 'all', category: 'Flexi Cap', query: '' });
  assert.ok(flexiCapFunds.length >= 4);
  assert.ok(flexiCapFunds.every((f) => f.category === 'Flexi Cap'));
});

test('Screener executes dual-filtering (AMC + Category simultaneously)', () => {
  // 1. HDFC + Small Cap -> exactly HDFC Small Cap Fund
  const hdfcSmallCap = filterFunds(FUND_REGISTRY, { amc: 'hdfc', category: 'Small Cap', query: '' });
  assert.equal(hdfcSmallCap.length, 1);
  assert.equal(hdfcSmallCap[0].fundSlug, 'hdfc-small-cap-fund');

  // 2. PPFAS + Flexi Cap -> Parag Parikh Flexi Cap Fund
  const ppfasFlexi = filterFunds(FUND_REGISTRY, { amc: 'ppfas', category: 'Flexi Cap', query: '' });
  assert.equal(ppfasFlexi.length, 1);
  assert.equal(ppfasFlexi[0].fundSlug, 'parag-parikh-flexi-cap-fund');

  // 3. Nippon + Small Cap -> Nippon India Small Cap Fund
  const nipponSmallCap = filterFunds(FUND_REGISTRY, { amc: 'nippon', category: 'Small Cap', query: '' });
  assert.equal(nipponSmallCap.length, 1);
  assert.equal(nipponSmallCap[0].fundSlug, 'nippon-india-small-cap-fund');
});

test('Screener search matches across multiple attributes', () => {
  // By partial fund name
  const parikh = filterFunds(FUND_REGISTRY, { amc: 'all', category: 'all', query: 'Parikh' });
  assert.ok(parikh.length >= 1);
  assert.ok(parikh.every((f) => f.schemeName.includes('Parag Parikh')));

  // By AMFI Scheme Code
  const codeMatch = filterFunds(FUND_REGISTRY, { amc: 'all', category: 'all', query: '120503' });
  assert.ok(codeMatch.length >= 1);
  assert.ok(codeMatch.some((f) => f.schemeCode === 120503));

  // By Benchmark Index keyword
  const bse500 = filterFunds(FUND_REGISTRY, { amc: 'all', category: 'all', query: 'BSE 500' });
  assert.ok(bse500.length >= 2);
  assert.ok(bse500.every((f) => f.benchmark.includes('BSE 500')));
});

test('Screener handles zero-match edge cases gracefully', () => {
  const noMatch = filterFunds(FUND_REGISTRY, { amc: 'all', category: 'all', query: 'xyznonexistentfund999' });
  assert.equal(noMatch.length, 0);

  const incompatibleDual = filterFunds(FUND_REGISTRY, { amc: 'ppfas', category: 'Small Cap', query: '' });
  assert.equal(incompatibleDual.length, 0);
});
