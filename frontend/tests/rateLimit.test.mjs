import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import test from 'node:test';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const ts = require('typescript');
const Module = require('module');

function loadRateLimitModule() {
  const filename = resolve('lib/rateLimit.ts');
  const previous = Module._extensions['.ts'];
  Module._extensions['.ts'] = (mod, childFilename) => {
    const source = readFileSync(childFilename, 'utf8');
    const output = ts.transpileModule(source, {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        target: ts.ScriptTarget.ES2022,
        esModuleInterop: true,
      },
    }).outputText;
    mod._compile(output, childFilename);
  };
  delete require.cache[filename];
  const loaded = require(filename);
  Module._extensions['.ts'] = previous;
  return loaded;
}

function requestFor(ip) {
  return new Request('https://fundersai.test/api/chat', {
    headers: {
      'x-forwarded-for': ip,
    },
  });
}

test('free chat limit blocks after the day bucket is exhausted', async () => {
  process.env.NODE_ENV = 'test';
  delete process.env.UPSTASH_REDIS_REST_URL;
  delete process.env.UPSTASH_REDIS_REST_TOKEN;
  const limiter = loadRateLimitModule();
  limiter.resetRateLimitMemoryForTests();

  for (let i = 0; i < 10; i += 1) {
    const result = await limiter.checkRateLimit(requestFor('203.0.113.10'), 'chat', {
      nowMs: 1000 + i * 61000,
      tier: 'free',
    });
    assert.equal(result.allowed, true);
  }

  const blocked = await limiter.checkRateLimit(requestFor('203.0.113.10'), 'chat', {
    nowMs: 1000 + 10 * 61000,
    tier: 'free',
  });
  assert.equal(blocked.allowed, false);

  const response = limiter.rateLimitResponse(blocked);
  assert.equal(response.status, 429);
  assert.equal((await response.json()).error, 'rate_limited');
});

test('paid tiers use higher chat buckets', async () => {
  process.env.NODE_ENV = 'test';
  delete process.env.UPSTASH_REDIS_REST_URL;
  delete process.env.UPSTASH_REDIS_REST_TOKEN;
  const limiter = loadRateLimitModule();
  limiter.resetRateLimitMemoryForTests();

  const pro = await limiter.checkRateLimit(requestFor('203.0.113.13'), 'chat', { nowMs: 1000, tier: 'pro' });
  assert.equal(pro.allowed, true);
  assert.equal(pro.limit, 10);

  const ultra = await limiter.checkRateLimit(requestFor('203.0.113.14'), 'chat', { nowMs: 1000, tier: 'ultra' });
  assert.equal(ultra.allowed, true);
  assert.equal(ultra.limit, 30);

  const admin = await limiter.checkRateLimit(requestFor('203.0.113.15'), 'chat', { nowMs: 1000, tier: 'free', role: 'admin' });
  assert.equal(admin.allowed, true);
  assert.equal(admin.limit, 30);
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
  assert.equal(quant.remaining, 19);
});

test('category fund browsing does not consume chat buckets', async () => {
  process.env.NODE_ENV = 'test';
  const limiter = loadRateLimitModule();
  limiter.resetRateLimitMemoryForTests();

  for (let i = 0; i < 6; i += 1) {
    const result = await limiter.checkRateLimit(requestFor('203.0.113.16'), 'category-funds', {
      nowMs: 1000,
      tier: 'free',
    });
    assert.equal(result.allowed, true);
  }

  const chat = await limiter.checkRateLimit(requestFor('203.0.113.16'), 'chat', {
    nowMs: 1000,
    tier: 'free',
  });
  assert.equal(chat.allowed, true);
  assert.equal(chat.remaining, 4);
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
