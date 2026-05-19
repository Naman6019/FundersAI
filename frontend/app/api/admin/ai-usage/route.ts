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

  let sourceTable = 'ai_usage_events';
  let tokenMode: 'actual' | 'proxy' = 'actual';
  let monthRows: UsageEvent[] = [];
  let todayRows: UsageEvent[] = [];
  const todoNotes: string[] = [];

  try {
    const monthRes = await supabase
      .from('ai_usage_events')
      .select('created_at,provider,model,feature,user_id,success,total_tokens')
      .gte('created_at', monthStart)
      .limit(100000);
    monthRows = (monthRes.data || []) as UsageEvent[];

    const todayRes = await supabase
      .from('ai_usage_events')
      .select('created_at,provider,model,feature,user_id,success,total_tokens')
      .gte('created_at', dayStart)
      .limit(20000);
    todayRows = (todayRes.data || []) as UsageEvent[];
  } catch {
    sourceTable = 'provider_usage_logs';
    tokenMode = 'proxy';
    todoNotes.push('TODO: ai_usage_events table missing; tokens are proxied from request_cost.');

    const monthRes = await supabase
      .from('provider_usage_logs')
      .select('created_at,provider,endpoint,user_id,success,request_cost')
      .gte('created_at', monthStart)
      .limit(100000);
    monthRows = (monthRes.data || []).map((row) => ({
      ...row,
      feature: row.endpoint || 'unknown',
      model: 'unknown',
      total_tokens: readNumber(row.request_cost),
    })) as UsageEvent[];

    const todayRes = await supabase
      .from('provider_usage_logs')
      .select('created_at,provider,endpoint,user_id,success,request_cost')
      .gte('created_at', dayStart)
      .limit(20000);
    todayRows = (todayRes.data || []).map((row) => ({
      ...row,
      feature: row.endpoint || 'unknown',
      model: 'unknown',
      total_tokens: readNumber(row.request_cost),
    })) as UsageEvent[];
  }

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
    source_table: sourceTable,
    token_mode: tokenMode,
    todo_notes: todoNotes,
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
