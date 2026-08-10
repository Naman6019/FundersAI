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
  const decisionId = String((body as { decision_id?: string } | null)?.decision_id || '').trim();
  const confirmPhrase = String((body as { confirm_phrase?: string } | null)?.confirm_phrase || '').trim();
  if (!decisionId) {
    return NextResponse.json({ error: 'decision_id is required' }, { status: 400 });
  }
  if (confirmPhrase !== 'PROMOTE') {
    return NextResponse.json({ error: 'Type PROMOTE to confirm this write to production data.' }, { status: 400 });
  }

  try {
    const res = await fetch(backendUrl('/api/admin/mf-promotion-review/promote'), {
      method: 'POST',
      cache: 'no-store',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Key': internalAdminKey,
        'X-Forwarded-For': getClientIp(request),
      },
      body: JSON.stringify({
        decision_id: decisionId,
        requested_by: auth.context.user.email || auth.context.user.id,
      }),
    });
    const responseBody = await res.json().catch(() => ({ error: 'Invalid backend response' }));
    return NextResponse.json(responseBody, { status: res.status });
  } catch {
    return NextResponse.json({ error: 'Admin action backend unavailable' }, { status: 502 });
  }
}
