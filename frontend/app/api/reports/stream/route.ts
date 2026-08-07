import { NextResponse } from 'next/server';
import { getClientIp } from '@/lib/rateLimit';

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const targetBase =
      process.env.REPORTS_MICROSERVICE_URL ||
      process.env.REPORTS_API_URL ||
      process.env.BACKEND_API_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      (process.env.NODE_ENV === 'development' ? 'http://127.0.0.1:8001' : 'http://127.0.0.1:8000');

    const targetUrl = `${targetBase.replace(/\/$/, '')}/api/v1/reports/stream`;

    console.log(`[Reports Stream Proxy] Proxying report request to ${targetUrl}`);

    const upstreamRes = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Forwarded-For': getClientIp(req),
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
  } catch (error: any) {
    console.error('[Reports Stream Proxy Error]:', error);
    return NextResponse.json(
      { error: error?.message || 'Reports stream proxy failed' },
      { status: 500 },
    );
  }
}
