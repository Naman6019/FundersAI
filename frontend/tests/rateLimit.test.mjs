import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const ts = require('typescript');
const Module = require('module');

function loadRateLimitModule() {
  const filename = resolve('lib/rateLimit.ts');
  const source = readFileSync(filename, 'utf8');
  const output = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      esModuleInterop: true,
    },
  }).outputText;
  const mod = new Module(filename);
  mod.filename = filename;
  mod.paths = Module._nodeModulePaths(dirname(filename));
  mod._compile(output, filename);
  return mod.exports;
}

function requestFor(ip) {
  return new Request('https://fundersai.test/api/chat', {
    headers: {
      'x-forwarded-for': ip,
    },
  });
}

test('chat limit blocks after the minute bucket is exhausted', async () => {
  process.env.NODE_ENV = 'test';
  delete process.env.UPSTASH_REDIS_REST_URL;
  delete process.env.UPSTASH_REDIS_REST_TOKEN;
  const limiter = loadRateLimitModule();
  limiter.resetRateLimitMemoryForTests();

  for (let i = 0; i < 10; i += 1) {
    const result = await limiter.checkRateLimit(requestFor('203.0.113.10'), 'chat', { nowMs: 1000 });
    assert.equal(result.allowed, true);
  }

  const blocked = await limiter.checkRateLimit(requestFor('203.0.113.10'), 'chat', { nowMs: 1000 });
  assert.equal(blocked.allowed, false);
  assert.equal(blocked.retryAfterSeconds, 59);

  const response = limiter.rateLimitResponse(blocked);
  assert.equal(response.status, 429);
  assert.equal(response.headers.get('Retry-After'), '59');
  assert.equal((await response.json()).error, 'rate_limited');
});

test('route groups use separate buckets', async () => {
  process.env.NODE_ENV = 'test';
  const limiter = loadRateLimitModule();
  limiter.resetRateLimitMemoryForTests();

  for (let i = 0; i < 11; i += 1) {
    await limiter.checkRateLimit(requestFor('203.0.113.11'), 'chat', { nowMs: 1000 });
  }

  const quant = await limiter.checkRateLimit(requestFor('203.0.113.11'), 'quant', { nowMs: 1000 });
  assert.equal(quant.allowed, true);
  assert.equal(quant.remaining, 59);
});

test('production without Upstash config fails closed', async () => {
  process.env.NODE_ENV = 'production';
  delete process.env.UPSTASH_REDIS_REST_URL;
  delete process.env.UPSTASH_REDIS_REST_TOKEN;
  const limiter = loadRateLimitModule();
  limiter.resetRateLimitMemoryForTests();

  const result = await limiter.checkRateLimit(requestFor('203.0.113.12'), 'search', { nowMs: 1000 });
  assert.equal(result.allowed, false);
  assert.equal(result.configured, false);

  const response = limiter.rateLimitResponse(result);
  assert.equal(response.status, 503);
  assert.equal((await response.json()).error, 'rate_limit_unconfigured');
});
