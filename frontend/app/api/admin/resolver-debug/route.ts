import { NextResponse } from 'next/server';
import { requireAdminFromRequest } from '@/lib/admin/server';
import { backendUrl } from '../../quant/proxy';

export async function GET(request: Request) {
  const auth = await requireAdminFromRequest(request);
  if (!auth.ok) return auth.response;

  const { searchParams } = new URL(request.url);
  const query = String(searchParams.get('query') || '').trim();
  const horizon = String(searchParams.get('horizon') || '3Y').toUpperCase();
  if (!query) {
    return NextResponse.json({ error: 'query is required' }, { status: 400 });
  }

  const internalAdminKey = String(process.env.MF_INTERNAL_ADMIN_KEY || '').trim();
  if (!internalAdminKey) {
    return NextResponse.json({ error: 'Internal admin key is not configured' }, { status: 500 });
  }

  try {
    const backendResponse = await fetch(
      backendUrl(`/api/admin/mf-resolver-debug?query=${encodeURIComponent(query)}&horizon=${encodeURIComponent(horizon)}`),
      {
        method: 'GET',
        cache: 'no-store',
        headers: {
          'X-Admin-Key': internalAdminKey,
        },
      },
    );
    const payload = await backendResponse.json().catch(() => ({ error: 'Invalid backend response' }));
    return NextResponse.json(payload, { status: backendResponse.status });
  } catch {
    return NextResponse.json({ error: 'Resolver debug backend unavailable' }, { status: 502 });
  }
}

