import { NextResponse } from 'next/server';
import { getClientIp, enforceRateLimit } from '@/lib/rateLimit';
import { requireUserContext } from '@/lib/auth/server';

export async function POST(req: Request) {
  try {
    // Same auth as the research chat endpoint (see app/api/chat/route.ts): a
    // valid Supabase session is required before we'll spend LLM/compute
    // budget on a report.
    const auth = await requireUserContext(req);
    if (!auth.ok) return auth.response;
    const userContext = auth.context;

    const limited = await enforceRateLimit(req, 'reports', {
      identifier: userContext.user.id,
      tier: userContext.profile.tier,
      role: userContext.profile.role,
    });
    if (limited) return limited;

    const body = await req.json();
    const targetBase =
      process.env.REPORTS_MICROSERVICE_URL ||
      process.env.REPORTS_API_URL ||
      process.env.BACKEND_API_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      (process.env.NODE_ENV === 'development' ? 'http://127.0.0.1:8001' : 'http://127.0.0.1:8000');

    const targetUrl = `${targetBase.replace(/\/$/, '')}/api/v1/reports/stream`;

    console.log(`[Reports Stream Proxy] Proxying report request to ${targetUrl}`);

    const internalProxyKey = process.env.REPORTS_INTERNAL_PROXY_KEY || '';
    if (!internalProxyKey) {
      console.error('[Reports Stream Proxy] REPORTS_INTERNAL_PROXY_KEY is not set on the frontend server.');
      return NextResponse.json({ error: 'Reports service is not configured' }, { status: 503 });
    }

    const upstreamRes = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Forwarded-For': getClientIp(req),
        'X-User-Id': userContext.user.id,
        'X-User-Tier': userContext.profile.tier,
        'X-Internal-Proxy-Key': internalProxyKey,
      },
      body: JSON.stringify(body),
    });

    if (!upstreamRes.ok) {
      const errText = await upstreamRes.text().catch(() => 'Upstream error');
      console.error(`[Reports Stream Proxy] Upstream returned status ${upstreamRes.status}:`, errText);
      return NextResponse.json(
        { error: 'Failed to generate report from upstream service' },
        { status: upstreamRes.status },
      );
    }

    if (!upstreamRes.body) {
      return NextResponse.json({ error: 'Empty upstream response stream' }, { status: 502 });
    }

    return new Response(upstreamRes.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache, no-transform',
        Connection: 'keep-alive',
      },
    });
  } catch (error: unknown) {
    console.error('[Reports Stream Proxy Error]:', error);
    const message = error instanceof Error ? error.message : 'Reports stream proxy failed';
    return NextResponse.json(
      { error: message },
      { status: 500 },
    );
  }
}
