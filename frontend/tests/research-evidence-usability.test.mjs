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
  assert.match(page, /Models and components used/);
  assert.match(page, /model_usage/);
  assert.match(page, /Only components used for this answer are listed/);
  assert.match(page, /Developer evaluation \(not part of the answer\)/);
  assert.match(page, /Expected sources found/);
  assert.match(page, /Correct refusals/);
  assert.match(page, /citationMatch/);
  assert.match(page, /answer_format/);
  assert.match(page, /isLegacyExcerptDump/);
  assert.match(page, /Matching official evidence/);
  assert.match(page, /View matching excerpt/);
  assert.match(page, /View evidence \{sourceNumber\}/);
  assert.match(page, /Official evidence excerpts/);
  assert.match(page, /!isAbstention && !isExtractiveFallback/);
  assert.match(page, /has not converted them into an answer because the wording could not be verified safely/);
});
