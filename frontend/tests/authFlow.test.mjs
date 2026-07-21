import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

test('sign out uses a full auth navigation after Supabase clears the session', () => {
  const source = readFileSync(
    new URL('../components/auth/SignOutButton.tsx', import.meta.url),
    'utf8',
  );

  assert.match(source, /await supabaseBrowser\.auth\.signOut\(\)/);
  assert.match(source, /window\.location\.replace\('\/auth'\)/);
  assert.doesNotMatch(source, /router\.replace/);
  assert.match(source, /disabled=\{isSigningOut\}/);
});
