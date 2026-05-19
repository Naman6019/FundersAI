import { NextResponse } from 'next/server';
import { monthStartIso, readNumber, requireAdminFromRequest, utcDayStartIso } from '@/lib/admin/server';

type UserFilter = 'all' | 'free' | 'pro' | 'admin' | 'tester';

function normalizeFilter(value: string | null): UserFilter {
  const raw = String(value || 'all').toLowerCase();
  if (raw === 'free' || raw === 'pro' || raw === 'admin' || raw === 'tester') return raw;
  return 'all';
}

export async function GET(request: Request) {
  const auth = await requireAdminFromRequest(request);
  if (!auth.ok) return auth.response;

  const supabase = auth.context.supabaseAdmin;
  if (!supabase) {
    return NextResponse.json({ error: 'Supabase service role key is missing' }, { status: 500 });
  }

  const { searchParams } = new URL(request.url);
  const filter = normalizeFilter(searchParams.get('filter'));
  const dayStart = utcDayStartIso();
  const monthStart = monthStartIso();

  const profilesRes = await supabase
    .from('user_profiles')
    .select('user_id,role,tier,created_at,last_active_at,updated_at')
    .order('created_at', { ascending: false })
    .limit(5000);
  const profiles = profilesRes.data || [];

  const profileRows = profiles.filter((row) => {
    if (filter === 'all') return true;
    if (filter === 'free' || filter === 'pro') return row.tier === filter;
    return row.role === filter;
  });

  const usageRowsRes = await supabase
    .from('provider_usage_logs')
    .select('user_id,request_cost,created_at')
    .gte('created_at', monthStart)
    .limit(100000);
  const usageRows = usageRowsRes.data || [];

  const byUserMonthTokens = new Map<string, number>();
  const byUserTodayRequests = new Map<string, number>();
  for (const row of usageRows) {
    const userId = String(row.user_id || '').trim();
    if (!userId) continue;
    byUserMonthTokens.set(userId, (byUserMonthTokens.get(userId) || 0) + readNumber(row.request_cost));
    if ((row.created_at || '') >= dayStart) {
      byUserTodayRequests.set(userId, (byUserTodayRequests.get(userId) || 0) + 1);
    }
  }

  let emailMap = new Map<string, string>();
  try {
    const authUsersRes = await supabase.auth.admin.listUsers({
      page: 1,
      perPage: 2000,
    });
    const users = authUsersRes.data?.users || [];
    emailMap = new Map(users.map((u) => [u.id, u.email || '']));
  } catch {
    emailMap = new Map();
  }

  const rows = profileRows.map((profile) => {
    const userId = String(profile.user_id);
    const tier = String(profile.tier || 'free');
    return {
      user_id: userId,
      email: emailMap.get(userId) || null,
      role: profile.role || 'user',
      tier,
      created_at: profile.created_at || null,
      last_active_at: profile.last_active_at || null,
      requests_today: byUserTodayRequests.get(userId) || 0,
      monthly_tokens: byUserMonthTokens.get(userId) || 0,
      subscription_status: tier === 'pro' ? 'active' : 'free',
    };
  });

  return NextResponse.json({
    status: 'ok',
    filter,
    checked_at: new Date().toISOString(),
    users: rows,
    count: rows.length,
    actions: {
      mode: 'read_only',
      todo: [
        'change_role',
        'change_tier',
        'reset_usage',
      ],
    },
  });
}

