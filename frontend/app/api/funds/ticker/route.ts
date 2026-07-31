import { NextResponse } from 'next/server';
import { backendUrl } from '@/app/api/quant/proxy';
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
      console.warn('Rate limit storage is not configured; continuing without rate limit.');
    }

    const res = await fetch(backendUrl('/api/funds/ticker'), {
      method: 'GET',
      next: { revalidate: 1800 }, // Cache response for 30 minutes
      headers: {
        'X-Forwarded-For': getClientIp(request),
      },
    });
    
    if (!res.ok) {
      return NextResponse.json({ error: 'Backend error' }, { status: res.status });
    }
    
    const body = await res.json();
    return NextResponse.json(body, { status: 200 });
  } catch (error) {
    console.error('Ticker proxy error:', error);
    return NextResponse.json({ error: 'Internal server error' }, { status: 502 });
  }
}
