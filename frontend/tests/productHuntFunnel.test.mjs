import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import test from 'node:test';

const read = (path) => readFileSync(resolve(path), 'utf8');

test('Product Hunt flow is routed through signup and keeps the research-only boundary visible', () => {
  const banner = read('components/growth/ProductHuntWelcomeBanner.tsx');
  const header = read('components/ecosystem/EcosystemHeader.tsx');
  const auth = read('components/auth/AuthForm.tsx');
  const callback = read('app/auth/callback/page.tsx');

  assert.match(header, /ProductHuntWelcomeBanner/);
  assert.match(banner, /utm_source/);
  assert.match(banner, /mode=signup/);
  assert.match(banner, /research only/i);
  assert.match(banner, /trackWhopEvent\("lead"\)/);
  assert.doesNotMatch(banner, /50% off|PRODUCTHUNT/);
  assert.match(auth, /searchParams\.get\('mode'\) === 'signup'/);
  assert.match(auth, /signup=1/);
  assert.match(callback, /trackWhopEvent\('complete_registration'/);
});

test('Whop Pixel conversions map to completed funnel states without breaking the flow', () => {
  const pixel = read('lib/whopPixel.ts');
  const billing = read('components/billing/BillingPage.tsx');
  const report = read('app/synthesis/generate/page.tsx');
  const privacy = read('app/privacy/page.tsx');

  assert.match(pixel, /window\.whop\?\.track/);
  assert.match(billing, /res\.status === 401/);
  assert.match(billing, /trackWhopEvent\('purchase'/);
  assert.match(report, /Authorization: `Bearer \$\{session\.access_token\}`/);
  assert.match(report, /trackWhopEvent\('report_generated'/);
  assert.match(report, /receivedReportText/);
  assert.match(privacy, /Whop Pixel/);
});
