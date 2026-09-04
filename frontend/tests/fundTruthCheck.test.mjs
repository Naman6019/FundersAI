import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (relativePath) => readFileSync(new URL(relativePath, import.meta.url), 'utf8');
const page = read('../app/tools/fund-truth-check/page.tsx');
const route = read('../app/api/funds/claim-check/route.ts');
const privateFeature = read('../lib/fundTruthCheckPrivate.ts');
const workbench = read('../components/truth-check/TruthCheckWorkbench.tsx');
const resultCard = read('../components/truth-check/ClaimResultCard.tsx');
const shareButton = read('../components/truth-check/ShareClaimButton.tsx');
const rateLimit = read('../lib/rateLimit.ts');
const toolsIndex = read('../app/tools/page.tsx');
const sitemap = read('../app/sitemap.ts');

test('Fund Truth Check is private, authenticated, dynamic, and noindex', () => {
  assert.match(privateFeature, /NODE_ENV !== 'production'/);
  assert.match(privateFeature, /FUND_TRUTH_CHECK_PRIVATE_ENABLED === 'true'/);
  assert.match(page, /isFundTruthCheckPrivateEnabled\(\)/);
  assert.match(page, /notFound\(\)/);
  assert.match(page, /<AuthGate>/);
  assert.match(page, /dynamic = 'force-dynamic'/);
  assert.match(page, /index: false, follow: false, nocache: true/);
});

test('browser proxy fails closed and preserves the server-only backend boundary', () => {
  assert.match(route, /NODE_ENV === 'production' && !userContext/);
  assert.match(route, /enforceRateLimit\(request, 'claim-check'/);
  assert.match(route, /CLAIM_CHECK_INTERNAL_PROXY_KEY/);
  assert.match(route, /'X-Internal-Proxy-Key': proxyKey/);
  assert.match(route, /'Cache-Control': 'no-store, max-age=0'/);
  assert.match(route, /'X-Robots-Tag': 'noindex, nofollow, noarchive'/);
  assert.match(route, /input\.length < 3 \|\| input\.length > 2_000/);
  assert.match(route, /AbortSignal\.timeout\(15_000\)/);
});

test('results render one card per atomic claim and keep verdict separate from freshness', () => {
  assert.match(workbench, /result\.claims\.map/);
  assert.match(workbench, /<ClaimResultCard/);
  assert.match(resultCard, /Evidence freshness:/);
  assert.match(resultCard, /Verdict and freshness are separate checks/);
  assert.match(resultCard, /This verdict describes the cited historical period/);
  assert.match(resultCard, /Official evidence/);
});

test('clarification edits wording but does not auto-submit', () => {
  assert.match(workbench, /chooseClarification/);
  assert.match(workbench, /Review it, then run the check again/);
  const clarificationBody = workbench.slice(
    workbench.indexOf('const chooseClarification'),
    workbench.indexOf("return (", workbench.indexOf('const chooseClarification')),
  );
  assert.doesNotMatch(clarificationBody, /submit\(/);
});

test('analytics contains aggregates only and checks are not persisted by the UI', () => {
  assert.match(workbench, /fund_truth_check_completed/);
  assert.match(workbench, /claim_count/);
  assert.match(workbench, /definitive_count/);
  assert.doesNotMatch(workbench, /trackEvent\([^)]*(input|statement):/s);
  assert.doesNotMatch(workbench, /localStorage|sessionStorage/);
});

test('share card is generated locally and never uploaded', () => {
  assert.match(shareButton, /document\.createElement\('canvas'\)/);
  assert.match(shareButton, /canvas\.toBlob/);
  assert.match(shareButton, /Download image/);
  assert.match(shareButton, /navigator\.share/);
  assert.doesNotMatch(shareButton, /fetch\(/);
});

test('private review build is absent from public tools and sitemap', () => {
  assert.doesNotMatch(toolsIndex, /fund-truth-check/i);
  assert.doesNotMatch(sitemap, /fund-truth-check/i);
  assert.match(rateLimit, /\| 'claim-check'/);
  assert.match(rateLimit, /'claim-check': \[/);
});
