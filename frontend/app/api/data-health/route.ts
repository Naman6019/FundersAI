import { NextResponse } from 'next/server';
import { backendUrl } from '../quant/proxy';
import { enforceRateLimit, getClientIp } from '@/lib/rateLimit';

export async function GET(request: Request) {
  try {
    const limited = await enforceRateLimit(request, 'data-health');
    if (limited) return limited;

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
          { label: 'Factsheets', status: 'Error', note: 'Proxy request failed.', last_updated: null },
        ],
        checked_at: new Date().toISOString(),
      },
      { status: 502 },
    );
  }
}
