import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';

test('landing hero keeps typed WebGL cleanup scoped to its own timeline', () => {
  const source = readFileSync(
    new URL('../components/ui/ai-input-hero.tsx', import.meta.url),
    'utf8',
  );

  assert.doesNotMatch(source, /\bas any\b/);
  assert.doesNotMatch(source, /gsap\.globalTimeline\.clear/);
  assert.match(source, /mainTimeline\?\.kill\(\)/);
  assert.match(source, /\}, \[extendLeftPx\]\);/);
  assert.match(source, /radial-gradient\(circle_at_72%_78%/);
});

test('mobile detection uses a subscription snapshot instead of effect-driven state', () => {
  const source = readFileSync(
    new URL('../hooks/use-mobile.ts', import.meta.url),
    'utf8',
  );

  assert.match(source, /useSyncExternalStore/);
  assert.match(source, /matchMedia\(MOBILE_QUERY\)\.matches/);
  assert.doesNotMatch(source, /setIsMobile/);
});

test('effect-triggered chat requests are deferred and cancellable', () => {
  const source = readFileSync(
    new URL('../components/chat/ChatWindow.tsx', import.meta.url),
    'utf8',
  );

  assert.match(source, /const timer = window\.setTimeout/);
  assert.match(source, /return \(\) => window\.clearTimeout\(timer\)/);
});
