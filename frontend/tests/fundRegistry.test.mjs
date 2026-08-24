import assert from 'node:assert/strict';
import test from 'node:test';
import {
  AMC_REGISTRY,
  CATEGORY_LIST,
  FUND_REGISTRY,
  COMPARE_PAIRS,
  categorySlug,
  getCategoryBySlug,
  getFundBySlug,
  getAmcBySlug,
  getFundsByAmc,
  getFundBySchemeCode,
  getFundsByCategory,
} from '../lib/fund-registry.ts';

test('AMC registry contains valid definitions and unique slugs', () => {
  assert.ok(AMC_REGISTRY.length >= 10, 'Must have at least 10 AMCs');
  const slugs = new Set();

  for (const amc of AMC_REGISTRY) {
    assert.ok(amc.slug, 'AMC must have slug');
    assert.ok(amc.name, 'AMC must have name');
    assert.ok(amc.shortName, 'AMC must have shortName');
    assert.ok(amc.description, 'AMC must have description');
    assert.ok(!slugs.has(amc.slug), `Duplicate AMC slug: ${amc.slug}`);
    slugs.add(amc.slug);
  }
});

test('FUND_REGISTRY contains valid unique scheme codes and fund slugs', () => {
  assert.ok(FUND_REGISTRY.length >= 20, 'Must have at least 20 registered funds');
  const codes = new Set();
  const amcFundSlugs = new Set();

  for (const fund of FUND_REGISTRY) {
    assert.ok(typeof fund.schemeCode === 'number', `Scheme code must be a number: ${fund.schemeName}`);
    assert.ok(fund.schemeCode > 100000, `Scheme code must be valid AMFI code: ${fund.schemeCode}`);
    assert.ok(!codes.has(fund.schemeCode), `Duplicate AMFI scheme code: ${fund.schemeCode}`);
    codes.add(fund.schemeCode);

    const compositeSlug = `${fund.amcSlug}/${fund.fundSlug}`;
    assert.ok(!amcFundSlugs.has(compositeSlug), `Duplicate composite fund slug: ${compositeSlug}`);
    amcFundSlugs.add(compositeSlug);

    // Verify AMC exists in AMC_REGISTRY
    const parentAmc = AMC_REGISTRY.find((a) => a.slug === fund.amcSlug);
    assert.ok(parentAmc, `Fund references unknown AMC slug: ${fund.amcSlug}`);

    // Verify category is valid
    assert.ok(
      CATEGORY_LIST.includes(fund.category),
      `Invalid category "${fund.category}" in fund: ${fund.schemeName}`,
    );

    // Verify plan & option
    assert.equal(fund.plan, 'Direct');
    assert.equal(fund.option, 'Growth');
    assert.ok(fund.benchmark, 'Fund must have benchmark index');
  }
});

test('categorySlug and getCategoryBySlug maintain bidirectional mapping', () => {
  for (const cat of CATEGORY_LIST) {
    const slug = categorySlug(cat);
    assert.ok(slug, `categorySlug must produce non-empty string for ${cat}`);
    assert.doesNotMatch(slug, /[&\s/]/, `Slug must not contain whitespace or special chars: ${slug}`);

    const retrieved = getCategoryBySlug(slug);
    assert.equal(retrieved, cat, `getCategoryBySlug(${slug}) must resolve back to ${cat}`);
  }
});

test('Fund lookup helpers return correct entities', () => {
  const hdfcFlexi = getFundBySlug('hdfc', 'hdfc-flexi-cap-fund');
  assert.ok(hdfcFlexi);
  assert.equal(hdfcFlexi.schemeCode, 120503);
  assert.equal(hdfcFlexi.category, 'Flexi Cap');

  const byCode = getFundBySchemeCode(120503);
  assert.equal(byCode?.fundSlug, 'hdfc-flexi-cap-fund');

  const hdfcAmc = getAmcBySlug('hdfc');
  assert.ok(hdfcAmc);
  assert.equal(hdfcAmc.shortName, 'HDFC');

  const hdfcFunds = getFundsByAmc('hdfc');
  assert.ok(hdfcFunds.length >= 3);
  assert.ok(hdfcFunds.every((f) => f.amcSlug === 'hdfc'));

  const smallCapFunds = getFundsByCategory('Small Cap');
  assert.ok(smallCapFunds.length >= 3);
  assert.ok(smallCapFunds.every((f) => f.category === 'Small Cap'));
});

test('COMPARE_PAIRS entries reference valid funds in registry', () => {
  assert.ok(COMPARE_PAIRS.length >= 4);

  for (const pair of COMPARE_PAIRS) {
    const fundA = getFundBySlug(pair.amcSlugA, pair.fundSlugA);
    const fundB = getFundBySlug(pair.amcSlugB, pair.fundSlugB);

    assert.ok(fundA, `Compare pair ${pair.pair} fund A not found: ${pair.fundSlugA}`);
    assert.ok(fundB, `Compare pair ${pair.pair} fund B not found: ${pair.fundSlugB}`);
    assert.notEqual(fundA.schemeCode, fundB.schemeCode, 'Comparison pair must compare distinct funds');
  }
});
