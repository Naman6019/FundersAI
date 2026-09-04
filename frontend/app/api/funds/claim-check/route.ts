import { NextResponse } from 'next/server';
import { getUserContext } from '@/lib/auth/server';
import { isFundTruthCheckPrivateEnabled } from '@/lib/fundTruthCheckPrivate';
import { enforceRateLimit, getClientIp } from '@/lib/rateLimit';

const PRIVATE_HEADERS = {
  'Cache-Control': 'no-store, max-age=0',
  'X-Robots-Tag': 'noindex, nofollow, noarchive',
};

function json(body: unknown, status = 200) {
  return NextResponse.json(body, { status, headers: PRIVATE_HEADERS });
}

export async function POST(request: Request) {
  if (!isFundTruthCheckPrivateEnabled()) {
    return json({ error: 'Not Found' }, 404);
  }

  const userContext = await getUserContext(request);
  if (process.env.NODE_ENV === 'production' && !userContext) {
    return json({ error: 'Unauthorized' }, 401);
  }

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return json({ error: 'invalid_json' }, 400);
  }

  const input = typeof (payload as { input?: unknown })?.input === 'string'
    ? (payload as { input: string }).input.trim()
    : '';
  if (input.length < 3 || input.length > 2_000) {
    return json({ error: 'input_must_be_between_3_and_2000_characters' }, 400);
  }

  const limited = await enforceRateLimit(request, 'claim-check', userContext ? {
    identifier: userContext.user.id,
    tier: userContext.profile.tier,
    role: userContext.profile.role,
  } : {});
  if (limited) {
    Object.entries(PRIVATE_HEADERS).forEach(([name, value]) => limited.headers.set(name, value));
    return limited;
  }

  const proxyKey = String(process.env.CLAIM_CHECK_INTERNAL_PROXY_KEY || '').trim();
  if (!proxyKey) {
    console.error('Fund Truth Check proxy is missing CLAIM_CHECK_INTERNAL_PROXY_KEY.');
    return json({ error: 'claim_check_unavailable' }, 503);
  }

  const targetBase = String(
    process.env.BACKEND_API_URL
      || process.env.NEXT_PUBLIC_API_URL
      || (process.env.NODE_ENV === 'development' ? 'http://127.0.0.1:8000' : ''),
  ).replace(/\/$/, '');
  if (!targetBase) return json({ error: 'claim_check_unavailable' }, 503);

  try {
    const backendResponse = await fetch(`${targetBase}/api/funds/claim-check`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-Proxy-Key': proxyKey,
        'X-Forwarded-For': getClientIp(request),
      },
      body: JSON.stringify({ input }),
      cache: 'no-store',
      signal: AbortSignal.timeout(15_000),
    });

    const responseBody = await backendResponse.text();
    if (!backendResponse.ok) {
      console.error(`Fund Truth Check backend returned ${backendResponse.status}.`);
      return json(
        { error: backendResponse.status === 429 ? 'rate_limited' : 'claim_check_unavailable' },
        backendResponse.status === 429 ? 429 : 502,
      );
    }

    return new NextResponse(responseBody, {
      status: 200,
      headers: {
        ...PRIVATE_HEADERS,
        'Content-Type': backendResponse.headers.get('content-type') || 'application/json',
      },
    });
  } catch (error) {
    console.error('Fund Truth Check proxy failed:', error);
    return json({ error: 'claim_check_unavailable' }, 502);
  }
}
