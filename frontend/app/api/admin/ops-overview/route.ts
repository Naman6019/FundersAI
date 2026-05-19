import { NextResponse } from 'next/server';
import { backendUrl } from '../../quant/proxy';
import { requireAdminFromRequest } from '@/lib/admin/server';

export async function GET(request: Request) {
  const auth = await requireAdminFromRequest(request);
  if (!auth.ok) return auth.response;

  try {
    const internalAdminKey = String(process.env.MF_INTERNAL_ADMIN_KEY || '').trim();
    if (!internalAdminKey) {
      return NextResponse.json({ error: 'Admin backend key missing' }, { status: 500 });
    }

    const res = await fetch(backendUrl('/api/admin/ops-overview'), {
      method: 'GET',
      cache: 'no-store',
      headers: {
        'X-Admin-Key': internalAdminKey,
      },
    });
    const body = await res.json().catch(() => ({ error: 'Invalid backend response' }));
    return NextResponse.json(body, { status: res.status });
  } catch (error) {
    console.error('Admin ops proxy error:', error);
    return NextResponse.json({ error: 'Admin ops backend unavailable' }, { status: 502 });
  }
}
