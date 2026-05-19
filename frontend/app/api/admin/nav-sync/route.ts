import { NextResponse } from 'next/server';
import { requireAdminFromRequest } from '@/lib/admin/server';

function readMetaNumber(metadata: unknown, keys: string[]): number {
  if (!metadata || typeof metadata !== 'object') return 0;
  for (const key of keys) {
    const value = Number((metadata as Record<string, unknown>)[key]);
    if (Number.isFinite(value)) return value;
  }
  return 0;
}

export async function GET(request: Request) {
  const auth = await requireAdminFromRequest(request);
  if (!auth.ok) return auth.response;

  const supabase = auth.context.supabaseAdmin;
  if (!supabase) {
    return NextResponse.json({ error: 'Supabase service role key is missing' }, { status: 500 });
  }

  const runsRes = await supabase
    .from('data_provider_runs')
    .select('id,provider,job_name,status,started_at,finished_at,symbols_attempted,symbols_succeeded,symbols_failed,error_summary,metadata')
    .ilike('job_name', '%mf%')
    .order('started_at', { ascending: false })
    .limit(80);
  const rows = runsRes.data || [];

  const navRuns = rows
    .filter((row) => {
      const provider = String(row.provider || '').toLowerCase();
      const job = String(row.job_name || '').toLowerCase();
      return provider.includes('mf') || job.includes('nav') || job.includes('mutual');
    })
    .map((row) => {
      const metadata = row.metadata || {};
      const startedAt = row.started_at || null;
      const finishedAt = row.finished_at || null;
      const durationSeconds = startedAt && finishedAt
        ? Math.max(Math.floor((new Date(finishedAt).getTime() - new Date(startedAt).getTime()) / 1000), 0)
        : null;
      const rowsInserted = readMetaNumber(metadata, ['rows_inserted', 'inserted_rows', 'inserted']);
      const rowsUpdated = readMetaNumber(metadata, ['rows_updated', 'updated_rows', 'updated']);
      const rowsSkipped = readMetaNumber(metadata, ['rows_skipped', 'skipped_rows', 'skipped']);
      const failedSchemes = readMetaNumber(metadata, ['failed_schemes', 'failed_symbols', 'symbols_failed']);

      return {
        id: row.id,
        provider: row.provider || 'unknown',
        source: row.provider || 'unknown',
        job_name: row.job_name || 'unknown',
        status: row.status || 'unknown',
        started_at: startedAt,
        completed_at: finishedAt,
        duration_seconds: durationSeconds,
        rows_processed: Number(row.symbols_attempted || 0),
        rows_inserted: rowsInserted,
        rows_updated: rowsUpdated,
        rows_skipped: rowsSkipped,
        failed_schemes: failedSchemes || Number(row.symbols_failed || 0),
        error_summary: row.error_summary || null,
      };
    });

  const latestRun = navRuns[0] || null;

  const latestNavDateRes = await supabase
    .from('mutual_fund_core_snapshot')
    .select('nav_date')
    .order('nav_date', { ascending: false })
    .limit(1);
  const latestNavDate = (latestNavDateRes.data || [])[0]?.nav_date || null;

  const alerts: Array<{ id: string; severity: 'warning' | 'error'; message: string }> = [];
  const today = new Date();
  const todayIso = today.toISOString().slice(0, 10);
  if (!latestRun || !String(latestRun.started_at || '').startsWith(todayIso)) {
    alerts.push({ id: 'run-not-today', severity: 'warning', message: 'NAV sync has not run today.' });
  }
  if (latestNavDate && latestNavDate < new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10)) {
    alerts.push({ id: 'stale-nav', severity: 'warning', message: `Latest NAV date is stale (${latestNavDate}).` });
  }
  if (latestRun && latestRun.failed_schemes > 25) {
    alerts.push({ id: 'many-failures', severity: 'error', message: `Latest run has many failed schemes (${latestRun.failed_schemes}).` });
  }
  if (latestRun && latestRun.rows_inserted === 0 && latestRun.rows_updated === 0 && latestRun.status && String(latestRun.status).toLowerCase().includes('success')) {
    alerts.push({ id: 'zero-write', severity: 'warning', message: 'Latest successful run inserted/updated 0 rows.' });
  }

  return NextResponse.json({
    status: 'ok',
    checked_at: new Date().toISOString(),
    latest_nav_sync: latestRun,
    latest_nav_date: latestNavDate,
    recent_runs: navRuns,
    alerts,
    actions: {
      run_sync_now: {
        enabled: false,
        reason: 'TODO: enable when a safe backend trigger endpoint is exposed.',
      },
    },
  });
}

