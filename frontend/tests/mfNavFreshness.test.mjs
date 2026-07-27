import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

test('chat shows NAV freshness returned by the comparison service', () => {
  const chat = readFileSync(new URL('../components/chat/ChatWindow.tsx', import.meta.url), 'utf8');

  assert.match(chat, /row\.expected_nav_date/);
  assert.match(chat, /NAV lagging/);
  assert.match(chat, /Latest expected NAV date/);
});
