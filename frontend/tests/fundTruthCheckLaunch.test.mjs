import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const read = (relativePath) => readFileSync(new URL(relativePath, import.meta.url), 'utf8');
const page = read('../app/fund-truth-check/page.tsx');
const launchPage = read('../components/landing/FundTruthCheckLaunchPage.tsx');
const sitemap = read('../app/sitemap.ts');
const tools = read('../app/tools/page.tsx');
const banner = read('../components/growth/ProductHuntWelcomeBanner.tsx');
const home = read('../components/landing/MasterEcosystemLandingPage.tsx');
const badge = read('../components/growth/ProductHuntBadge.tsx');
const gallery = read('../app/fund-truth-check/product-hunt-gallery/route.tsx');
const thumbnail = read('../app/fund-truth-check/product-hunt-thumbnail/route.tsx');

test('public launch page is a preview and does not expose the private live checker', () => {
  assert.match(page, /canonical: 'https:\/\/www\.fundersai\.co\.in\/fund-truth-check'/);
  assert.match(page, /opengraph-image/);
  assert.match(launchPage, /Interactive product preview/);
  assert.match(launchPage, /This preview does not submit or evaluate a live claim/);
  assert.match(launchPage, /Live, arbitrary-claim checks remain in private beta/);
  assert.doesNotMatch(launchPage, /\/api\/funds\/claim-check/);
});

test('launch page is discoverable without adding the private route to public navigation', () => {
  assert.match(sitemap, /path: '\/fund-truth-check'/);
  assert.match(tools, /title: 'Fund Truth Check'/);
  assert.match(tools, /badge: 'Private Beta'/);
});

test('Product Hunt referral points to the release page and badges require a real post identity', () => {
  assert.match(banner, /href="\/fund-truth-check"/);
  assert.match(home, /NEXT_PUBLIC_PRODUCT_HUNT_POST_ID/);
  assert.match(home, /NEXT_PUBLIC_PRODUCT_HUNT_POST_SLUG/);
  assert.doesNotMatch(home, /Featured on Product Hunt/);
  assert.match(badge, /postId: string/);
  assert.match(badge, /postSlug: string/);
  assert.match(badge, /post_id=\$\{postId\}/);
});

test('Product Hunt images are generated at usable gallery and thumbnail dimensions', () => {
  assert.match(gallery, /width: 1270, height: 760/);
  assert.match(gallery, /The useful answer is sometimes a stop sign/);
  assert.match(thumbnail, /width: 960, height: 960/);
  assert.match(thumbnail, /borderRight: '42px solid #00ff9d'/);
});
