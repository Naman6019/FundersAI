import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import test from 'node:test';

test('fund chat answers keep provenance and trust actions visible', () => {
  const chat = readFileSync(resolve('components/chat/ChatWindow.tsx'), 'utf8');

  assert.match(chat, /As of:/);
  assert.match(chat, /Why is this lagging\?/);
  assert.match(chat, /Refresh data status/);
  assert.match(chat, /Find official evidence/);
  assert.match(chat, /fetch\('\/api\/data-health', \{ cache: 'no-store' \}\)/);
  assert.match(chat, /never starts ingestion or a sync/);
  assert.doesNotMatch(chat, /fetch\('\/api\/cron\/sync-mf/);
});

test('official research citations are linked per claim and remain persisted', () => {
  const chat = readFileSync(resolve('components/chat/ChatWindow.tsx'), 'utf8');
  const route = readFileSync(resolve('app/api/chat/route.ts'), 'utf8');

  assert.match(chat, /responseWithCitationLinks/);
  assert.match(chat, /Claim sources/);
  assert.match(chat, /claim_validation: data\.claim_validation/);
  assert.match(route, /claim_validation: data\.claim_validation/);
  assert.match(route, /as_of: data\.as_of/);
  assert.match(route, /lag_details: data\.lag_details/);
});
