import { NextResponse } from 'next/server';
import { requireAdminFromRequest } from '@/lib/admin/server';
import { backendUrl } from '../../../quant/proxy';

export async function GET(request: Request) {
  const auth = await requireAdminFromRequest(request);
  if (!auth.ok) return auth.response;

  const { searchParams } = new URL(request.url);
  const amc = searchParams.get('amc') || '';
  const scope = searchParams.get('scope') || '';
  const reportMonth = searchParams.get('report_month') || '';

  const internalAdminKey = String(process.env.MF_INTERNAL_ADMIN_KEY || '').trim();
  if (!internalAdminKey) {
    return NextResponse.json({ error: 'Admin backend key missing' }, { status: 500 });
  }

  try {
    const query = new URLSearchParams({ amc, scope, report_month: reportMonth }).toString();
    const res = await fetch(backendUrl(`/api/admin/mf-promotion-review/flags?${query}`), {
      method: 'GET',
      cache: 'no-store',
      headers: { 'X-Admin-Key': internalAdminKey },
    });
    const body = await res.json().catch(() => ({ error: 'Invalid backend response' }));
    return NextResponse.json(body, { status: res.status });
  } catch {
    return NextResponse.json({ error: 'Admin action backend unavailable' }, { status: 502 });
  }
}
