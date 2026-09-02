import { NextResponse } from 'next/server';
import { requireUserContext } from '@/lib/auth/server';
import { buildPortfolioSnapshots, type PortfolioPositionRow, type PortfolioRow } from '@/lib/portfolioTracking';
import { parsePortfolioName } from '@/lib/portfolioInput';

function storageError(error: { code?: string } | null | undefined): NextResponse {
  const unavailable = error?.code === 'PGRST205' || error?.code === '42P01';
  return NextResponse.json(
    { error: unavailable ? 'portfolio_storage_unavailable' : 'portfolio_read_failed' },
    { status: unavailable ? 503 : 500 },
  );
}

export async function GET(request: Request) {
  const auth = await requireUserContext(request);
  if (!auth.ok) return auth.response;

  try {
    const { data: portfolios, error: portfolioError } = await auth.context.supabaseUser
      .from('portfolios')
      .select('id,name,created_at,updated_at')
      .order('created_at', { ascending: true });
    if (portfolioError) return storageError(portfolioError);

    const portfolioRows = (portfolios || []) as PortfolioRow[];
    const ids = portfolioRows.map((portfolio) => portfolio.id);
    let positionRows: PortfolioPositionRow[] = [];
    if (ids.length) {
      const { data: positions, error: positionError } = await auth.context.supabaseUser
        .from('portfolio_positions')
        .select('id,portfolio_id,scheme_code,units,current_value,position_source,created_at,updated_at')
        .in('portfolio_id', ids)
        .order('created_at', { ascending: true });
      if (positionError) return storageError(positionError);
      positionRows = (positions || []) as PortfolioPositionRow[];
    }

    const snapshots = await buildPortfolioSnapshots(
      portfolioRows,
      positionRows,
      auth.context.supabaseAdmin,
    );
    return NextResponse.json({ portfolios: snapshots });
  } catch (error) {
    console.error('Portfolio read failed:', error);
    return NextResponse.json({ error: 'portfolio_read_failed' }, { status: 500 });
  }
}

export async function POST(request: Request) {
  const auth = await requireUserContext(request);
  if (!auth.ok) return auth.response;

  try {
    const body = await request.json().catch(() => ({}));
    const name = parsePortfolioName(body?.name);
    if (!name) {
      return NextResponse.json({ error: 'invalid_portfolio_name' }, { status: 400 });
    }

    const { data, error } = await auth.context.supabaseUser
      .from('portfolios')
      .insert({ user_id: auth.context.user.id, name })
      .select('id,name,created_at,updated_at')
      .single();
    if (error || !data) {
      if (error?.code === 'PGRST205' || error?.code === '42P01') return storageError(error);
      console.error('Portfolio create failed:', error);
      return NextResponse.json({ error: 'portfolio_create_failed' }, { status: 500 });
    }

    return NextResponse.json({ portfolio: data }, { status: 201 });
  } catch (error) {
    console.error('Portfolio create request failed:', error);
    return NextResponse.json({ error: 'invalid_portfolio_request' }, { status: 400 });
  }
}
