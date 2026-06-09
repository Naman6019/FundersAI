import { NextResponse } from 'next/server';
import { getUserContext } from '@/lib/auth/server';
import { enforceRateLimit, getClientIp } from '@/lib/rateLimit';

export async function GET(req: Request) {
  try {
    const userContext = await getUserContext(req);
    const limited = await enforceRateLimit(req, 'chat', userContext ? {
      identifier: userContext.user.id,
      tier: userContext.profile.tier,
      role: userContext.profile.role,
    } : {});
    if (limited) return limited;

    const url = new URL(req.url);
    const category = url.searchParams.get('category') || '';
    const targetBase = process.env.NODE_ENV === 'development'
      ? 'http://127.0.0.1:8000'
      : process.env.NEXT_PUBLIC_API_URL;
    const target = `${targetBase}/api/funds/category?category=${encodeURIComponent(category)}`;

    const proxyRes = await fetch(target, {
      headers: { 'X-Forwarded-For': getClientIp(req) },
      cache: 'no-store',
    });
    const text = await proxyRes.text();
    return new NextResponse(text, {
      status: proxyRes.status,
      headers: { 'Content-Type': proxyRes.headers.get('content-type') || 'application/json' },
    });
  } catch (error) {
    console.error('Category funds proxy error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
