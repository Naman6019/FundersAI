import { NextResponse } from 'next/server';
import { requireAdminFromRequest } from '@/lib/admin/server';

export async function GET(request: Request) {
  const auth = await requireAdminFromRequest(request);
  if (!auth.ok) return auth.response;

  return NextResponse.json({
    status: 'ok',
    user: auth.context.user,
    profile: auth.context.profile,
  });
}

