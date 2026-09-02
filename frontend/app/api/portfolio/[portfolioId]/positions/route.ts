import { NextResponse } from 'next/server';
import { requireUserContext, type UserContext } from '@/lib/auth/server';
import { isUuid, parsePositionInput } from '@/lib/portfolioInput';

type Params = { portfolioId: string };

async function ownedPortfolio(context: UserContext, portfolioId: string) {
  return context.supabaseUser
    .from('portfolios')
    .select('id')
    .eq('id', portfolioId)
    .maybeSingle();
}

export async function GET(request: Request, { params }: { params: Promise<Params> }) {
  const auth = await requireUserContext(request);
  if (!auth.ok) return auth.response;
  const { portfolioId } = await params;
  if (!isUuid(portfolioId)) return NextResponse.json({ error: 'invalid_portfolio_id' }, { status: 400 });

  const { data: portfolio, error: portfolioError } = await ownedPortfolio(auth.context, portfolioId);
  if (portfolioError || !portfolio) return NextResponse.json({ error: 'portfolio_not_found' }, { status: 404 });

  const { data, error } = await auth.context.supabaseUser
    .from('portfolio_positions')
    .select('id,portfolio_id,scheme_code,units,current_value,position_source,created_at,updated_at')
    .eq('portfolio_id', portfolioId)
    .order('created_at', { ascending: true });
  if (error) return NextResponse.json({ error: 'portfolio_positions_read_failed' }, { status: 500 });
  return NextResponse.json({ positions: data || [] });
}

export async function POST(request: Request, { params }: { params: Promise<Params> }) {
  const auth = await requireUserContext(request);
  if (!auth.ok) return auth.response;
  const { portfolioId } = await params;
  if (!isUuid(portfolioId)) return NextResponse.json({ error: 'invalid_portfolio_id' }, { status: 400 });

  const { data: portfolio, error: portfolioError } = await ownedPortfolio(auth.context, portfolioId);
  if (portfolioError || !portfolio) return NextResponse.json({ error: 'portfolio_not_found' }, { status: 404 });

  try {
    const body = await request.json();
    const position = parsePositionInput(body || {});
    if (!position) {
      return NextResponse.json({ error: 'invalid_position' }, { status: 400 });
    }

    const { data, error } = await auth.context.supabaseUser
      .from('portfolio_positions')
      .insert({ portfolio_id: portfolioId, ...position, position_source: 'manual' })
      .select('id,portfolio_id,scheme_code,units,current_value,position_source,created_at,updated_at')
      .single();
    if (error || !data) {
      if (error?.code === '23505') return NextResponse.json({ error: 'position_already_exists' }, { status: 409 });
      console.error('Portfolio position create failed:', error);
      return NextResponse.json({ error: 'portfolio_position_create_failed' }, { status: 500 });
    }
    return NextResponse.json({ position: data }, { status: 201 });
  } catch (error) {
    console.error('Portfolio position request failed:', error);
    return NextResponse.json({ error: 'invalid_position_request' }, { status: 400 });
  }
}
