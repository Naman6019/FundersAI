import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import vm from 'node:vm';
import test from 'node:test';

const require = createRequire(import.meta.url);
const ts = require('typescript');
const read = (relativePath) => readFileSync(new URL(relativePath, import.meta.url), 'utf8');
const helperSource = read('../lib/fundTruthMonitor.ts');
const helperCode = ts.transpileModule(helperSource, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;

function loadHelper(key = 'internal-monitor-key') {
  const sandbox = {
    exports: {},
    require: (name) => {
      if (name === 'server-only') return {};
      if (name === 'node:crypto') return require('node:crypto');
      throw new Error(`Unexpected module: ${name}`);
    },
    process: { env: { CLAIM_MONITOR_INTERNAL_KEY: key } },
    Buffer,
    AbortSignal,
    fetch,
  };
  vm.runInNewContext(helperCode, sandbox);
  return sandbox.exports;
}

function result({ verdicts = ['supported'], freshness = ['current'], trackable = true } = {}) {
  return {
    input: 'HDFC Flexi Cap has a higher CAGR than PPFAS Flexi Cap.',
    generated_at: '2026-09-06T12:00:00Z',
    resolved_entities: [
      { input: 'HDFC Flexi Cap', scheme_code: '118955', scheme_name: 'HDFC Flexi Cap', amc_name: 'HDFC', confidence: 1, resolution_status: 'supported', candidates: [] },
      { input: 'PPFAS Flexi Cap', scheme_code: '122639', scheme_name: 'PPFAS Flexi Cap', amc_name: 'PPFAS', confidence: 1, resolution_status: 'supported', candidates: [] },
    ],
    claims: verdicts.map((verdict, index) => ({
      statement: `Atomic claim ${index + 1}`,
      metric: index === 0 ? 'cagr' : 'expense_ratio',
      operator: 'higher_than',
      status: 'evaluated',
      verdict,
      freshness: freshness[index] || freshness[0],
      values: { left: 1, right: 2 },
      evidence: [{
        source_type: index === 0 ? 'amfi_nav' : 'official_amc_document',
        source_name: 'Official source',
        source_url: 'https://example.com/source',
        document_id: null,
        as_of_date: '2026-09-05',
        source_fingerprint: `${index + 1}`.repeat(64),
      }],
      limitations: [],
      clarification: null,
      trackable,
    })),
  };
}

test('monitor snapshot is deterministic and aggregates atomic verdicts and freshness', () => {
  const helper = loadHelper();
  const response = result({ verdicts: ['supported', 'contradicted'], freshness: ['current', 'stale'] });
  const first = helper.buildClaimMonitorSnapshot(response);
  const second = helper.buildClaimMonitorSnapshot(structuredClone(response));
  const wordingOnlyChange = structuredClone(response);
  wordingOnlyChange.claims[0].statement = 'Reworded atomic claim';
  wordingOnlyChange.claims[0].operator = 'lower_than';
  const reworded = helper.buildClaimMonitorSnapshot(wordingOnlyChange);

  assert.equal(first.verdict, 'mixed');
  assert.equal(first.freshness, 'stale');
  assert.equal(first.sourceFingerprint, second.sourceFingerprint);
  assert.equal(first.sourceFingerprint, reworded.sourceFingerprint);
  assert.match(first.sourceFingerprint, /^[a-f0-9]{64}$/);
  assert.deepEqual(Array.from(first.normalizedClaim.claims[0].source_scopes), ['nav']);
  assert.deepEqual(Array.from(first.normalizedClaim.claims[1].source_scopes), ['core']);
  assert.equal(first.evidence.length, 2);
});

test('a claim without deterministic fingerprinted evidence cannot be saved initially', () => {
  const helper = loadHelper();
  assert.throws(
    () => helper.buildClaimMonitorSnapshot(result({ trackable: false })),
    (error) => error.code === 'claim_not_trackable' && error.status === 422,
  );
});

test('source-change matching requires the same scheme, relevant scope, and a new fingerprint', () => {
  const helper = loadHelper();
  const snapshot = helper.buildClaimMonitorSnapshot(result());
  const oldFingerprint = snapshot.evidence[0].source_fingerprint;
  const change = (scheme_code, scope, source_fingerprint) => [{ scheme_code, scope, source_fingerprint }];

  assert.equal(helper.claimAffectedBySourceChanges(snapshot.normalizedClaim, snapshot.resolvedEntities, snapshot.evidence, change('118955', 'nav', 'a'.repeat(64))), true);
  assert.equal(helper.claimAffectedBySourceChanges(snapshot.normalizedClaim, snapshot.resolvedEntities, snapshot.evidence, change('118955', 'core', 'a'.repeat(64))), false);
  assert.equal(helper.claimAffectedBySourceChanges(snapshot.normalizedClaim, snapshot.resolvedEntities, snapshot.evidence, change('999999', 'nav', 'a'.repeat(64))), false);
  assert.equal(helper.claimAffectedBySourceChanges(snapshot.normalizedClaim, snapshot.resolvedEntities, snapshot.evidence, change('118955', 'nav', oldFingerprint)), false);
});

test('internal source-change key comparison fails closed', () => {
  const helper = loadHelper();
  assert.equal(helper.trustedClaimMonitorKey('internal-monitor-key'), true);
  assert.equal(helper.trustedClaimMonitorKey('wrong'), false);
  assert.equal(loadHelper('').trustedClaimMonitorKey('anything'), false);
});

test('migration enforces ownership, atomic initial save, and append-only evaluation access', () => {
  const migration = read('../../backend/migrations/20260906_add_research_claim_monitor.sql');
  assert.match(migration, /CREATE TABLE IF NOT EXISTS public\.research_claims/);
  assert.match(migration, /CREATE TABLE IF NOT EXISTS public\.research_claim_evaluations/);
  assert.match(migration, /ALTER TABLE public\.research_claims ENABLE ROW LEVEL SECURITY/);
  assert.match(migration, /research_claims\.user_id = \(SELECT auth\.uid\(\)\)/);
  assert.match(migration, /GRANT UPDATE \(active\) ON public\.research_claims TO authenticated/);
  assert.match(migration, /UNIQUE \(claim_id, source_fingerprint\)/);
  assert.match(migration, /save_research_claim_with_evaluation/);
  assert.match(migration, /FROM PUBLIC, anon, authenticated/);
  assert.match(migration, /GRANT SELECT, INSERT ON public\.research_claim_evaluations TO service_role/);
  assert.doesNotMatch(migration, /GRANT (?:ALL|UPDATE|DELETE)[^;]*research_claim_evaluations TO (?:authenticated|service_role)/);
});

test('private monitor routes keep canonical evaluation and source-trigger boundaries', () => {
  const monitorRoute = read('../app/api/funds/claim-monitor/route.ts');
  const itemRoute = read('../app/api/funds/claim-monitor/[claimId]/route.ts');
  const sourceRoute = read('../app/api/internal/funds/claim-monitor/source-change/route.ts');
  const panel = read('../components/truth-check/ThesisMonitorPanel.tsx');

  assert.match(monitorRoute, /isFundTruthCheckPrivateEnabled\(\)/);
  assert.match(monitorRoute, /requireUserContext\(request\)/);
  assert.match(monitorRoute, /fetchCanonicalClaimCheck\(input/);
  assert.match(monitorRoute, /save_research_claim_with_evaluation/);
  assert.match(itemRoute, /\.update\(\{ active:/);
  assert.doesNotMatch(itemRoute, /\.delete\(/);
  assert.match(sourceRoute, /trustedClaimMonitorKey/);
  assert.match(sourceRoute, /claimAffectedBySourceChanges/);
  assert.match(sourceRoute, /bypassCache: true/);
  assert.match(sourceRoute, /snapshot\.sourceFingerprint === claim\.latest_source_fingerprint/);
  assert.doesNotMatch(sourceRoute, /schedule|setInterval|cron/i);
  assert.match(panel, /Save this claim/);
  assert.match(panel, /Evaluation history/);
  assert.match(panel, /Monitoring paused\. Existing history was preserved/);
  assert.doesNotMatch(panel, /setInterval|Notification/);
});
