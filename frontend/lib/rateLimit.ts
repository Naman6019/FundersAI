import { createHash } from 'crypto';
import { UserRole, UserTier, effectiveRateLimitTier } from './billing/tiers';

type RateLimitWindow = {
  name: string;
  limit: number;
  seconds: number;
};

export type RateLimitGroup =
  | 'chat'
  | 'quant'
  | 'mf-detail'
  | 'category-funds'
  | 'search'
  | 'data-health'
  | 'feedback'
  | 'cron-sync-mf'
  | 'admin-mutation';

export type RateLimitResult = {
  allowed: boolean;
  configured: boolean;
  limit: number;
  remaining: number;
  resetSeconds: number;
  retryAfterSeconds: number;
};

export const RATE_LIMIT_GROUPS: Record<RateLimitGroup, RateLimitWindow[]> = {
  chat: [
    { name: 'minute', limit: 10, seconds: 60 },
  ],
  quant: [
    { name: 'minute', limit: 60, seconds: 60 },
    { name: 'day', limit: 1000, seconds: 86400 },
  ],
  'mf-detail': [
    { name: 'minute', limit: 60, seconds: 60 },
    { name: 'day', limit: 1000, seconds: 86400 },
  ],
  'category-funds': [
    { name: 'minute', limit: 60, seconds: 60 },
    { name: 'day', limit: 1000, seconds: 86400 },
  ],
  search: [
    { name: 'minute', limit: 30, seconds: 60 },
    { name: 'day', limit: 500, seconds: 86400 },
  ],
  'data-health': [
    { name: 'minute', limit: 30, seconds: 60 },
    { name: 'day', limit: 500, seconds: 86400 },
  ],
  feedback: [
    { name: 'minute', limit: 10, seconds: 60 },
    { name: 'day', limit: 100, seconds: 86400 },
  ],
  'cron-sync-mf': [
    { name: 'hour', limit: 2, seconds: 3600 },
  ],
  'admin-mutation': [
    { name: 'minute', limit: 20, seconds: 60 },
  ],
};

export const RATE_LIMIT_TIERS: Record<UserTier, Partial<Record<RateLimitGroup, RateLimitWindow[]>>> = {
  free: {
    chat: [
      { name: 'minute', limit: 5, seconds: 60 },
    ],
    quant: [
      { name: 'minute', limit: 20, seconds: 60 },
      { name: 'day', limit: 100, seconds: 86400 },
    ],
    'mf-detail': [
      { name: 'minute', limit: 20, seconds: 60 },
      { name: 'day', limit: 100, seconds: 86400 },
    ],
    'category-funds': [
      { name: 'minute', limit: 30, seconds: 60 },
      { name: 'day', limit: 300, seconds: 86400 },
    ],
    search: [
      { name: 'minute', limit: 10, seconds: 60 },
      { name: 'day', limit: 50, seconds: 86400 },
    ],
    'data-health': [
      { name: 'minute', limit: 15, seconds: 60 },
      { name: 'day', limit: 100, seconds: 86400 },
    ],
    feedback: [
      { name: 'minute', limit: 5, seconds: 60 },
      { name: 'day', limit: 30, seconds: 86400 },
    ],
  },
  pro: RATE_LIMIT_GROUPS,
  ultra: {
    chat: [
      { name: 'minute', limit: 30, seconds: 60 },
    ],
    quant: [
      { name: 'minute', limit: 180, seconds: 60 },
      { name: 'day', limit: 3000, seconds: 86400 },
    ],
    'mf-detail': [
      { name: 'minute', limit: 180, seconds: 60 },
      { name: 'day', limit: 3000, seconds: 86400 },
    ],
    'category-funds': [
      { name: 'minute', limit: 180, seconds: 60 },
      { name: 'day', limit: 3000, seconds: 86400 },
    ],
    search: [
      { name: 'minute', limit: 90, seconds: 60 },
      { name: 'day', limit: 1500, seconds: 86400 },
    ],
    'data-health': [
      { name: 'minute', limit: 90, seconds: 60 },
      { name: 'day', limit: 1500, seconds: 86400 },
    ],
    feedback: [
      { name: 'minute', limit: 20, seconds: 60 },
      { name: 'day', limit: 300, seconds: 86400 },
    ],
    'cron-sync-mf': RATE_LIMIT_GROUPS['cron-sync-mf'],
    'admin-mutation': RATE_LIMIT_GROUPS['admin-mutation'],
  },
};

type WindowUsage = {
  count: number;
  resetSeconds: number;
  window: RateLimitWindow;
};

const memoryStore = new Map<string, { count: number; expiresAtMs: number }>();
let warnedInMemoryFallback = false;

function isEnabled(): boolean {
  return String(process.env.RATE_LIMIT_ENABLED ?? 'true').trim().toLowerCase() !== 'false';
}

function upstashConfig() {
  const url = String(process.env.UPSTASH_REDIS_REST_URL || '').trim().replace(/\/$/, '');
  const token = String(process.env.UPSTASH_REDIS_REST_TOKEN || '').trim();
  return { url, token, configured: Boolean(url && token) };
}

function hashValue(value: string): string {
  return createHash('sha256').update(value).digest('hex').slice(0, 24);
}

export function getClientIp(request: Request): string {
  const forwarded = request.headers.get('x-forwarded-for')?.split(',')[0]?.trim();
  return (
    forwarded ||
    request.headers.get('x-real-ip')?.trim() ||
    request.headers.get('cf-connecting-ip')?.trim() ||
    'unknown'
  );
}

