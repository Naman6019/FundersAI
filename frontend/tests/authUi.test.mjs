import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const authForm = readFileSync(
  new URL('../components/auth/AuthForm.tsx', import.meta.url),
  'utf8',
);
const resetForm = readFileSync(
  new URL('../components/auth/ResetPasswordForm.tsx', import.meta.url),
  'utf8',
);
const authShell = readFileSync(
  new URL('../components/auth/AuthShell.tsx', import.meta.url),
  'utf8',
);

test('auth screen uses truthful local product trust signals', () => {
  assert.doesNotMatch(authForm, /Join thousands|randomuser\.me|svgrepo\.com/);
  assert.match(authShell, /FUNDERSAI-background\.png/);
  assert.match(authShell, /#050505/);
  assert.match(authShell, /#00FF9D/);
  assert.doesNotMatch(authShell, /#66a3ff/);
  assert.match(authShell, /Research-only/);
  assert.match(authShell, /Official evidence where available/);
  assert.match(authShell, /href="\/terms"/);
  assert.match(authShell, /href="\/privacy"/);
});

test('auth screen exposes accessible fields and explicit feedback states', () => {
  assert.match(authForm, /htmlFor="auth-email"/);
  assert.match(authForm, /htmlFor="auth-password"/);
  assert.match(authForm, /aria-label=\{showPassword \? 'Hide password' : 'Show password'\}/);
  assert.match(authForm, /feedback\.kind === 'error'/);
  assert.doesNotMatch(authForm, /message\.includes/);
});

test('password recovery uses the Supabase callback and a generic confirmation', () => {
  assert.match(authForm, /resetPasswordForEmail/);
  assert.match(authForm, /\/auth\/callback\?next=\/auth\/reset-password/);
  assert.match(authForm, /If an account exists for this email/);
  assert.match(resetForm, /supabaseBrowser\.auth\.updateUser\(\{ password \}\)/);
  assert.match(resetForm, /await supabaseBrowser\.auth\.signOut\(\)/);
});
