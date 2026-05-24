import { NextResponse } from 'next/server';
import { requireAdminFromRequest } from '@/lib/admin/server';
import { backendUrl } from '../../../../../quant/proxy';
import { enforceRateLimit, getClientIp } from '@/lib/rateLimit';

type RouteContext = {
  params: Promise<{ documentId: string }>;
};

export async function POST(request: Request, context: RouteContext) {
  const auth = await requireAdminFromRequest(request);
  if (!auth.ok) return auth.response;

  const limited = await enforceRateLimit(request, 'admin-mutation', { identifier: auth.context.user.id });
  if (limited) return limited;

  const { documentId } = await context.params;
  const internalAdminKey = String(process.env.MF_INTERNAL_ADMIN_KEY || '').trim();
  if (!internalAdminKey) {
    return NextResponse.json({ error: 'Admin backend key missing' }, { status: 500 });
  }

  try {
    const res = await fetch(backendUrl(`/api/admin/mf-documents/${encodeURIComponent(documentId)}/request-reparse`), {
      method: 'POST',
      cache: 'no-store',
      headers: {
        'Content-Type': 'application/json',
        'X-Admin-Key': internalAdminKey,
        'X-Forwarded-For': getClientIp(request),
      },
      body: JSON.stringify({ reviewer_notes: 'Requested from admin data coverage.' }),
    });
    const body = await res.json().catch(() => ({ error: 'Invalid backend response' }));
    return NextResponse.json(body, { status: res.status });
  } catch {
    return NextResponse.json({ error: 'Admin action backend unavailable' }, { status: 502 });
  }
}
