import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import vm from 'node:vm';
import test from 'node:test';

const require = createRequire(import.meta.url);
const ts = require('typescript');
const source = readFileSync(new URL('../components/truth-check/claimAutopsy.ts', import.meta.url), 'utf8');
const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
const sandbox = { exports: {}, require: (name) => { throw new Error(`Unexpected module: ${name}`); } };
vm.runInNewContext(code, sandbox);
const helper = sandbox.exports;

function claim(overrides = {}) {
  return {
    statement: 'HDFC Flexi Cap has a higher 3-year CAGR than Parag Parikh Flexi Cap.',
    metric: 'cagr',
    operator: 'higher_than',
    status: 'evaluated',
    verdict: 'supported',
    freshness: 'stale',
    values: {
      'HDFC Flexi Cap': { value: 17.640344, as_of_date: '2026-08-21' },
      'Parag Parikh Flexi Cap': { value: 14.390639, as_of_date: '2026-08-21' },
    },
    evidence: [{ source_name: 'AMFI NAV History', as_of_date: '2026-08-21' }],
    limitations: [],
    clarification: null,
    trackable: true,
    ...overrides,
  };
}

test('comparison explanation is deterministic and names both displayed values', () => {
  const input = claim();
  const rows = helper.extractAutopsyRows(input);
  const explanation = helper.buildExplanation(input, rows);
  const rule = helper.comparisonRule(input, rows);

  assert.match(explanation, /17\.64% for HDFC Flexi Cap/);
  assert.match(explanation, /14\.391% for Parag Parikh Flexi Cap/);
  assert.match(explanation, /greater than/);
  assert.equal(rule.rule, '17.64% > 14.391%');
  assert.equal(rule.difference, '3.25 percentage points');
});

test('stale verdict and lookup wording never imply present-day proof', () => {
  assert.equal(helper.verdictTitle(claim()), 'Supported for the cited period');
  assert.equal(helper.verdictTitle(claim({ operator: 'is' })), 'Value found in the cited evidence');
  assert.match(helper.freshnessMessage(claim()), /today's relationship is not confirmed/);
  assert.match(helper.freshnessMessage(claim()), /data is as of 21 Aug 2026/);
});

test('clarification exposes the deterministic prompt instead of inventing a rationale', () => {
  const input = claim({
    status: 'clarification_required',
    verdict: 'unverifiable',
    freshness: 'unknown',
    values: {},
    evidence: [],
    clarification: { reason: 'subjective', prompt: 'What does safer mean here?', choices: ['volatility'] },
  });
  assert.equal(helper.buildExplanation(input, []), 'What does safer mean here?');
  assert.equal(helper.verdictTitle(input), 'A definition is needed');
});
