// Run after npm run build: node tests/mfCatalogHttpSmoke.mjs
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { resolve } from 'node:path';
import { setTimeout as delay } from 'node:timers/promises';

const outage = process.env.MF_CATALOG_SMOKE_OUTAGE === '1';

async function runServer({ port, verify }) {
  const child = spawn(process.execPath, ['--require', resolve('tests/fixtures/mfCatalogFetch.cjs'),
    resolve('node_modules/next/dist/bin/next'), 'start', '--hostname', '127.0.0.1', '--port', String(port)], {
    windowsHide: true, env: { ...process.env, SUPABASE_SERVICE_ROLE_KEY: 'synthetic-test-key', MF_CATALOG_OUTAGE: outage ? '1' : '0' }, stdio: 'pipe',
  });
  let output = '';
  child.stdout.on('data', c => { output += c; });
  child.stderr.on('data', c => { output += c; });
  for (let attempt = 0; attempt < 60; attempt++) {
    if (output.includes('Ready in')) break;
    if (child.exitCode !== null) throw new Error(output);
    await delay(500);
  }
  if (!output.includes('Ready in')) throw new Error(`Next.js did not start:\n${output}`);
  try {
    await verify(`http://127.0.0.1:${port}`);
  } finally {
    child.kill();
  }
}

await runServer({ port: 3327, verify: async (base) => {
  if (outage) {
    for (const path of [
      '/mutual-funds',
      '/mutual-funds/hdfc',
      '/mutual-funds/category/flexi-cap',
      '/mutual-funds/hdfc/hdfc-flexi-cap-fund',
    ]) {
      const directory = await fetch(base + path);
      const directoryHtml = await directory.text();
      assert.equal(directory.status, 200, path);
      assert.ok(directoryHtml.includes('temporarily unavailable'), path);
      assert.ok(directoryHtml.includes('noindex'), path);
    }

    const sitemap = await (await fetch(base + '/sitemap.xml')).text();
    assert.ok(!sitemap.includes('/mutual-funds'));
    assert.ok(sitemap.includes('/methodology'));
    console.log('Catalog outage keeps the directory non-indexable and the sitemap valid');
    return;
  }

  for (const [path, status] of [
    ['/mutual-funds/hdfc/hdfc-flexi-cap-fund', 200],
    ['/mutual-funds/hdfc/missing', 404],
    ['/mutual-funds/hdfc/rejected', 404],
    ['/mutual-funds/missing-amc', 404],
    ['/mutual-funds/category/missing-category', 404],
  ]) {
    const response = await fetch(base + path, { signal: AbortSignal.timeout(20000) });
    const html = await response.text();
    assert.equal(response.status, status, `${path}: expected ${status}`);
    if (status === 200) {
      assert.ok(html.includes('123.4500') && html.includes('10.00%') && html.includes('Insufficient history'));
      assert.ok(html.includes('https://www.fundersai.co.in/mutual-funds/hdfc/hdfc-flexi-cap-fund'));
    }
    console.log(`${response.status} ${path}`);
  }
  const routeOutage = await fetch(base + '/mutual-funds/outage/anything');
  const routeOutageHtml = await routeOutage.text();
  assert.equal(routeOutage.status, 200);
  assert.ok(routeOutageHtml.includes('temporarily unavailable'));
  assert.ok(routeOutageHtml.includes('noindex'));
  console.log('200 /mutual-funds/outage/anything');
  const sitemap = await (await fetch(base + '/sitemap.xml')).text();
  assert.ok(sitemap.includes('/mutual-funds/hdfc/hdfc-flexi-cap-fund'));
  assert.ok(!sitemap.includes('/mutual-funds/ppfas/'));
  console.log('Sitemap includes the eligible fixture only');
} });
