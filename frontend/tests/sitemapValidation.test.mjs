import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import test from 'node:test';

test('sitemap.ts is configured for the two supported production hosts', () => {
  const source = readFileSync(resolve('app/sitemap.ts'), 'utf8');

  // Verify BASE_URL
  assert.match(source, /BASE_URL\s*=\s*'https:\/\/www\.fundersai\.co\.in'/);

  // The synthesis subdomain used to be quarantined out of this sitemap because the studio
  // was reachable on www as well, so listing it would have submitted duplicate URLs. Now
  // that middleware pins each product to one host and the studio pages carry subdomain
  // canonicals, the studio is listed here instead of being link-discoverable only.
  // Cross-host entries require synthesis.fundersai.co.in to be a verified Search Console
  // property (or covered by a fundersai.co.in domain property).
  assert.match(source, /SYNTHESIS_URL\s*=\s*'https:\/\/synthesis\.fundersai\.co\.in'/);

  // Noindex studio surfaces must never be submitted. Matches a quoted path literal rather
  // than the bare word, so prose in a comment does not trip the assertion.
  assert.doesNotMatch(source, /['"`]\/synthesis\/generate/);
  assert.doesNotMatch(source, /['"`]\/synthesis\/dashboard/);

  // Prototype route check
  assert.doesNotMatch(source, /emergent-replica/);

  // Index core routes
  assert.match(source, /FUND_REGISTRY/);
  assert.match(source, /AMC_REGISTRY/);
  assert.match(source, /CATEGORY_LIST/);
  assert.match(source, /COMPARE_PAIRS/);
});

test('robots.ts configures search crawlers and points to primary sitemap.xml', () => {
  const source = readFileSync(resolve('app/robots.ts'), 'utf8');

  assert.match(source, /sitemap:\s*'https:\/\/www\.fundersai\.co\.in\/sitemap\.xml'/);
  assert.match(source, /userAgent:\s*'\*'/);
  assert.match(source, /allow:\s*'\/'/);
  assert.match(source, /disallow:\s*\[\s*['"]\/api\/['"],\s*['"]\/admin\/['"]\s*\]/);
});

test('GEO files (llms.txt and llms-full.txt) are valid and present in public directory', () => {
  const llmsPath = resolve('public/llms.txt');
  const llmsFullPath = resolve('public/llms-full.txt');

  assert.ok(existsSync(llmsPath), 'public/llms.txt must exist');
  assert.ok(existsSync(llmsFullPath), 'public/llms-full.txt must exist');

  const llmsContent = readFileSync(llmsPath, 'utf8');
  assert.match(llmsContent, /# FundersAI/);
  assert.match(llmsContent, /https:\/\/www\.fundersai\.co\.in\/mutual-funds/);
  assert.match(llmsContent, /https:\/\/www\.fundersai\.co\.in\/methodology/);

  const fullContent = readFileSync(llmsFullPath, 'utf8');
  assert.match(fullContent, /HDFC Mutual Fund/);
  assert.match(fullContent, /Compound Annual Growth Rate/);
  assert.match(fullContent, /Sharpe Ratio/);
});
