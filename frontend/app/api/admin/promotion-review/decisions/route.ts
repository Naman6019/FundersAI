import { NextResponse } from 'next/server';
import { requireAdminFromRequest } from '@/lib/admin/server';
import { backendUrl } from '../../../quant/proxy';
import { enforceRateLimit, getClientIp } from '@/lib/rateLimit';

export async function POST(request: Request) {
  const auth = await requireAdminFromRequest(request);
  if (!auth.ok) return auth.response;

  const limited = await enforceRateLimit(request, 'admin-mutation', { identifier: auth.context.user.id });
  if (limited) return limited;

  const internalAdminKey = String(process.env.MF_INTERNAL_ADMIN_KEY || '').trim();
  if (!internalAdminKey) {
    return NextResponse.json({ error: 'Admin backend key missing' }, { status: 500 });
  }

  const body = await request.json().catch(() => null);
  if (!body) {
    return NextResponse.json({ error: 'Invalid request body' }, { status: 400 });
  }

  try {
    const res = await fetch(backendUrl('/api/admin/mf-promotion-review/decisions'), {
      method: 'POST',
      cache: 'no-store',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Key': internalAdminKey,
        'X-Forwarded-For': getClientIp(request),
      },
      body: JSON.stringify({ ...body, reviewed_by: auth.context.user.email || auth.context.user.id }),
    });
    const responseBody = await res.json().catch(() => ({ error: 'Invalid backend response' }));
    return NextResponse.json(responseBody, { status: res.status });
  } catch {
    return NextResponse.json({ error: 'Admin action backend unavailable' }, { status: 502 });
  }
}
