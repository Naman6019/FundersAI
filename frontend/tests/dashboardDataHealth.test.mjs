import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

test('dashboard exposes lagging mutual-fund data after the health check', () => {
  const layout = readFileSync(new URL('../components/layout/DashboardLayout.tsx', import.meta.url), 'utf8');
  const sidebar = readFileSync(new URL('../components/layout/AppSidebar.tsx', import.meta.url), 'utf8');

  assert.match(layout, /\{ label: 'AMC docs', status: 'Checking' \}/);
  assert.match(layout, /function isLaggingMfDataStatus/);
  assert.match(layout, /healthCheckedAt\s*\?/);
  assert.match(layout, /MF data lagging/);
  assert.match(sidebar, /dataHealth\.slice\(0, 4\)/);
});
