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

    const targetUrl = `${targetBase.replace(/\/$/, '')}/api/v1/reports/pdf`;

    console.log(`[Reports PDF Proxy] Proxying PDF request to ${targetUrl}`);

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
      console.error(`[Reports PDF Proxy] Upstream returned status ${upstreamRes.status}:`, errText);
      return NextResponse.json(
        { error: 'Failed to generate report PDF' },
        { status: upstreamRes.status },
      );
    }

    const pdfBuffer = await upstreamRes.arrayBuffer();

    return new Response(pdfBuffer, {
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': 'attachment; filename="synthesis-report.pdf"',
      },
    });
  } catch (error: any) {
    console.error('[Reports PDF Proxy Error]:', error);
    return NextResponse.json(
      { error: error?.message || 'Reports PDF proxy failed' },
      { status: 500 },
    );
  }
}
