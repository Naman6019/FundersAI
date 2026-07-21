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

  const hardening = readFileSync(
    new URL('../../backend/migrations/20260721_ensure_user_feedback_storage.sql', import.meta.url),
    'utf8',
  );
  assert.match(hardening, /create table if not exists public\.user_feedback/);
  assert.match(hardening, /revoke all on table public\.user_feedback from anon, authenticated/);
  assert.match(hardening, /revoke all on table public\.user_feedback from service_role/);
  assert.match(hardening, /grant select, insert on table public\.user_feedback to service_role/);
  assert.match(hardening, /notify pgrst, 'reload schema'/);
});

test('feedback API authenticates app and response feedback and validates owned chat targets', () => {
  const source = readFileSync(new URL('../app/api/feedback/route.ts', import.meta.url), 'utf8');

  assert.match(source, /feedbackType !== 'logout' && !userContext/);
  assert.match(source, /enforceRateLimit\(request, 'feedback'/);
  assert.match(source, /contentType !== 'application\/json'/);
  assert.match(source, /origin && origin !== new URL\(request\.url\)\.origin/);
  assert.match(source, /MAX_FEEDBACK_BODY_BYTES/);
  assert.match(source, /\.from\('ai_chat_messages'\)[\s\S]*?\.eq\('user_id', userContext\.user\.id\)[\s\S]*?\.eq\('role', 'system'\)/);
  assert.match(source, /\.from\('ai_chat_sessions'\)[\s\S]*?\.eq\('user_id', userContext\.user\.id\)/);
  assert.match(source, /\.from\('user_feedback'\)\.insert/);
  assert.match(source, /const messageId = isResponseFeedback \? optionalUuid/);
  assert.match(source, /error\.code === 'PGRST205'/);
});

test('feedback client surfaces storage and rate-limit failures without exposing server details', () => {
  const source = readFileSync(new URL('../lib/feedback.ts', import.meta.url), 'utf8');

  assert.match(source, /class FeedbackSubmissionError extends Error/);
  assert.match(source, /feedback_storage_unavailable/);
  assert.match(source, /rate_limited/);
  assert.match(source, /typeof data\?\.error === 'string'/);
});

test('Next.js applies baseline browser security headers', () => {
  const config = readFileSync(new URL('../next.config.ts', import.meta.url), 'utf8');

  assert.match(config, /poweredByHeader: false/);
  assert.match(config, /Content-Security-Policy/);
  assert.match(config, /frame-ancestors 'none'/);
  assert.match(config, /Strict-Transport-Security/);
  assert.match(config, /X-Content-Type-Options/);
  assert.match(config, /X-Frame-Options/);
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
