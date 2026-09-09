import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import vm from 'node:vm';
import test from 'node:test';

const require = createRequire(import.meta.url);
const ts = require('typescript');
const source = readFileSync(new URL('../app/api/funds/claim-monitor/route.ts', import.meta.url), 'utf8');
const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;

function harness({ enabled = true, authenticated = true, storageError = null, trackable = true } = {}) {
  const calls = [];
  class ClaimMonitorError extends Error {
    constructor(codeValue, status) {
      super(codeValue);
      this.code = codeValue;
      this.status = status;
    }
  }
  const claims = [{ id: 'claim-1', original_text: 'Claim', normalized_claim: {}, resolved_entities: [], active: true, created_at: '2026-09-06T00:00:00Z' }];
  const evaluations = [{ id: 'evaluation-1', claim_id: 'claim-1', verdict: 'supported', freshness: 'current', result: {}, evidence: [], source_fingerprint: 'a'.repeat(64), evaluated_at: '2026-09-06T01:00:00Z' }];

  const query = (table) => {
    const builder = {
      select() { return builder; },
      in() { return builder; },
      order() { return builder; },
      limit: async () => ({ data: table === 'research_claims' ? claims : evaluations, error: storageError }),
    };
    return builder;
  };
  const context = {
    user: { id: 'user-1' },
    profile: { tier: 'free', role: 'user' },
    supabaseUser: { from: (table) => { calls.push(`user:${table}`); return query(table); } },
    supabaseAdmin: {
      rpc: async (name, params) => {
        calls.push({ name, params });
        return { data: storageError ? null : '11111111-1111-4111-8111-111111111111', error: storageError };
      },
    },
  };
  const modules = {
    'next/server': { NextResponse: Response },
    '@/lib/auth/server': {
      requireUserContext: async () => {
        calls.push('auth');
        return authenticated ? { ok: true, context } : { ok: false, response: Response.json({ error: 'Unauthorized' }, { status: 401 }) };
      },
    },
    '@/lib/fundTruthCheckPrivate': { isFundTruthCheckPrivateEnabled: () => enabled },
    '@/lib/fundTruthMonitor': {
      ClaimMonitorError,
      fetchCanonicalClaimCheck: async (input) => { calls.push(`check:${input}`); return { input }; },
      buildClaimMonitorSnapshot: () => {
        if (!trackable) throw new ClaimMonitorError('claim_not_trackable', 422);
        return {
          normalizedClaim: { version: 1, claims: [] },
          resolvedEntities: [],
          verdict: 'supported',
          freshness: 'current',
          result: { input: 'canonical' },
          evidence: [{ source_fingerprint: 'a'.repeat(64) }],
          sourceFingerprint: 'b'.repeat(64),
        };
      },
    },
    '@/lib/rateLimit': {
      enforceRateLimit: async (_request, group) => { calls.push(group); return null; },
      getClientIp: () => '127.0.0.1',
    },
  };
  const sandbox = { exports: {}, require: (name) => modules[name], console: { error: () => {} } };
  vm.runInNewContext(code, sandbox);
  return { get: sandbox.exports.GET, post: sandbox.exports.POST, calls };
}

const getRequest = () => new Request('https://fundersai.test/api/funds/claim-monitor');
const postRequest = (body = { input: '  PPFAS Flexi Cap expense ratio  ' }) => new Request('https://fundersai.test/api/funds/claim-monitor', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

function assertPrivate(response) {
  assert.match(response.headers.get('cache-control'), /no-store/);
  assert.match(response.headers.get('x-robots-tag'), /noindex/);
}

test('disabled monitor returns 404 before authentication or storage access', async () => {
  const h = harness({ enabled: false });
  const response = await h.post(postRequest());
  assert.equal(response.status, 404);
  assert.deepEqual(h.calls, []);
  assertPrivate(response);
});

test('monitor requires authentication even before reading or saving', async () => {
  const h = harness({ authenticated: false });
  const response = await h.get(getRequest());
  assert.equal(response.status, 401);
  assert.deepEqual(h.calls, ['auth']);
  assertPrivate(response);
});

test('invalid save input is rejected before canonical evaluation', async () => {
  const h = harness();
  const response = await h.post(postRequest({ input: 'x' }));
  assert.equal(response.status, 400);
  assert.deepEqual(h.calls, ['auth', 'claim-monitor']);
});

test('untrackable canonical results are not persisted', async () => {
  const h = harness({ trackable: false });
  const response = await h.post(postRequest());
  assert.equal(response.status, 422);
  assert.deepEqual(h.calls, ['auth', 'claim-monitor', 'check:PPFAS Flexi Cap expense ratio']);
});

test('save persists the server-built snapshot through the atomic RPC', async () => {
  const h = harness();
  const response = await h.post(postRequest());
  const body = await response.json();
  assert.equal(response.status, 201);
  assert.equal(body.claim_id, '11111111-1111-4111-8111-111111111111');
  const rpc = h.calls.find((call) => typeof call === 'object');
  assert.equal(rpc.name, 'save_research_claim_with_evaluation');
  assert.equal(rpc.params.p_user_id, 'user-1');
  assert.equal(rpc.params.p_original_text, 'PPFAS Flexi Cap expense ratio');
  assert.equal(rpc.params.p_result.input, 'canonical');
  assertPrivate(response);
});

test('owned monitor reads use the bearer-scoped client and attach history', async () => {
  const h = harness();
  const response = await h.get(getRequest());
  const body = await response.json();
  assert.equal(response.status, 200);
  assert.deepEqual(h.calls, ['auth', 'claim-monitor', 'user:research_claims', 'user:research_claim_evaluations']);
  assert.equal(body.claims[0].latest_evaluation.id, 'evaluation-1');
  assert.equal(body.claims[0].evaluations.length, 1);
});

test('missing Phase 3 schema returns a generic storage-unavailable response', async () => {
  const h = harness({ storageError: { code: 'PGRST205' } });
  const response = await h.get(getRequest());
  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), { error: 'claim_monitor_storage_unavailable' });
  assertPrivate(response);
});
