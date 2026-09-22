import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';
import ts from 'typescript';

// Loads middleware.ts and exposes a request stub so host routing can be exercised without
// a running Next.js server.
function loadMiddleware() {
  const source = ts.transpileModule(readFileSync('middleware.ts', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const exports = {};
  const redirects = [];
  const rewrites = [];
  vm.runInNewContext(source, {
    exports,
    URL,
    require: () => ({
      NextResponse: {
        next: () => ({ kind: 'next' }),
        rewrite: (url) => { rewrites.push(url.toString()); return { kind: 'rewrite', url: url.toString() }; },
        redirect: (url, status) => {
          redirects.push({ url: url.toString(), status });
          return { kind: 'redirect', url: url.toString(), status };
        },
      },
    }),
  });
  const run = (host, pathname, search = '') => {
    redirects.length = 0;
    rewrites.length = 0;
    const request = {
      headers: { get: (name) => (name === 'host' ? host : null) },
      nextUrl: { pathname, search },
      url: `https://${host}${pathname}${search}`,
    };
    const result = exports.middleware(request);
    return { result, redirects, rewrites };
  };
  return { run };
}

test('synthesis subdomain /synthesis collapses to the canonical root', () => {
  const { run } = loadMiddleware();
  const { result, redirects } = run('synthesis.fundersai.co.in', '/synthesis');
  assert.equal(result.status, 308);
  assert.equal(redirects[0].url, 'https://synthesis.fundersai.co.in/');

  // Trailing slash and query strings must preserve so the redirect is not a new duplicate.
  const withQuery = run('synthesis.fundersai.co.in', '/synthesis/', '?utm_source=x');
  assert.equal(withQuery.result.status, 308);
  assert.equal(withQuery.redirects[0].url, 'https://synthesis.fundersai.co.in/?utm_source=x');
});

test('synthesis subdomain root still rewrites to the studio landing page', () => {
  const { run } = loadMiddleware();
  const { result, rewrites } = run('synthesis.fundersai.co.in', '/');
  assert.equal(result.kind, 'rewrite');
  assert.equal(rewrites[0], 'https://synthesis.fundersai.co.in/synthesis');
});

test('synthesis subdomain studio pages are served, other paths return to www', () => {
  const { run } = loadMiddleware();
  assert.equal(run('synthesis.fundersai.co.in', '/synthesis/methodology').result.kind, 'next');
  assert.equal(run('synthesis.fundersai.co.in', '/synthesis/vs/a-vs-b').result.kind, 'next');

  const offHost = run('synthesis.fundersai.co.in', '/pricing');
  assert.equal(offHost.result.status, 308);
  assert.equal(offHost.redirects[0].url, 'https://www.fundersai.co.in/pricing');
});

test('www /synthesis redirects straight to the canonical subdomain root', () => {
  const { run } = loadMiddleware();

  // The landing page's canonical is the bare subdomain root, so www must not chain through
  // subdomain /synthesis (which itself 308s to root) — that would be a two-hop redirect.
  const landing = run('www.fundersai.co.in', '/synthesis');
  assert.equal(landing.result.status, 308);
  assert.equal(landing.redirects[0].url, 'https://synthesis.fundersai.co.in/');

  // Deeper studio paths still map to their own subdomain URL.
  const deep = run('www.fundersai.co.in', '/synthesis/methodology', '?a=1');
  assert.equal(deep.result.status, 308);
  assert.equal(deep.redirects[0].url, 'https://synthesis.fundersai.co.in/synthesis/methodology?a=1');
});
