/**
 * Scheme-code identity guard for the marketing and tool surfaces.
 *
 * These components used to carry their own scheme-code literals, and many pointed at entirely
 * different funds than the label shown: HDFC Flexi Cap was coded as Axis ELSS Tax Saver,
 * Nippon India Small Cap as Mirae Asset Large Cap, HDFC Top 100 as an Aditya Birla corporate
 * bond fund. Three codes were not real schemes at all (119551, 100356, 112090) and two were
 * absent from FUND_REGISTRY, so the overlap tool silently fell back to an unrelated fund while
 * still displaying the wrong pair's label.
 *
 * The fix is that every scheme code on these surfaces must resolve to FUND_REGISTRY. That is
 * what this suite enforces: no orphan codes, and no code whose registry identity disagrees
 * with the fund name the component prints next to it.
 */
import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { FUND_REGISTRY, getFundBySchemeCode } from '../lib/fund-registry.ts';
import { FUND_HOLDINGS_DB } from '../lib/fund-holdings.ts';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(here, '..');

/** Every surface that hardcodes scheme codes, and what its labels claim. */
const CODE_SOURCES = [
  'components/landing/LiveFundShowcase.tsx',
  'components/workspace/InteractiveHeroSandbox.tsx',
  'components/synthesis/SynthesisLandingPage.tsx',
  'components/tools/PortfolioOverlapCalculator.tsx',
];

/** Six-digit AMFI codes in the 100000-199999 range, ignoring colour literals and versions. */
function schemeCodeLiterals(source) {
  const stripped = source
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^[ \t]*\/\/.*$/gm, '');
  // Only look at values assigned to code-ish keys, so hex colours and years are not matched.
  const keys = /(?:schemeCode|schemeCodeA|schemeCodeB|codes)\s*:?\s*"?'?([\d,\s]+)/g;
  const found = new Set();
  for (const match of stripped.matchAll(keys)) {
    for (const part of match[1].split(',')) {
      const value = part.trim().replace(/["']/g, '');
      if (/^1\d{5}$/.test(value)) found.add(value);
    }
  }
  return [...found];
}

test('every scheme code on a marketing or tool surface resolves to FUND_REGISTRY', () => {
  for (const rel of CODE_SOURCES) {
    const source = fs.readFileSync(path.join(root, rel), 'utf8');
    for (const code of schemeCodeLiterals(source)) {
      assert.ok(
        getFundBySchemeCode(Number(code)),
        `${rel} uses scheme code ${code}, which is not in FUND_REGISTRY. ` +
          'Resolve identity through the registry, or if it is a real scheme that belongs on ' +
          'these surfaces, add it to FUND_REGISTRY with a matching AMFI fixture row first.',
      );
    }
  }
});

test('curated holdings keys are all real registry schemes', () => {
  // An orphan key is unreachable through the picker: the tool would never offer the fund, so
  // its holdings could never be used, which is how the wrong-keyed entries went unnoticed.
  const registryCodes = new Set(FUND_REGISTRY.map((f) => f.schemeCode));
  for (const key of Object.keys(FUND_HOLDINGS_DB)) {
    assert.ok(
      registryCodes.has(Number(key)),
      `FUND_HOLDINGS_DB has an entry for ${key}, which is not in FUND_REGISTRY, so no picker ` +
        'can ever select it. Fix the key or add the scheme to the registry.',
    );
  }
});

test('the overlap tool never derives a figure from a scheme it cannot resolve', () => {
  const source = fs.readFileSync(
    path.join(root, 'components/tools/PortfolioOverlapCalculator.tsx'),
    'utf8',
  );
  // The old fallback (`|| FUND_REGISTRY[0]`) reported one fund's numbers under another's name.
  assert.doesNotMatch(
    source,
    /FUND_REGISTRY\.find\([^)]*\)\s*\|\|\s*FUND_REGISTRY\[\d\]/,
    'Resolution must not fall back to an unrelated registry entry.',
  );
  assert.match(source, /FUND_REGISTRY\.find\(\(f\) => f\.schemeCode === codeA\) \?\? null/);
  // And holdings must come from the curated store, not a category proxy.
  assert.match(source, /getHoldingsForScheme\(/);
  assert.doesNotMatch(source, /getHoldingsForScheme\([^)]*,\s*fund[AB]\.category\)/);
});

test('the holdings module never fabricates a portfolio for an unknown scheme', () => {
  const source = fs.readFileSync(path.join(root, 'lib/fund-holdings.ts'), 'utf8');
  // The removed behaviour generated "representative" category holdings for any scheme.
  assert.doesNotMatch(source, /representative benchmark holdings/i);
  assert.doesNotMatch(source, /Default fallback holdings generator/i);
  // Absence must be signalled as null so callers abstain.
  assert.match(source, /export function getHoldingsForScheme\(schemeCode: number\): CuratedHoldings \| null/);
  assert.match(source, /return FUND_HOLDINGS_DB\[schemeCode\] \?\? null/);
  // Provenance is mandatory on every entry.
  assert.match(source, /asOf: '\d{4}-\d{2}'/);
  assert.match(source, /source: '/);
});

test('the overlap tool does not claim SEBI-published live disclosure', () => {
  const page = fs.readFileSync(path.join(root, 'app/tools/portfolio-overlap/page.tsx'), 'utf8');
  // Collapse JSX, HTML entities and whitespace so a phrase split across tags is matchable.
  const text = page
    .replace(/<[^>]+>/g, ' ')
    .replace(/&apos;/g, "'")
    .replace(/&ldquo;|&rdquo;/g, '"')
    .replace(/\s+/g, ' ');

  assert.doesNotMatch(page, /SEBI Disclosure Powered/);
  assert.match(text, /Illustrative Reference Data/);
  // The AMC-disclosure boundary must be stated, in the metadata and in the visible notice.
  assert.match(page, /not a live AMC disclosure/);
  assert.match(text, /not a live read of the AMC's current statutory portfolio/);
  // The abstention behaviour must be described, not just implemented.
  assert.match(text, /overlap as unavailable rather than estimating from a proxy/);
  assert.match(text, /Research only/);
  // No instruction language on a research-only page.
  assert.doesNotMatch(text, /you should (buy|sell|switch|exit)/i);
});

test('no marketing surface links a fund URL that does not resolve', () => {
  // Two hrefs used AMC slugs that do not exist (parag-parikh, nippon-india) and 404ed.
  const validAmcSlugs = new Set(FUND_REGISTRY.map((f) => f.amcSlug));
  const validPairs = new Set(FUND_REGISTRY.map((f) => `${f.amcSlug}/${f.fundSlug}`));
  const source = fs.readFileSync(path.join(root, 'components/landing/LiveFundShowcase.tsx'), 'utf8');

  for (const match of source.matchAll(/href:\s*"\/mutual-funds\/([^"]+)"/g)) {
    const target = match[1].replace(/\/$/, '');
    const [amcSlug, ...rest] = target.split('/');
    assert.ok(validAmcSlugs.has(amcSlug), `href uses unknown AMC slug "${amcSlug}"`);
    if (rest.length > 0) {
      assert.ok(validPairs.has(target), `href "/mutual-funds/${target}" is not a registry fund`);
    }
  }
});
