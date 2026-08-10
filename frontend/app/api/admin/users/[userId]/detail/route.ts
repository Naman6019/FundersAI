import { NextResponse } from 'next/server';
import { requireAdminFromRequest } from '@/lib/admin/server';

type RouteContext = {
  params: Promise<{ userId: string }>;
};

export async function GET(request: Request, context: RouteContext) {
  const auth = await requireAdminFromRequest(request);
  if (!auth.ok) return auth.response;

  const supabase = auth.context.supabaseAdmin;
  if (!supabase) {
    return NextResponse.json({ error: 'Supabase service role key is missing' }, { status: 500 });
  }

  const { userId } = await context.params;
  if (!userId) {
    return NextResponse.json({ error: 'userId is required' }, { status: 400 });
  }

  const since90d = new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString();

  const [usageRes, feedbackRes] = await Promise.all([
    supabase
      .from('ai_usage_events')
      .select('created_at,provider,model,feature,success,total_tokens')
      .eq('user_id', userId)
      .gte('created_at', since90d)
      .order('created_at', { ascending: false })
      .limit(500),
    supabase
      .from('user_feedback')
      .select('id,feedback_type,rating,comment,page_path,response_excerpt,created_at')
      .eq('user_id', userId)
      .order('created_at', { ascending: false })
      .limit(200),
  ]);

  const usageRows = usageRes.data || [];
  const feedbackRows = feedbackRes.data || [];

  const byDay = new Map<string, { requests: number; tokens: number; failed: number }>();
  for (const row of usageRows) {
    const day = String(row.created_at || '').slice(0, 10);
    if (!day) continue;
    const bucket = byDay.get(day) || { requests: 0, tokens: 0, failed: 0 };
    bucket.requests += 1;
    bucket.tokens += Number(row.total_tokens) || 0;
    if (row.success === false) bucket.failed += 1;
    byDay.set(day, bucket);
  }
  const usage_by_day = Array.from(byDay.entries())
    .map(([day, bucket]) => ({ day, ...bucket }))
    .sort((a, b) => a.day.localeCompare(b.day));

  return NextResponse.json({
    status: 'ok',
    user_id: userId,
    window_days: 90,
    usage_summary: {
      total_requests: usageRows.length,
      total_tokens: usageRows.reduce((sum, row) => sum + (Number(row.total_tokens) || 0), 0),
      total_failed: usageRows.filter((row) => row.success === false).length,
    },
    usage_by_day,
    usage_events: usageRows.slice(0, 100),
    feedback: feedbackRows,
    feedback_count: feedbackRows.length,
  });
}
