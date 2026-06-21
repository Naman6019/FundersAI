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

test('chat renders collapsed Thinking metadata', () => {
  const source = readFileSync(new URL('../components/chat/ChatWindow.tsx', import.meta.url), 'utf8');

  assert.match(source, /function ThinkingSummary/);
  assert.match(source, /metadata\?\.reasoning_summary/);
  assert.match(source, /<summary[^>]*>\s*Thinking\s*<\/summary>/);
  assert.match(source, /reasoning_summary: data\.reasoning_summary \|\| null/);
});

test('chat proxy persists Thinking metadata', () => {
  const source = readFileSync(new URL('../app/api/chat/route.ts', import.meta.url), 'utf8');

  assert.match(source, /reasoning_summary: data\.reasoning_summary \|\| null/);
});

test('inline copilot uses the real chat API request and response shape', () => {
  const source = readFileSync(new URL('../components/canvas/InlineCopilot.tsx', import.meta.url), 'utf8');

  assert.match(source, /fetch\('\/api\/chat'/);
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
