import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync, readdirSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const FRONTEND_ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const APP_ROOT = path.join(FRONTEND_ROOT, 'app');
const COMPONENT = path.join(FRONTEND_ROOT, 'components', 'navigation', 'Breadcrumbs.tsx');

function pageFiles(dir) {
  const out = [];
  for (const entry of readdirSync(dir)) {
    const full = path.join(dir, entry);
    if (statSync(full).isDirectory()) out.push(...pageFiles(full));
    else if (entry === 'page.tsx') out.push(full);
  }
  return out;
}

/**
 * Breadcrumbs used to be copy-pasted markup on ~19 pages, none of it semantic. These
 * tests keep the shared component the only implementation, so a new page cannot quietly
 * reintroduce a `<div>` trail that reads as a run of links to assistive tech.
 */

test('the shared Breadcrumbs component is semantic', () => {
  assert.ok(existsSync(COMPONENT), 'components/navigation/Breadcrumbs.tsx must exist');
  const source = readFileSync(COMPONENT, 'utf-8');

  assert.match(source, /<nav\s+aria-label="Breadcrumb"/, 'must render a labelled nav');
  assert.match(source, /<ol className/, 'crumbs must be an ordered list');
  assert.match(source, /aria-current=\{isLast \? "page" : undefined\}/, 'must mark the current page');
  assert.match(source, /aria-hidden="true">\/</, 'separators must be hidden from assistive tech');

  // Links resolve off the Synthesis subdomain, where a bare "/" is rewritten back to it.
  assert.match(source, /useEcosystemHref/);
  assert.match(source, /href=\{ecosystemHref\(item\.href\)\}/);
});

test('no page hand-rolls a breadcrumb trail any more', () => {
  const offenders = [];

  for (const file of pageFiles(APP_ROOT)) {
    const source = readFileSync(file, 'utf-8');
    // The separator span is the signature of the old copy-pasted trails.
    if (/<span>\/<\/span>/.test(source)) {
      offenders.push(path.relative(FRONTEND_ROOT, file));
    }
  }

  assert.deepEqual(
    offenders,
    [],
    `these pages still hand-roll a breadcrumb; use <Breadcrumbs> instead: ${offenders.join(', ')}`,
  );
});

test('pages that show a trail use the shared component', () => {
  const expected = [
    'app/about/page.tsx',
    'app/compare/[pair]/page.tsx',
    'app/contact/page.tsx',
    'app/data-trust/page.tsx',
    'app/how-it-works/page.tsx',
    'app/intelligence/page.tsx',
    'app/learn/page.tsx',
    'app/methodology/data-sources/page.tsx',
    'app/methodology/formulas/page.tsx',
    'app/methodology/guardrails/page.tsx',
    'app/methodology/page.tsx',
    'app/methodology/resolution/page.tsx',
    'app/mutual-funds/[amcSlug]/[fundSlug]/page.tsx',
    'app/mutual-funds/[amcSlug]/page.tsx',
    'app/mutual-funds/category/[categorySlug]/page.tsx',
    'app/pricing/page.tsx',
    'app/sample/page.tsx',
    'app/synthesis/category/[slug]/page.tsx',
    'app/synthesis/dashboard/page.tsx',
    'app/synthesis/generate/page.tsx',
    'app/synthesis/methodology/page.tsx',
    'app/synthesis/supported-funds/page.tsx',
    'app/synthesis/vs/[slug]/page.tsx',
    'app/tools/page.tsx',
    'app/tools/portfolio-overlap/page.tsx',
    'app/tools/sip-calculator/page.tsx',
  ];

  for (const relative of expected) {
    const file = path.join(FRONTEND_ROOT, relative);
    assert.ok(existsSync(file), `${relative} must exist`);
    const source = readFileSync(file, 'utf-8');
    assert.match(
      source,
      /import Breadcrumbs from '@\/components\/navigation\/Breadcrumbs'/,
      `${relative} must import the shared Breadcrumbs component`,
    );
    assert.match(source, /<Breadcrumbs/, `${relative} must render <Breadcrumbs>`);
  }
});
