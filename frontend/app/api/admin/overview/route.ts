import { NextResponse } from 'next/server';
import { monthStartIso, readNumber, requireAdminFromRequest, utcDayStartIso } from '@/lib/admin/server';

type StatusBadge = 'Fresh' | 'Stale' | 'Error' | 'Partial' | 'Active' | 'Planned' | 'Failing';

export async function GET(request: Request) {
  const auth = await requireAdminFromRequest(request);
  if (!auth.ok) return auth.response;

  const supabase = auth.context.supabaseAdmin;
  if (!supabase) {
    return NextResponse.json({ error: 'Supabase service role key is missing' }, { status: 500 });
  }

  const now = new Date();
  const dayStart = utcDayStartIso(now);
  const monthStart = monthStartIso(now);

  const usersRes = await supabase
    .from('user_profiles')
    .select('user_id,role,tier,last_active_at,created_at', { count: 'exact' })
    .limit(10000);
  const users = usersRes.data || [];
  const totalUsers = Number(usersRes.count || users.length || 0);
  const freeUsers = users.filter((u) => u.tier === 'free').length;
  const proUsers = users.filter((u) => u.tier === 'pro').length;
  const adminTesterUsers = users.filter((u) => u.role === 'admin' || u.role === 'tester').length;
  const activeUsersTodayByProfile = users.filter((u) => (u.last_active_at || '') >= dayStart).length;

  let activeUsersTodayByUsage = 0;
  const usageTodayRowsRes = await supabase
    .from('provider_usage_logs')
    .select('user_id,request_cost,success,created_at')
    .gte('created_at', dayStart)
    .limit(20000);
  const usageTodayRows = usageTodayRowsRes.data || [];
  if (usageTodayRows.length) {
    const unique = new Set(usageTodayRows.map((row) => row.user_id).filter(Boolean));
    activeUsersTodayByUsage = unique.size;
  }
  const activeUsersToday = Math.max(activeUsersTodayByProfile, activeUsersTodayByUsage);

  const monthUsageRowsRes = await supabase
    .from('provider_usage_logs')
    .select('request_cost,success,created_at')
    .gte('created_at', monthStart)
    .limit(50000);
  const monthUsageRows = monthUsageRowsRes.data || [];

  const aiRequestsToday = usageTodayRows.length;
  const aiRequestsMonth = monthUsageRows.length;
  const tokensToday = usageTodayRows.reduce((sum, row) => sum + readNumber(row.request_cost), 0);
  const tokensMonth = monthUsageRows.reduce((sum, row) => sum + readNumber(row.request_cost), 0);
  const failedAiCallsToday = usageTodayRows.filter((row) => row.success === false).length;

  const fundsRes = await supabase
    .from('mutual_fund_core_snapshot')
    .select('scheme_code,amc_name,nav_date,return_1y,aum,expense_ratio,alpha,beta,sharpe_ratio')
    .limit(10000);
  const funds = fundsRes.data || [];
  const totalFunds = funds.length;
  const todayDate = new Date();
  const freshCutoff = new Date(todayDate.getTime() - 4 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  const staleCutoff = new Date(todayDate.getTime() - 10 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);

  const fundsWithFreshNav = funds.filter((row) => row.nav_date && row.nav_date >= freshCutoff).length;
  const fundsWithStaleNav = funds.filter((row) => !row.nav_date || row.nav_date < staleCutoff).length;
  const fundsWithInsufficientHistory = funds.filter((row) => row.return_1y === null || row.return_1y === undefined).length;

  const amcSet = new Set(funds.map((row) => String(row.amc_name || '').trim()).filter(Boolean));
  const amcSourcesRes = await supabase
    .from('mf_amc_sources')
    .select('amc_code,is_enabled,created_at,updated_at')
    .limit(200);
  const amcSources = amcSourcesRes.data || [];
  const amcsCovered = amcSet.size;
  const amcsPlannedPartial = amcSources.filter((row) => row.is_enabled !== true).length;

  const navRunsRes = await supabase
    .from('data_provider_runs')
    .select('provider,job_name,status,started_at,finished_at,error_summary,metadata')
    .ilike('job_name', '%mf%')
    .order('started_at', { ascending: false })
    .limit(30);
  const navRuns = navRunsRes.data || [];
  const latestNavRun = navRuns[0] || null;
  const failedProviderRuns = navRuns.filter((row) => String(row.status || '').toLowerCase().includes('fail')).length;

  const latestParserRes = await supabase
    .from('mf_raw_documents')
    .select('downloaded_at,parsed_at,parse_status')
    .order('downloaded_at', { ascending: false })
    .limit(1);
  const latestParserRun = (latestParserRes.data || [])[0] || null;

  const criticalAlerts: Array<{ id: string; label: string; status: StatusBadge; detail: string }> = [];
  if (fundsWithInsufficientHistory > 0) {
    criticalAlerts.push({
      id: 'low-history',
      label: 'Funds with <252 NAV rows (estimated)',
      status: 'Partial',
      detail: `${fundsWithInsufficientHistory} funds need deeper history.`,
    });
  }
  if (fundsWithStaleNav > 0) {
    criticalAlerts.push({
      id: 'stale-nav',
      label: 'Stale NAV data',
      status: 'Stale',
      detail: `${fundsWithStaleNav} funds have stale or missing latest NAV date.`,
    });
  }
  if (failedProviderRuns > 0) {
    criticalAlerts.push({
      id: 'failed-sync',
      label: 'Failed NAV/provider runs',
      status: 'Failing',
      detail: `${failedProviderRuns} recent MF-related provider runs failed.`,
    });
  }
  if (failedAiCallsToday > 0) {
    criticalAlerts.push({
      id: 'failed-ai',
      label: 'Failed AI provider calls today',
      status: 'Error',
      detail: `${failedAiCallsToday} provider usage calls failed today.`,
    });
  }
  criticalAlerts.push({
    id: 'resolver-ambiguity',
    label: 'Resolver ambiguity monitor',
    status: 'Partial',
    detail: 'Use Resolver Debug page for ICICI/Parag ambiguity checks (detailed conflict log table is TODO).',
  });

  return NextResponse.json({
    status: 'ok',
    checked_at: new Date().toISOString(),
    cards: {
      users: {
        total_users: totalUsers,
        active_users_today: activeUsersToday,
        free_users: freeUsers,
        pro_users: proUsers,
        admin_tester_users: adminTesterUsers,
      },
      ai_usage: {
        ai_requests_today: aiRequestsToday,
        ai_requests_month: aiRequestsMonth,
        tokens_today: tokensToday,
        tokens_month: tokensMonth,
        failed_ai_calls_today: failedAiCallsToday,
        token_note: 'TODO: request_cost is currently used as token proxy from provider_usage_logs.',
      },
      data: {
        total_funds: totalFunds,
        funds_with_fresh_nav: fundsWithFreshNav,
        funds_with_stale_nav: fundsWithStaleNav,
        funds_with_insufficient_nav_history: fundsWithInsufficientHistory,
        amcs_covered: amcsCovered,
        amcs_planned_partial: amcsPlannedPartial,
      },
      sync_health: {
        latest_nav_sync_status: latestNavRun?.status || 'unknown',
        latest_nav_sync_time: latestNavRun?.finished_at || latestNavRun?.started_at || null,
        latest_amc_parser_run: latestParserRun?.parsed_at || latestParserRun?.downloaded_at || null,
        failed_provider_runs: failedProviderRuns,
      },
    },
    critical_alerts: criticalAlerts,
    latest_nav_run: latestNavRun,
    latest_parser_run: latestParserRun,
  });
}
