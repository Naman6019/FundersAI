import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import test from 'node:test';

test('JsonLd component exports all required Schema.org generator components', () => {
  const source = readFileSync(resolve('components/seo/JsonLd.tsx'), 'utf8');

  // Verify all essential components exist and export
  assert.match(source, /export function FundJsonLd/);
  assert.match(source, /export function CompareJsonLd/);
  assert.match(source, /export function CategoryJsonLd/);
  assert.match(source, /export function ArticleJsonLd/);
  assert.match(source, /export function DirectoryJsonLd/);
});

test('FundJsonLd defines FinancialProduct, BreadcrumbList, and FAQPage graphs', () => {
  const source = readFileSync(resolve('components/seo/JsonLd.tsx'), 'utf8');

  assert.match(source, /'@type':\s*'FinancialProduct'/);
  assert.match(source, /'@type':\s*'BreadcrumbList'/);
  assert.match(source, /'@type':\s*'FAQPage'/);
  assert.match(source, /Direct plan has zero distributor commission/);
  assert.match(source, /What is the benchmark index for/);
});

test('CompareJsonLd creates valid side-by-side comparison metadata', () => {
  const source = readFileSync(resolve('components/seo/JsonLd.tsx'), 'utf8');

  assert.match(source, /'@type':\s*'WebPage'/);
  assert.match(source, /Side-by-side comparison of/);
  assert.match(source, /portfolio overlap/);
});

test('DirectoryJsonLd generates CollectionPage with ItemList entities', () => {
  const source = readFileSync(resolve('components/seo/JsonLd.tsx'), 'utf8');

  assert.match(source, /['"]@type['"]:\s*'CollectionPage'/);
  assert.match(source, /['"]@type['"]:\s*'ItemList'/);
  assert.match(source, /['"]numberOfItems['"]:\s*funds\.length/);
  assert.match(source, /['"]itemListElement['"]:\s*funds\.map/);
});

test('ArticleJsonLd sets TechArticle structure for educational guides', () => {
  const source = readFileSync(resolve('components/seo/JsonLd.tsx'), 'utf8');

  assert.match(source, /['"]@type['"]:\s*'TechArticle'/);
  assert.match(source, /['"]inLanguage['"]:\s*'en-IN'/);
  assert.match(source, /FundersAI Research Team/);
});
