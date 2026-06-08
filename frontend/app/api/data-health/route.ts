import { NextResponse } from 'next/server';
import { backendUrl } from '../quant/proxy';
import { checkRateLimit, getClientIp, rateLimitResponse } from '@/lib/rateLimit';
import { getUserContext } from '@/lib/auth/server';

export async function GET(request: Request) {
  try {
    const userContext = await getUserContext(request);
    const rateLimit = await checkRateLimit(request, 'data-health', userContext ? {
      identifier: userContext.user.id,
      tier: userContext.profile.tier,
      role: userContext.profile.role,
    } : {});
    if (!rateLimit.allowed && rateLimit.configured) {
      return rateLimitResponse(rateLimit);
    }
    if (!rateLimit.configured) {
      console.warn('Data health rate limit storage is not configured; continuing without rate limit.');
    }

    const res = await fetch(backendUrl('/api/data-health'), {
      method: 'GET',
      cache: 'no-store',
      headers: {
        'X-Forwarded-For': getClientIp(request),
      },
    });
    const body = await res.json().catch(() => ({ error: 'Invalid backend response' }));
    return NextResponse.json(body, { status: res.status });
  } catch (error) {
    console.error('Data health proxy error:', error);
    return NextResponse.json(
      {
        status: 'degraded',
        source: 'frontend_proxy_error',
        metrics: [
          { label: 'MF NAV', status: 'Error', note: 'Proxy request failed.', last_updated: null },
          { label: 'AUM / TER', status: 'Error', note: 'Proxy request failed.', last_updated: null },
          { label: 'Risk metrics', status: 'Error', note: 'Proxy request failed.', last_updated: null },
          { label: 'AMC docs', status: 'Error', note: 'Proxy request failed.', last_updated: null },
        ],
        checked_at: new Date().toISOString(),
      },
      { status: 502 },
    );
  }
}
