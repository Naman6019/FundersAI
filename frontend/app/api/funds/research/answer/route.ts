import { NextResponse } from 'next/server';
import { getUserContext } from '@/lib/auth/server';
import { enforceRateLimit, getClientIp } from '@/lib/rateLimit';

export async function POST(req: Request) {
  try {
    const userContext = await getUserContext(req);
    const limited = await enforceRateLimit(req, 'chat', userContext ? {
      identifier: userContext.user.id,
      tier: userContext.profile.tier,
      role: userContext.profile.role,
    } : {});
    if (limited) return limited;

    const targetBase = process.env.NODE_ENV === 'development'
      ? 'http://127.0.0.1:8000'
      : process.env.NEXT_PUBLIC_API_URL;
    const proxyRes = await fetch(`${targetBase}/api/funds/research/answer`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Forwarded-For': getClientIp(req) },
      body: JSON.stringify(await req.json()),
      cache: 'no-store',
    });
    return new NextResponse(await proxyRes.text(), {
      status: proxyRes.status,
      headers: { 'Content-Type': proxyRes.headers.get('content-type') || 'application/json' },
    });
  } catch (error) {
    console.error('Fund research answer proxy error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
