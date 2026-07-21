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

test('root metadata publishes an explicit canonical URL', () => {
  const source = readFileSync(new URL('../app/layout.tsx', import.meta.url), 'utf8');

  assert.match(source, /metadataBase: new URL\('https:\/\/www\.fundersai\.co\.in'\)/);
  assert.match(source, /alternates:\s*\{\s*canonical: '\/'/);
});
