import { NextResponse } from 'next/server';
import { requireUserContext } from '@/lib/auth/server';
import { isUuid, parsePositionPatch } from '@/lib/portfolioInput';

type Params = { portfolioId: string; positionId: string };

export async function PATCH(request: Request, { params }: { params: Promise<Params> }) {
  const auth = await requireUserContext(request);
  if (!auth.ok) return auth.response;
  const { portfolioId, positionId } = await params;
  if (!isUuid(portfolioId) || !isUuid(positionId)) {
    return NextResponse.json({ error: 'invalid_position_id' }, { status: 400 });
  }

  try {
    const body = await request.json();
    const patch = parsePositionPatch(body || {});
    if (!patch) return NextResponse.json({ error: 'invalid_position' }, { status: 400 });

    const { data, error } = await auth.context.supabaseUser
      .from('portfolio_positions')
      .update(patch)
      .eq('id', positionId)
      .eq('portfolio_id', portfolioId)
      .select('id,portfolio_id,scheme_code,units,current_value,position_source,created_at,updated_at')
      .maybeSingle();
    if (error) return NextResponse.json({ error: 'portfolio_position_update_failed' }, { status: 500 });
    if (!data) return NextResponse.json({ error: 'position_not_found' }, { status: 404 });
    return NextResponse.json({ position: data });
  } catch (error) {
    console.error('Portfolio position update failed:', error);
    return NextResponse.json({ error: 'invalid_position_request' }, { status: 400 });
  }
}

export async function DELETE(request: Request, { params }: { params: Promise<Params> }) {
  const auth = await requireUserContext(request);
  if (!auth.ok) return auth.response;
  const { portfolioId, positionId } = await params;
  if (!isUuid(portfolioId) || !isUuid(positionId)) {
    return NextResponse.json({ error: 'invalid_position_id' }, { status: 400 });
  }

  const { data, error } = await auth.context.supabaseUser
    .from('portfolio_positions')
    .delete()
    .eq('id', positionId)
    .eq('portfolio_id', portfolioId)
    .select('id')
    .maybeSingle();
  if (error) return NextResponse.json({ error: 'portfolio_position_delete_failed' }, { status: 500 });
  if (!data) return NextResponse.json({ error: 'position_not_found' }, { status: 404 });
  return NextResponse.json({ ok: true });
}
