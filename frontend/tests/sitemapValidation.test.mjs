import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import test from 'node:test';

test('sitemap.ts is configured exclusively for supported production domain', () => {
  const source = readFileSync(resolve('app/sitemap.ts'), 'utf8');

  // Verify BASE_URL
  assert.match(source, /BASE_URL\s*=\s*'https:\/\/www\.fundersai\.co\.in'/);

  // Quarantine check: must NOT include synthesis subdomain in primary sitemap
  assert.doesNotMatch(source, /synthesis\.fundersai\.co\.in/);

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