export function rateLimitIdentity(request: Request, override?: string): string {
  return hashValue(String(override || getClientIp(request)));
}

function windowKey(group: RateLimitGroup, identity: string, window: RateLimitWindow, nowMs: number): string {
  const bucket = Math.floor(nowMs / 1000 / window.seconds);
  return `rl:${group}:${identity}:${window.name}:${bucket}`;
}

function secondsUntilReset(window: RateLimitWindow, nowMs: number): number {
  const nowSeconds = Math.floor(nowMs / 1000);
  const nextReset = (Math.floor(nowSeconds / window.seconds) + 1) * window.seconds;
  return Math.max(nextReset - nowSeconds, 1);
}

async function readMemoryWindow(group: RateLimitGroup, identity: string, window: RateLimitWindow, nowMs: number): Promise<WindowUsage> {
  const key = windowKey(group, identity, window, nowMs);
  const resetSeconds = secondsUntilReset(window, nowMs);
  const existing = memoryStore.get(key);
  if (!existing || existing.expiresAtMs <= nowMs) {
    memoryStore.set(key, { count: 1, expiresAtMs: nowMs + resetSeconds * 1000 });
    return { count: 1, resetSeconds, window };
  }
  existing.count += 1;
  return { count: existing.count, resetSeconds, window };
}

async function readUpstashWindow(group: RateLimitGroup, identity: string, window: RateLimitWindow, nowMs: number): Promise<WindowUsage> {
  const { url, token } = upstashConfig();
  const key = windowKey(group, identity, window, nowMs);
  const resetSeconds = secondsUntilReset(window, nowMs);
  const response = await fetch(`${url}/pipeline`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify([
      ['INCR', key],
      ['EXPIRE', key, resetSeconds + 5],
    ]),
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new Error(`upstash_rate_limit_failed:${response.status}`);
  }
  const payload = await response.json();
  const count = Number(payload?.[0]?.result || 0);
  return { count, resetSeconds, window };
}

export async function checkRateLimit(
  request: Request,
  group: RateLimitGroup,
  options: { identifier?: string; nowMs?: number; tier?: UserTier; role?: UserRole } = {},
): Promise<RateLimitResult> {
  const tier = effectiveRateLimitTier(options.tier, options.role);
  const windows = RATE_LIMIT_TIERS[tier][group] || RATE_LIMIT_GROUPS[group];
  if (!isEnabled() || !windows) {
    return { allowed: true, configured: true, limit: 0, remaining: 0, resetSeconds: 0, retryAfterSeconds: 0 };
  }

  const config = upstashConfig();
  if (!config.configured) {
    if (process.env.NODE_ENV === 'production') {
      return { allowed: false, configured: false, limit: 0, remaining: 0, resetSeconds: 60, retryAfterSeconds: 60 };
    }
    if (!warnedInMemoryFallback) {
      warnedInMemoryFallback = true;
      console.warn('Rate limit storage (Upstash Redis) is not configured; falling back to in-memory rate limiting.');
    }
  }
  const useMemory = !config.configured;

  const nowMs = options.nowMs ?? Date.now();
  const identity = rateLimitIdentity(request, options.identifier);
  const usages = await Promise.all(
    windows.map((window) => (
      useMemory
        ? readMemoryWindow(group, identity, window, nowMs)
        : readUpstashWindow(group, identity, window, nowMs)
    )),
  );

  const mostLimited = usages.reduce((selected, usage) => {
    const selectedRemaining = selected.window.limit - selected.count;
    const usageRemaining = usage.window.limit - usage.count;
    return usageRemaining < selectedRemaining ? usage : selected;
  }, usages[0]);
  const allowed = usages.every((usage) => usage.count <= usage.window.limit);
  const retryAfterSeconds = allowed
    ? 0
    : Math.max(...usages.filter((usage) => usage.count > usage.window.limit).map((usage) => usage.resetSeconds));

  return {
    allowed,
    configured: true,
    limit: mostLimited.window.limit,
    remaining: Math.max(mostLimited.window.limit - mostLimited.count, 0),
    resetSeconds: mostLimited.resetSeconds,
    retryAfterSeconds,
  };
}

export function rateLimitHeaders(result: RateLimitResult): Headers {
  const headers = new Headers();
  headers.set('X-RateLimit-Limit', String(result.limit));
  headers.set('X-RateLimit-Remaining', String(result.remaining));
  headers.set('X-RateLimit-Reset', String(result.resetSeconds));
  if (!result.allowed) {
    headers.set('Retry-After', String(result.retryAfterSeconds));
  }
  return headers;
}

export function rateLimitResponse(result: RateLimitResult): Response {
  const status = result.configured ? 429 : 503;
  const error = result.configured ? 'rate_limited' : 'rate_limit_unconfigured';
  return Response.json(
    { error, retry_after_seconds: result.retryAfterSeconds },
    { status, headers: rateLimitHeaders(result) },
  );
}

export async function enforceRateLimit(
  request: Request,
  group: RateLimitGroup,
  options: { identifier?: string; tier?: UserTier; role?: UserRole } = {},
): Promise<Response | null> {
  let result: RateLimitResult;
  try {
    result = await checkRateLimit(request, group, options);
  } catch {
    result = { allowed: false, configured: false, limit: 0, remaining: 0, resetSeconds: 60, retryAfterSeconds: 60 };
  }
  return result.allowed ? null : rateLimitResponse(result);
}

export function resetRateLimitMemoryForTests(): void {
  memoryStore.clear();
}
