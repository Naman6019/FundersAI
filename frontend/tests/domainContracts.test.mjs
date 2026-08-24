import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

const supportedOrigin = 'https://www.fundersai.co.in';
const retiredOrigin = 'https://fundersai.com';

test('public metadata uses the supported production domain', () => {
  const files = [
    '../app/layout.tsx',
    '../app/robots.ts',
    '../app/sitemap.ts',
    '../components/landing/SchemaMarkup.tsx',
  ];

  for (const file of files) {
    const source = readFileSync(new URL(file, import.meta.url), 'utf8');
    assert.match(source, new RegExp(supportedOrigin.replaceAll('.', '\\.')));
    assert.doesNotMatch(source, new RegExp(retiredOrigin.replaceAll('.', '\\.')));
  }
});

test('root metadata sets metadataBase and home page publishes canonical URL', () => {
  const layoutSource = readFileSync(new URL('../app/layout.tsx', import.meta.url), 'utf8');
  const pageSource = readFileSync(new URL('../app/page.tsx', import.meta.url), 'utf8');

  assert.match(layoutSource, /metadataBase: new URL\('https:\/\/www\.fundersai\.co\.in'\)/);
  // Root layout must NOT set a blanket canonical: '/' to avoid the GSC root canonical trap
  assert.doesNotMatch(layoutSource, /canonical:\s*['"]\/['"]/);
  assert.match(pageSource, /canonical:\s*['"]https:\/\/www\.fundersai\.co\.in['"]/);
});

test('search identity publishes the FundersAI organization and square logo', () => {
  const source = readFileSync(
    new URL('../components/landing/SchemaMarkup.tsx', import.meta.url),
    'utf8',
  );
  const logo = readFileSync(new URL('../public/logo.png', import.meta.url));

  assert.match(source, /'@type': 'Organization'/);
  assert.match(source, /'@type': 'WebSite'/);
  assert.match(source, /https:\/\/www\.fundersai\.co\.in\/logo\.png/);
  assert.deepEqual(readFileSync(new URL('../app/icon.png', import.meta.url)), logo);
  assert.deepEqual(readFileSync(new URL('../app/apple-icon.png', import.meta.url)), logo);
});
