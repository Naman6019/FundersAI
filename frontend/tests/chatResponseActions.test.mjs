import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import test from 'node:test';

test('fund chat answers keep provenance labels visible with shared read-only actions', () => {
  const chat = readFileSync(resolve('components/chat/ChatWindow.tsx'), 'utf8');
  const healthHook = readFileSync(resolve('hooks/useDataHealth.ts'), 'utf8');
  const statusLabel = readFileSync(resolve('components/data-health/StatusLabel.tsx'), 'utf8');

  assert.match(chat, /label="As of"/);
  assert.match(chat, /Why is this lagging\?/);
  assert.match(chat, /Refresh data status/);
  assert.match(chat, /Find official evidence/);
  assert.match(chat, /useDataHealthContext/);
  assert.match(healthHook, /fetch\('\/api\/data-health'/);
  assert.match(statusLabel, /onMouseEnter|onFocus|onClick|event\.key === 'Escape'/);
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

test('claim sources render immediately after the answer and before other trust panels', () => {
  const chat = readFileSync(resolve('components/chat/ChatWindow.tsx'), 'utf8');
  const markdownAt = chat.indexOf('<ReactMarkdown');
  const sourcesAt = chat.indexOf('<ResponseSources', markdownAt);
  const actionsAt = chat.indexOf('<FundAnswerActions', sourcesAt);
  const reasoningAt = chat.indexOf('<ReasoningSummary', sourcesAt);

  assert.ok(markdownAt >= 0 && sourcesAt > markdownAt);
  assert.ok(actionsAt > sourcesAt);
  assert.ok(reasoningAt > sourcesAt);
});
