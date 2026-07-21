import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

test('chat input exposes asset, explanation, and comparison controls', () => {
  const source = readFileSync(new URL('../components/chat/ChatWindow.tsx', import.meta.url), 'utf8');

  for (const label of ["'Auto'", "'Stocks'", "'Funds'", "'Beginner'", "'Advanced'", "'Canvas'", "'Chat'"]) {
    assert.match(source, new RegExp(label.replace(/[']/g, "\\'")));
  }
  assert.match(source, /setComparisonViewMode\(option\.value as ComparisonViewMode\)/);
  assert.match(source, /setResearchDepth\(nextMode === 'advanced' \? 'deep' : 'standard'\)/);
});

test('chat renders a collapsed reasoning summary without raw model thinking', () => {
  const source = readFileSync(new URL('../components/chat/ChatWindow.tsx', import.meta.url), 'utf8');

  assert.match(source, /function ReasoningSummary/);
  assert.match(source, /metadata\?\.reasoning_summary/);
  assert.match(source, /<summary[^>]*>\s*Reasoning summary\s*<\/summary>/);
  assert.match(source, /reasoning_summary: data\.reasoning_summary \|\| null/);
  assert.doesNotMatch(source, /Model Thinking/);
  assert.doesNotMatch(source, /thinkMatch/);
});

test('chat proxy persists reasoning-summary metadata', () => {
  const source = readFileSync(new URL('../app/api/chat/route.ts', import.meta.url), 'utf8');

  assert.match(source, /reasoning_summary: data\.reasoning_summary \|\| null/);
});

test('chat proxy returns the persisted assistant message id for response feedback', () => {
  const proxy = readFileSync(new URL('../app/api/chat/route.ts', import.meta.url), 'utf8');
  const stream = readFileSync(new URL('../lib/chatStream.ts', import.meta.url), 'utf8');

  assert.match(proxy, /\.insert\(rowsWithSession\)\s*\.select\('id,role'\)/);
  assert.match(proxy, /response_message_id = responseMessageId/);
  assert.match(stream, /response_message_id\?: string/);
});

test('chat schema migration defines owned sessions and messages', () => {
  const migration = readFileSync(
    new URL('../../backend/migrations/20260721_add_ai_chat_sessions_and_messages.sql', import.meta.url),
    'utf8',
  );

  assert.match(migration, /create table if not exists public\.ai_chat_sessions/);
  assert.match(migration, /create table if not exists public\.ai_chat_messages/);
  assert.match(migration, /update public\.ai_chat_messages as message\s+set user_id = session\.user_id/s);
  assert.match(migration, /alter column user_id set not null/);
  assert.match(migration, /foreign key \(session_id\) references public\.ai_chat_sessions\(id\) on delete cascade/);
  assert.match(migration, /ai_chat_messages_own_rows/);
});

test('chat proxy requires auth and validates session ownership before forwarding', () => {
  const source = readFileSync(new URL('../app/api/chat/route.ts', import.meta.url), 'utf8');

  assert.match(source, /requireUserContext\(req\)/);
  assert.match(source, /if \(!auth\.ok\) return auth\.response/);
  assert.match(source, /\.from\('ai_chat_sessions'\)[\s\S]*?\.eq\('id', sessionId\)[\s\S]*?\.eq\('user_id', userContext\.user\.id\)[\s\S]*?\.maybeSingle\(\)/);
  assert.match(source, /return NextResponse\.json\(\{ error: 'session_not_found' \}, \{ status: 403 \}\)/);
  assert.match(source, /\.update\(\{ updated_at:[\s\S]*?\.eq\('id', sessionId\)\s*\.eq\('user_id', userContext\.user\.id\)/);
});

test('inline copilot uses the real chat API request and response shape', () => {
  const source = readFileSync(new URL('../components/canvas/InlineCopilot.tsx', import.meta.url), 'utf8');

  assert.match(source, /fetch\('\/api\/chat'/);
  assert.match(source, /Authorization: `Bearer \$\{token\}`/);
  assert.match(source, /query:/);
  assert.match(source, /asset_type:/);
  assert.match(source, /conversation_context:/);
  assert.match(source, /data\.answer/);
  assert.doesNotMatch(source, /messages:\s*\[\{\s*role:\s*'user'/);
  assert.doesNotMatch(source, /data\.content \|\| data\.reply/);
});

test('comparison view syncs local ids when a new compare action arrives', () => {
  const layout = readFileSync(new URL('../components/layout/DashboardLayout.tsx', import.meta.url), 'utf8');
  const chat = readFileSync(new URL('../components/chat/ChatWindow.tsx', import.meta.url), 'utf8');
  const comparison = readFileSync(new URL('../components/canvas/ComparisonView.tsx', import.meta.url), 'utf8');

  assert.match(layout, /key=\{`comparison:\$\{selectedIds\.join\('\|'\)\}`\}/);
  assert.match(layout, /key=\{`comparison-graph:\$\{selectedIds\.join\('\|'\)\}`\}/);
  assert.match(chat, /key=\{\(msg\.metadata\.system_action_ids as string\[\]\)\.join\('\|'\)\}/);
  assert.match(comparison, /setIds\(newIds\);\s*store\.setIds\(newIds\);/);
});
