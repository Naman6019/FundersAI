import { NextResponse } from 'next/server';
import { backendUrl } from '../quant/proxy';

export async function GET() {
  try {
    const res = await fetch(backendUrl('/api/data-health'), {
      method: 'GET',
      cache: 'no-store',
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
