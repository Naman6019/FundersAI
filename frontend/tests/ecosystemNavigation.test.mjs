import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const FRONTEND_ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));

const read = (...segments) => {
  const file = path.join(FRONTEND_ROOT, ...segments);
  assert.ok(existsSync(file), `${segments.join('/')} must exist`);
  return readFileSync(file, 'utf-8');
};

/**
 * Every surface must offer a way back to the ecosystem hub at `/`.
 *
 * The Synthesis silo is the hard case: middleware rewrites "/" to /synthesis on the
 * `synthesis.` subdomain, so a relative home link there lands the user back where they
 * started. These tests pin the escape hatches so the trap cannot quietly reappear.
 */

test('EcosystemHeader logo does not branch on the Synthesis surface', () => {
  const header = read('components', 'ecosystem', 'EcosystemHeader.tsx');

  assert.doesNotMatch(
    header,
    /isSynthesis\s*\?\s*"\/synthesis"\s*:\s*"\/"/,
    'the brand logo must not route back into /synthesis when inside Synthesis',
  );
  assert.match(
    header,
    /<Link href=\{homeHref\}/,
    'the brand logo must use the resolved ecosystem home href',
  );
});

test('EcosystemHeader resolves its home href off the subdomain', () => {
  const header = read('components', 'ecosystem', 'EcosystemHeader.tsx');
  const origin = read('lib', 'ecosystem-origin.ts');

  assert.match(header, /useEcosystemHref\(\)/);
  assert.match(header, /const homeHref = ecosystemHref\("\/"\)/);
  assert.match(
    origin,
    /hostname\.startsWith\(SYNTHESIS_PREFIX\)/,
    'link resolution must detect the synthesis subdomain, where "/" is rewritten to /synthesis',
  );
});

test('the Synthesis silo has a footer whose exits leave the subdomain', () => {
  const layout = read('app', 'synthesis', 'layout.tsx');
  const footer = read('components', 'synthesis', 'SynthesisFooter.tsx');

  assert.match(layout, /<SynthesisFooter \/>/, 'the synthesis layout must render a footer');

  // Every destination outside /synthesis must be resolved, or it becomes a duplicate URL
  // on the synthesis subdomain rather than a link back to www.
  assert.match(footer, /href=\{ecosystemHref\("\/"\)\}/, 'the footer must link home');
  assert.match(footer, /href=\{ecosystemHref\(link\.href\)\}/);

  const rawExternal = footer.match(/href="\/(?!synthesis)[a-z-]*"/g) ?? [];
  assert.deepEqual(
    rawExternal,
    [],
    `non-synthesis links must go through ecosystemHref, found: ${rawExternal.join(', ')}`,
  );
});

test('EcosystemHeader exposes an explicit Home affordance', () => {
  const header = read('components', 'ecosystem', 'EcosystemHeader.tsx');

  assert.match(
    header,
    /key: "home",[\s\S]{0,80}?label: "Home",[\s\S]{0,80}?href: homeHref,/,
    'the navigation must include a Home item pointing at the resolved hub',
  );
  assert.match(
    header,
    /name: "FundersAI Home", href: homeHref/,
    'the command palette must be able to reach the ecosystem hub',
  );
});

test('the dashboard sidebar logo links to the hub, not a remembered surface', () => {
  const sidebar = read('components', 'layout', 'AppSidebar.tsx');

  assert.match(sidebar, /<Link href="\/" className="group block/);
  assert.doesNotMatch(sidebar, /rememberedLanding/);
});

test('the volatile last-landing key is gone from every surface', () => {
  const files = [
    ['components', 'ecosystem', 'EcosystemHeader.tsx'],
    ['components', 'layout', 'AppSidebar.tsx'],
    ['components', 'auth', 'UserProfileDropdown.tsx'],
    ['components', 'synthesis', 'SynthesisLandingPage.tsx'],
    ['components', 'landing', 'PremiumLandingPage.jsx'],
  ];

  for (const segments of files) {
    assert.doesNotMatch(
      read(...segments),
      /fundersai_last_landing/,
      `${segments.join('/')} must not read or write the last-landing key`,
    );
  }
});

test('navigation labels name the surface they actually reach', () => {
  const dropdown = read('components', 'auth', 'UserProfileDropdown.tsx');
  const footer = read('components', 'layout', 'PublicFooter.tsx');

  // `/` is the ecosystem hub; `/research` is the research landing page.
  assert.match(dropdown, /<span>FundersAI Home<\/span>/);
  assert.doesNotMatch(dropdown, /Research Landing Page/);

  // The footer badge points at /dashboard, so it must not claim to be a research link.
  assert.doesNotMatch(footer, /← Back to Research/);
  assert.match(footer, /← Back to Workspace/);
  assert.match(footer, /<Link href="\/" className="flex items-center gap-3">/);
});

test('navigation is reachable below the desktop breakpoint', () => {
  const header = read('components', 'ecosystem', 'EcosystemHeader.tsx');

  // The switcher pill is lg-only, so sub-1024px viewports need their own affordance.
  assert.match(header, /aria-label="Open navigation menu"/);
  assert.match(header, /id="ecosystem-mobile-nav"/);
  assert.match(header, /aria-modal="true"/);
  assert.match(header, /aria-label="Close navigation menu"/);

  // Desktop pill and mobile drawer render from one list, so they cannot drift apart.
  const renders = header.match(/navItems\.map\(/g) ?? [];
  assert.equal(renders.length, 2, 'both navigations must render from navItems');
});

test('the mobile drawer honours the modality it declares', () => {
  const header = read('components', 'ecosystem', 'EcosystemHeader.tsx');

  // aria-modal promises assistive tech that focus is contained; these are the parts
  // that actually deliver it.
  assert.match(header, /ref=\{mobileNavTriggerRef\}/, 'the trigger needs a ref to restore focus to');
  assert.match(header, /ref=\{mobileNavRef\}/, 'the panel needs a ref to scope the focus trap');
  assert.match(header, /e\.key !== "Tab"/, 'Tab must be trapped inside the panel');
  assert.match(header, /requestAnimationFrame\(\(\) => trigger\?\.focus\(\)\)/);
  assert.match(header, /document\.body\.style\.overflow = "hidden"/);
});
