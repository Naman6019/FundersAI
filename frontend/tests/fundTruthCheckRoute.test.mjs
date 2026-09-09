import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import vm from 'node:vm';
import test from 'node:test';

const require = createRequire(import.meta.url);
const ts = require('typescript');
const source = readFileSync(new URL('../app/api/funds/claim-check/route.ts', import.meta.url), 'utf8');
const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText;

function harness({ enabled = true, authenticated = true, authFailure = false, key = 'test-only', limited = null, backendStatus = 200 } = {}) {
  const calls = [];
  const modules = {
    'next/server': { NextResponse: Response },
    '@/lib/fundTruthCheckPrivate': { isFundTruthCheckPrivateEnabled: () => enabled },
    '@/lib/auth/server': { getUserContext: async () => {
      calls.push('auth');
      if (authFailure) throw new Error('private database detail');
      return authenticated ? { user: { id: 'reviewer' }, profile: { tier: 'free', role: 'user' } } : null;
    } },
    '@/lib/rateLimit': {
      getClientIp: () => '127.0.0.1',
      enforceRateLimit: async (_request, group) => { calls.push(group); return limited; },
    },
  };
  const sandbox = {
    exports: {}, require: (name) => modules[name],
    process: { env: { NODE_ENV: 'production', CLAIM_CHECK_INTERNAL_PROXY_KEY: key, BACKEND_API_URL: 'http://backend.test' } },
    console: { error: () => {} }, AbortSignal,
    fetch: async (url, options) => {
      calls.push({ url, options });
      return Response.json(backendStatus === 200 ? { claims: [] } : { secret: 'backend details' }, { status: backendStatus });
    },
  };
  vm.runInNewContext(code, sandbox);
  return { post: sandbox.exports.POST, calls };
}

const request = (body = '{"input":"  factual claim  ","untrusted":"ignored"}') => new Request('https://fundersai.test/api/funds/claim-check', { method: 'POST', body });
function privateHeaders(response) {
  assert.match(response.headers.get('cache-control'), /no-store/);
  assert.match(response.headers.get('x-robots-tag'), /noindex/);
}

test('disabled feature returns 404 before auth or downstream access', async () => {
  const h = harness({ enabled: false });
  const response = await h.post(request());
  assert.equal(response.status, 404);
  assert.deepEqual(h.calls, []);
  privateHeaders(response);
});

test('production anonymous and failed-auth requests never reach the backend', async () => {
  for (const [options, status] of [[{ authenticated: false }, 401], [{ authFailure: true }, 503]]) {
    const h = harness(options);
    const response = await h.post(request());
    assert.equal(response.status, status);
    assert.deepEqual(h.calls, ['auth']);
    privateHeaders(response);
    assert.doesNotMatch(await response.text(), /database detail/);
  }
});

test('malformed and out-of-range input is rejected before evaluation', async () => {
  for (const body of ['{', 'null', '{"input":1}', '{"input":"ab"}', JSON.stringify({ input: 'x'.repeat(2001) })]) {
    const h = harness();
    const response = await h.post(request(body));
    assert.equal(response.status, 400);
    assert.deepEqual(h.calls, ['auth']);
    privateHeaders(response);
  }
});

test('rate limit denial retains retry and privacy headers without forwarding', async () => {
  const h = harness({ limited: Response.json({ error: 'rate_limited' }, { status: 429, headers: { 'Retry-After': '60' } }) });
  const response = await h.post(request());
  assert.equal(response.status, 429);
  assert.equal(response.headers.get('retry-after'), '60');
  assert.deepEqual(h.calls, ['auth', 'claim-check']);
  privateHeaders(response);
});

test('missing proxy secret fails closed', async () => {
  const h = harness({ key: '' });
  const response = await h.post(request());
  assert.equal(response.status, 503);
  assert.deepEqual(h.calls, ['auth', 'claim-check']);
  privateHeaders(response);
});

test('authorized check forwards normalized input only and keeps the secret server-side', async () => {
  const h = harness();
  const response = await h.post(request());
  assert.equal(response.status, 200);
  const forwarded = h.calls[2];
  assert.equal(forwarded.url, 'http://backend.test/api/funds/claim-check');
  assert.equal(forwarded.options.headers['X-Internal-Proxy-Key'], 'test-only');
  assert.deepEqual(JSON.parse(forwarded.options.body), { input: 'factual claim' });
  assert.doesNotMatch(await response.text(), /test-only/);
  privateHeaders(response);
});

test('backend error details are not returned to the browser', async () => {
  const h = harness({ backendStatus: 500 });
  const response = await h.post(request());
  assert.equal(response.status, 502);
  assert.doesNotMatch(await response.text(), /backend details/);
  privateHeaders(response);
});
