import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import test from 'node:test';

test('authenticated Data & Trust page exposes live metrics, pipeline boundaries, and AMC quality', () => {
  const route = readFileSync(resolve('app/dashboard/data-trust/page.tsx'), 'utf8');
  const page = readFileSync(resolve('components/data-health/DataTrustPage.tsx'), 'utf8');
  const health = readFileSync(resolve('lib/dataHealth.ts'), 'utf8');

  assert.match(route, /<AuthGate>/);
  assert.match(route, /<DataHealthProvider>/);
  for (const label of ['MF NAV', 'AUM / TER', 'Risk metrics', 'AMC docs']) {
    assert.match(health, new RegExp(label.replace(/[\/]/g, '\\/')));
  }
  for (const copy of ['Acquisition and promotion stay separate', 'Why FundersAI was built']) {
    assert.match(page, new RegExp(copy));
  }
  assert.match(page, /pipeline\.total_documents/);
  assert.match(page, /quality\.map/);
  assert.match(page, /Refresh status/);
  assert.match(page, /never starts discovery, ingestion, parsing, sync, or promotion/);
});

test('health polling is foreground-only, one minute, and retains last successful values', () => {
  const hook = readFileSync(resolve('hooks/useDataHealth.ts'), 'utf8');

  assert.match(hook, /pollIntervalMs = 60_000/);
  assert.match(hook, /document\.visibilityState/);
  assert.match(hook, /visibilitychange/);
  assert.match(hook, /setInterval\(\(\) => void refresh\(\), pollIntervalMs\)/);
  assert.match(hook, /setLastSuccessfulCheck/);
  assert.doesNotMatch(hook, /setData\(DEFAULT_PAYLOAD\)/);
});

test('landing page has a static Data & Trust preview and authenticated CTA', () => {
  const landing = readFileSync(resolve('components/landing/PremiumLandingPage.jsx'), 'utf8');

  assert.match(landing, /id="data-trust"/);
  assert.match(landing, /href="\/dashboard\/data-trust"/);
  assert.match(landing, /Acquisition and promotion stay separate|discovery, acquisition, parsing, and validated runtime data separate/);
  assert.doesNotMatch(landing, /fetch\(['"]\/api\/data-health/);
});
