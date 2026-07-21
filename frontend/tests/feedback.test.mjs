import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

test('feedback migration is service-role-only and validates ratings', () => {
  const migration = readFileSync(
    new URL('../../backend/migrations/20260721_add_user_feedback.sql', import.meta.url),
    'utf8',
  );

  assert.match(migration, /create table if not exists public\.user_feedback/);
  assert.match(migration, /feedback_type in \('general', 'response', 'logout'\)/);
  assert.match(migration, /rating between 1 and 5/);
  assert.match(migration, /message_id uuid references public\.ai_chat_messages\(id\) on delete set null/);
  assert.match(migration, /alter table public\.user_feedback enable row level security/);
  assert.match(migration, /revoke all on table public\.user_feedback from anon, authenticated/);
  assert.match(migration, /grant select, insert, update, delete on table public\.user_feedback to service_role/);
});

test('feedback API authenticates app and response feedback and validates owned chat targets', () => {
  const source = readFileSync(new URL('../app/api/feedback/route.ts', import.meta.url), 'utf8');

  assert.match(source, /feedbackType !== 'logout' && !userContext/);
  assert.match(source, /enforceRateLimit\(request, 'feedback'/);
  assert.match(source, /\.from\('ai_chat_messages'\)[\s\S]*?\.eq\('user_id', userContext\.user\.id\)[\s\S]*?\.eq\('role', 'system'\)/);
  assert.match(source, /\.from\('ai_chat_sessions'\)[\s\S]*?\.eq\('user_id', userContext\.user\.id\)/);
  assert.match(source, /\.from\('user_feedback'\)\.insert/);
  assert.match(source, /const messageId = isResponseFeedback \? optionalUuid/);
});

test('authenticated workspace exposes app feedback and chat response ratings', () => {
  const gate = readFileSync(new URL('../components/auth/AuthGate.tsx', import.meta.url), 'utf8');
  const prompt = readFileSync(new URL('../components/feedback/FeedbackPrompt.tsx', import.meta.url), 'utf8');
  const response = readFileSync(new URL('../components/feedback/ResponseFeedback.tsx', import.meta.url), 'utf8');
  const chat = readFileSync(new URL('../components/chat/ChatWindow.tsx', import.meta.url), 'utf8');

  assert.match(gate, /<FeedbackPrompt/);
  assert.match(prompt, /role="dialog"/);
  assert.match(prompt, /feedback_type: 'general'/);
  assert.match(response, /feedback_type: 'response'/);
  assert.match(response, /Helpful response/);
  assert.match(response, /Unhelpful response/);
  assert.match(chat, /<ResponseFeedback/);
});

test('logout feedback page accepts an optional comment and clears the redirect marker', () => {
  const page = readFileSync(new URL('../components/feedback/FeedbackPageForm.tsx', import.meta.url), 'utf8');

  assert.match(page, /feedback_type: isLogout \? 'logout' : 'general'/);
  assert.match(page, /fundersai-logout-feedback-pending/);
  assert.match(page, /Your thoughts/);
  assert.match(page, /\(optional\)/);
});
