/**
 * AMFI scheme-code identity guard.
 *
 * A mutual fund is identified by its AMFI scheme code, not by its name: names
 * change under SEBI re-categorisation and codes get transposed easily. This
 * suite pins every scheme code the app ships to the identity AMFI publishes for
 * it (tests/fixtures/amfi-scheme-identity.json, captured verbatim from
 * https://portal.amfiindia.com/spages/NAVAll.txt), so a wrong code fails CI
 * instead of quietly showing one fund's data under another fund's name.
 *
 * It also enforces that FUND_REGISTRY is the ONLY place scheme codes are
 * written down: the fund pickers and the supported-funds fallback must resolve
 * through the registry rather than carrying their own literals.
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  FUND_REGISTRY,
  POPULAR_FUND_SLUGS,
  getPopularFunds,
  getPeerFunds,
  getFundsGroupedByAmc,
} from '../lib/fund-registry.ts';

const here = path.dirname(fileURLToPath(import.meta.url));
const fixture = JSON.parse(
  fs.readFileSync(path.join(here, 'fixtures', 'amfi-scheme-identity.json'), 'utf8'),
);

/**
 * AMFI's own strings are inconsistently cased and sometimes carry an
 * "(erstwhile ...)" suffix during a rename window, so compare on a normalised
 * form rather than byte equality.
 */
function normaliseName(name) {
  return String(name)
    .toLowerCase()
    .replace(/\((?:erstwhile|formerly)[^)]*\)/g, '')
    .replace(/&/g, ' and ')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

test('fixture is a usable AMFI snapshot', () => {
  assert.match(fixture.source, /amfiindia\.com/);
  assert.match(fixture.capturedOn, /^\d{4}-\d{2}-\d{2}$/);
  assert.ok(Object.keys(fixture.schemes).length >= 20);
});

test('every FUND_REGISTRY scheme code matches the AMFI scheme master', () => {
  for (const fund of FUND_REGISTRY) {
    const amfi = fixture.schemes[String(fund.schemeCode)];
    assert.ok(
      amfi,
      `Scheme code ${fund.schemeCode} (${fund.schemeName}) is not in the AMFI fixture. ` +
        'Verify it against NAVAll.txt and add a fixture row — do not guess.',
    );
    assert.equal(
      normaliseName(fund.schemeName),
      normaliseName(amfi.amfiSchemeName),
      `Scheme code ${fund.schemeCode} is "${amfi.amfiSchemeName}" at AMFI, ` +
        `but the registry calls it "${fund.schemeName}".`,
    );
  }
});

test('registry entries are the Direct Plan / Growth Option line', () => {
  const undeclared = new Set(fixture.planOptionUndeclared ?? []);
  for (const fund of FUND_REGISTRY) {
    assert.equal(fund.plan, 'Direct');
    assert.equal(fund.option, 'Growth');

    const code = String(fund.schemeCode);
    const amfi = fixture.schemes[code];
    if (undeclared.has(code)) {
      // AMFI leaves Plan/Option blank for these rows; documented in the fixture.
      assert.equal(amfi.amfiPlan, null);
      continue;
    }
    assert.match(
      amfi.amfiPlan ?? '',
      /direct/i,
      `Scheme code ${fund.schemeCode} is not a Direct Plan at AMFI (${amfi.amfiPlan}).`,
    );
    assert.match(
      amfi.amfiOption ?? '',
      /growth/i,
      `Scheme code ${fund.schemeCode} is not a Growth option at AMFI (${amfi.amfiOption}).`,
    );
    assert.doesNotMatch(amfi.amfiOption ?? '', /idcw|dividend/i);
  }
});

test('renamed schemes record the former name and keep it distinct', () => {
  for (const fund of FUND_REGISTRY) {
    if (fund.formerName === undefined) continue;
    assert.ok(fund.formerName.length > 0, `Empty formerName on ${fund.schemeCode}`);
    assert.notEqual(
      normaliseName(fund.formerName),
      normaliseName(fund.schemeName),
      `formerName duplicates schemeName on ${fund.schemeCode}`,
    );
  }

  // Schemes AMFI still tags "(erstwhile X)" must carry a formerName.
  for (const fund of FUND_REGISTRY) {
    const amfiName = fixture.schemes[String(fund.schemeCode)].amfiSchemeName;
    if (/\(erstwhile/i.test(amfiName)) {
      assert.ok(
        fund.formerName,
        `AMFI marks ${fund.schemeCode} as renamed ("${amfiName}") but the registry has no formerName.`,
      );
    }
  }
});

test('fund slugs are unique so slug-based shortlists resolve unambiguously', () => {
  const slugs = new Set();
  for (const fund of FUND_REGISTRY) {
    assert.ok(!slugs.has(fund.fundSlug), `Duplicate fundSlug: ${fund.fundSlug}`);
    slugs.add(fund.fundSlug);
  }
});

test('derived shortlists resolve entirely through the registry', () => {
  const popular = getPopularFunds();
  assert.equal(
    popular.length,
    POPULAR_FUND_SLUGS.length,
    'POPULAR_FUND_SLUGS references a slug that is not in FUND_REGISTRY.',
  );
  for (const fund of popular) {
    assert.ok(fixture.schemes[String(fund.schemeCode)]);
  }

  const grouped = getFundsGroupedByAmc();
  assert.equal(
    grouped.reduce((n, g) => n + g.funds.length, 0),
    FUND_REGISTRY.length,
  );

  const subject = FUND_REGISTRY[0];
  const peers = getPeerFunds(subject.schemeCode, 3);
  assert.equal(peers.length, 3);
  for (const peer of peers) {
    assert.notEqual(peer.schemeCode, subject.schemeCode);
    assert.ok(fixture.schemes[String(peer.schemeCode)]);
  }
});

/**
 * Regression guard for the three files that used to keep their own scheme-code
 * lists (with codes that pointed at entirely different funds). They must read
 * from fund-registry instead of re-declaring literals.
 */
const REGISTRY_ONLY_SOURCES = [
  '../app/api/reports/supported-funds/route.ts',
  '../app/synthesis/generate/page.tsx',
  '../components/canvas/MFDetailView.tsx',
];

test('no module outside fund-registry hardcodes AMFI scheme codes', () => {
  for (const rel of REGISTRY_ONLY_SOURCES) {
    const file = path.join(here, rel);
    const source = fs.readFileSync(file, 'utf8');
    const stripped = source
      .replace(/\/\*[\s\S]*?\*\//g, '')
      .replace(/^[ \t]*\/\/.*$/gm, '');

    // AMFI scheme codes are 6-digit integers in the 100000-199999 range.
    const literals = stripped.match(/(?<![\d.])1\d{5}(?![\d.])/g) ?? [];
    assert.deepEqual(
      literals,
      [],
      `${rel} contains scheme-code literals ${literals.join(', ')}. ` +
        'Resolve fund identity through @/lib/fund-registry so it stays covered by this suite.',
    );
  }
});

test('the supported-funds fallback ships no fabricated performance figures', () => {
  const source = fs.readFileSync(
    path.join(here, '../app/api/reports/supported-funds/route.ts'),
    'utf8',
  );
  const fallback = source.slice(0, source.indexOf('export async function GET'));
  for (const field of ['return_3y', 'nav', 'expense_ratio']) {
    const literal = new RegExp(field + '\\s*:\\s*[\\d.]');
    assert.doesNotMatch(
      fallback,
      literal,
      `The offline fallback assigns a literal ${field}. Point-in-time figures must ` +
        'come from the live snapshot or be omitted and disclosed as unavailable.',
    );
  }
});
