import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import test from 'node:test';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const ts = require('typescript');
const Module = require('module');

function loadTokenBudgetModule() {
  const filename = resolve('lib/billing/tokenBudgets.ts');
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
    mod.filename = childFilename;
    mod.paths = Module._nodeModulePaths(dirname(childFilename));
    mod._compile(output, childFilename);
  };
  delete require.cache[filename];
  const loaded = require(filename);
  Module._extensions['.ts'] = previous;
  return loaded;
}

test('token budget config gives each tier the configured daily and monthly budget', () => {
  delete process.env.TOKEN_BUDGET_FREE_DAILY;
  delete process.env.TOKEN_BUDGET_FREE_MONTHLY;
  delete process.env.TOKEN_BUDGET_PRO_DAILY;
  delete process.env.TOKEN_BUDGET_PRO_MONTHLY;
  delete process.env.TOKEN_BUDGET_ULTRA_DAILY;
  delete process.env.TOKEN_BUDGET_ULTRA_MONTHLY;

  const budgets = loadTokenBudgetModule();
  assert.deepEqual(budgets.getTokenBudget('free'), { dailyTokens: 25_000, monthlyTokens: 100_000 });
  assert.deepEqual(budgets.getTokenBudget('pro'), { dailyTokens: 250_000, monthlyTokens: 2_000_000 });
  assert.deepEqual(budgets.getTokenBudget('ultra'), { dailyTokens: 750_000, monthlyTokens: 6_000_000 });
  assert.deepEqual(budgets.getTokenBudget('free', 'admin'), { dailyTokens: 750_000, monthlyTokens: 6_000_000 });
});

test('token estimation uses prompt characters plus completion reserve', () => {
  process.env.TOKEN_ESTIMATE_CHARS_PER_TOKEN = '4';
  process.env.TOKEN_COMPLETION_RESERVE_TOKENS = '1500';

  const budgets = loadTokenBudgetModule();
  const body = { query: 'abcdabcd', history: [{ role: 'user', content: 'abcd' }] };
  const expected = Math.ceil(JSON.stringify(body).length / 4) + 1500;
  assert.equal(budgets.estimateChatTokens(body), expected);
});

test('chat route reserves tokens, forwards trusted headers, and strips backend usage', () => {
  const route = readFileSync(resolve('app/api/chat/route.ts'), 'utf8');
  assert.match(route, /reserveAiTokens/);
  assert.match(route, /token_budget_exceeded/);
  assert.match(route, /X-Internal-Proxy-Key/);
  assert.match(route, /delete data\._usage/);
  assert.match(route, /finalizeAiUsage/);
});

test('AI usage admin route reads actual ai_usage_events only', () => {
  const route = readFileSync(resolve('app/api/admin/ai-usage/route.ts'), 'utf8');
  assert.match(route, /from\('ai_usage_events'\)/);
  assert.match(route, /token_mode: 'actual'/);
  assert.doesNotMatch(route, /from\('provider_usage_logs'\)/);
  assert.doesNotMatch(route, /token_mode: 'proxy'/);
});

test('migration creates ai usage event table and reservation RPC', () => {
  const migration = readFileSync(resolve('../backend/migrations/20260612_add_ai_usage_events.sql'), 'utf8');
  assert.match(migration, /create table if not exists public\.ai_usage_events/);
  assert.match(migration, /user_id uuid not null/);
  assert.match(migration, /prompt_tokens integer/);
  assert.match(migration, /completion_tokens integer/);
  assert.match(migration, /total_tokens integer/);
  assert.match(migration, /create or replace function public\.reserve_ai_tokens/);
  assert.match(migration, /ai_usage_events_user_created_idx/);
  assert.match(migration, /ai_usage_events_tier_created_idx/);
});
