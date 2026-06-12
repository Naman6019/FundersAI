import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import test from 'node:test';

test('chat route forwards and stores trust metadata', () => {
  const route = readFileSync(resolve('app/api/chat/route.ts'), 'utf8');
  assert.match(route, /explanation_mode: body\.explanation_mode/);
  assert.match(route, /source_freshness: data\.source_freshness/);
  assert.match(route, /risk_analysis: data\.risk_analysis/);
  assert.match(route, /confidence: data\.confidence/);
});

test('chat store persists explanation mode preferences', () => {
  const store = readFileSync(resolve('store/useChatStore.ts'), 'utf8');
  assert.match(store, /ExplanationMode = 'beginner' \| 'advanced'/);
  assert.match(store, /fundersai-chat-preferences/);
  assert.match(store, /setExplanationMode/);
  assert.match(store, /researchDepth: explanationMode === 'advanced' \? 'deep' : 'standard'/);
});

test('chat window renders templates and source risk badges', () => {
  const chat = readFileSync(resolve('components/chat/ChatWindow.tsx'), 'utf8');
  assert.match(chat, /Mutual Fund Deep Dive/);
  assert.match(chat, /Stock Deep Dive/);
  assert.match(chat, /MessageMetadataBadges/);
  assert.match(chat, /risk_analysis/);
  assert.match(chat, /explanation_mode/);
});

test('comparison canvas renders risk analysis panel', () => {
  const comparison = readFileSync(resolve('components/canvas/ComparisonView.tsx'), 'utf8');
  assert.match(comparison, /type RiskAnalysisPayload/);
  assert.match(comparison, /function RiskAnalysisPanel/);
  assert.match(comparison, /getRiskAnalysis/);
  assert.match(comparison, /Risk Analysis/);
});
