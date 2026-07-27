import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

test('dashboard links exact shared health status without sidebar pipeline duplication', () => {
  const layout = readFileSync(new URL('../components/layout/DashboardLayout.tsx', import.meta.url), 'utf8');
  const sidebar = readFileSync(new URL('../components/layout/AppSidebar.tsx', import.meta.url), 'utf8');
  const health = readFileSync(new URL('../lib/dataHealth.ts', import.meta.url), 'utf8');

  assert.match(layout, /href="\/dashboard\/data-trust"/);
  assert.match(layout, /dataHealthSummary\(dataHealth\.metrics\)/);
  assert.match(health, /label: `\$\{affected\.label\} \$\{affected\.status\.toLowerCase\(\)\}`/);
  assert.doesNotMatch(layout, /MF data lagging|toggleCanvas|>Canvas</);
  assert.doesNotMatch(sidebar, />\s*Pipelines\s*</);
  assert.doesNotMatch(sidebar, />\s*Data health\s*</);
});
