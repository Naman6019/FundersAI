import { NextResponse } from 'next/server';
import { getUserContext } from '@/lib/auth/server';
import { enforceRateLimit, getClientIp } from '@/lib/rateLimit';

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const userContext = await getUserContext(req);
    const limited = await enforceRateLimit(req, 'category-funds', userContext ? {
      identifier: userContext.user.id,
      tier: userContext.profile.tier,
      role: userContext.profile.role,
    } : {});
    if (limited) return limited;

    const targetBase = process.env.NODE_ENV === 'development'
      ? 'http://127.0.0.1:8000'
      : process.env.NEXT_PUBLIC_API_URL;
    const proxyRes = await fetch(`${targetBase}/api/funds/category/compare`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Forwarded-For': getClientIp(req),
      },
      body: JSON.stringify(body),
    });
    const text = await proxyRes.text();
    return new NextResponse(text, {
      status: proxyRes.status,
      headers: { 'Content-Type': proxyRes.headers.get('content-type') || 'application/json' },
    });
  } catch (error) {
    console.error('Category compare proxy error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
