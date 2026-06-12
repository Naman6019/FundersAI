import { NextResponse } from 'next/server';
import { monthStartIso, readNumber, requireAdminFromRequest, utcDayStartIso } from '@/lib/admin/server';

type UsageEvent = {
  created_at: string;
  provider?: string | null;
  model?: string | null;
  feature?: string | null;
  user_id?: string | null;
  success?: boolean | null;
  total_tokens?: number | null;
  request_cost?: number | null;
  endpoint?: string | null;
};

function dayKey(iso: string): string {
  return (iso || '').slice(0, 10);
}

export async function GET(request: Request) {
  const auth = await requireAdminFromRequest(request);
  if (!auth.ok) return auth.response;

  const supabase = auth.context.supabaseAdmin;
  if (!supabase) {
    return NextResponse.json({ error: 'Supabase service role key is missing' }, { status: 500 });
  }

  const dayStart = utcDayStartIso();
  const monthStart = monthStartIso();

  let monthRows: UsageEvent[] = [];
  let todayRows: UsageEvent[] = [];

  const monthRes = await supabase
    .from('ai_usage_events')
    .select('created_at,provider,model,feature,user_id,success,total_tokens')
    .gte('created_at', monthStart)
    .limit(100000);
  if (monthRes.error) {
    return NextResponse.json({ error: 'ai_usage_events_unavailable' }, { status: 500 });
  }
  monthRows = (monthRes.data || []) as UsageEvent[];

  const todayRes = await supabase
    .from('ai_usage_events')
    .select('created_at,provider,model,feature,user_id,success,total_tokens')
    .gte('created_at', dayStart)
    .limit(20000);
  if (todayRes.error) {
    return NextResponse.json({ error: 'ai_usage_events_unavailable' }, { status: 500 });
  }
  todayRows = (todayRes.data || []) as UsageEvent[];

  const requestsToday = todayRows.length;
  const requestsMonth = monthRows.length;
  const tokensToday = todayRows.reduce((sum, row) => sum + readNumber(row.total_tokens), 0);
  const tokensMonth = monthRows.reduce((sum, row) => sum + readNumber(row.total_tokens), 0);
  const failedCallsToday = todayRows.filter((row) => row.success === false).length;

  const usageByProvider = new Map<string, { requests: number; tokens: number; failed: number }>();
  const usageByModel = new Map<string, { requests: number; tokens: number; failed: number }>();
  const usageByFeature = new Map<string, { requests: number; tokens: number; failed: number }>();
  const usageByDay = new Map<string, { requests: number; tokens: number; failed: number }>();
  const usageByUser = new Map<string, { requests: number; tokens: number; failed: number }>();

  for (const row of monthRows) {
    const provider = String(row.provider || 'unknown');
    const model = String(row.model || 'unknown');
    const feature = String(row.feature || 'unknown');
    const dateKey = dayKey(row.created_at || '');
    const userId = String(row.user_id || 'unknown');
    const tokens = readNumber(row.total_tokens);
    const failed = row.success === false ? 1 : 0;

    const apply = (map: Map<string, { requests: number; tokens: number; failed: number }>, key: string) => {
      const bucket = map.get(key) || { requests: 0, tokens: 0, failed: 0 };
      bucket.requests += 1;
      bucket.tokens += tokens;
      bucket.failed += failed;
      map.set(key, bucket);
    };

    apply(usageByProvider, provider);
    apply(usageByModel, model);
    apply(usageByFeature, feature);
    apply(usageByDay, dateKey || 'unknown');
    apply(usageByUser, userId);
  }

  const toRows = (map: Map<string, { requests: number; tokens: number; failed: number }>, keyName: string) =>
    Array.from(map.entries())
      .map(([key, value]) => ({ [keyName]: key, ...value }))
      .sort((a, b) => b.tokens - a.tokens);

  return NextResponse.json({
    status: 'ok',
    checked_at: new Date().toISOString(),
    source_table: 'ai_usage_events',
    token_mode: 'actual',
    todo_notes: [],
    summary: {
      requests_today: requestsToday,
      requests_month: requestsMonth,
      tokens_today: tokensToday,
      tokens_month: tokensMonth,
      failed_calls_today: failedCallsToday,
    },
    requests_over_time: toRows(usageByDay, 'day'),
    usage_by_provider: toRows(usageByProvider, 'provider'),
    usage_by_model: toRows(usageByModel, 'model'),
    usage_by_feature: toRows(usageByFeature, 'feature'),
    top_users_by_tokens_month: toRows(usageByUser, 'user_id').slice(0, 20),
  });
}
