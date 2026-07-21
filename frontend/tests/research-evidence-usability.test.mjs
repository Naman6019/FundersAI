import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';

const page = readFileSync(new URL('../app/dashboard/research-evidence/page.tsx', import.meta.url), 'utf8');

test('research evidence defaults to reader-friendly labels and hides diagnostics in disclosures', () => {
  assert.match(page, /Question for official documents/);
  assert.match(page, /Fund house/);
  assert.match(page, /Answer from official documents/);
  assert.match(page, /Why you can trust this result/);
  assert.match(page, /<details[^>]*>[\s\S]*Technical audit trail/);
  assert.match(page, /Developer evaluation \(not part of the answer\)/);
  assert.match(page, /Expected sources found/);
  assert.match(page, /Correct refusals/);
  assert.match(page, /citationMatch/);
});
