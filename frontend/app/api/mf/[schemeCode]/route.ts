import { NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';
import { calculateCAGR, calculateRiskMetrics } from '@/lib/mf/returns';
import { enforceRateLimit, getClientIp } from '@/lib/rateLimit';

export const dynamic = 'force-dynamic';

type MfPoint = { date: string; value: number };
type HistoryCoverage = {
  historyPoints: number;
  firstNavDate: string | null;
  lastNavDate: string | null;
  supports: {
    '1Y': boolean;
    '3Y': boolean;
    '5Y': boolean;
  };
};
type MfPayload = {
  details: Record<string, unknown>;
  chartData: MfPoint[];
  fullData?: MfPoint[];
  returns?: Record<string, number | null>;
  riskMetrics?: Record<string, number | null>;
  historyCoverage?: HistoryCoverage;
  [key: string]: unknown;
};

type HistoryRow = { nav: number | string; nav_date: string };

function isMfPayload(value: unknown): value is MfPayload {
  if (!value || typeof value !== 'object') return false;
  const candidate = value as MfPayload;
  return Boolean(candidate.details) && Array.isArray(candidate.chartData);
}

function toDateLabel(navDate: string): string {
  const parts = navDate.split('-');
  if (parts.length !== 3) return navDate;
  return [parts[2], parts[1], parts[0]].join('-');
}

function toFullData(historyRows: HistoryRow[]): MfPoint[] {
  return historyRows
    .map((row) => {
      const value = Number(row.nav);
      if (!Number.isFinite(value)) return null;
      return { date: toDateLabel(row.nav_date), value };
    })
    .filter((row): row is MfPoint => row !== null);
}

function buildMetricsFromFullData(fullData: MfPoint[]) {
  const navHistory = fullData.map((point) => ({
    date: point.date,
    nav: point.value.toString(),
  }));
  return {
    returns: {
      '1Y': calculateCAGR(navHistory, 1),
      '3Y': calculateCAGR(navHistory, 3),
      '5Y': calculateCAGR(navHistory, 5),
    },
    riskMetrics: calculateRiskMetrics(navHistory),
  };
}

function parseDdMmYyyy(dateLabel: string): Date | null {
  const parts = dateLabel.split('-');
  if (parts.length !== 3) return null;
  const day = Number(parts[0]);
  const month = Number(parts[1]);
  const year = Number(parts[2]);
  if (!Number.isFinite(day) || !Number.isFinite(month) || !Number.isFinite(year)) return null;
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function buildHistoryCoverage(fullData: MfPoint[]): HistoryCoverage {
  if (!fullData.length) {
    return {
      historyPoints: 0,
      firstNavDate: null,
      lastNavDate: null,
      supports: { '1Y': false, '3Y': false, '5Y': false },
    };
  }

  const sorted = [...fullData].sort((a, b) => {
    const da = parseDdMmYyyy(a.date)?.getTime() || 0;
    const db = parseDdMmYyyy(b.date)?.getTime() || 0;
    return da - db;
  });
  const first = sorted[0]?.date ?? null;
  const last = sorted[sorted.length - 1]?.date ?? null;
  const firstDate = first ? parseDdMmYyyy(first) : null;
  const lastDate = last ? parseDdMmYyyy(last) : null;
  const spanDays = firstDate && lastDate ? Math.max(Math.floor((lastDate.getTime() - firstDate.getTime()) / (1000 * 60 * 60 * 24)), 0) : 0;

  return {
    historyPoints: sorted.length,
    firstNavDate: first,
    lastNavDate: last,
    supports: {
      '1Y': spanDays >= 365,
      '3Y': spanDays >= 365 * 3,
      '5Y': spanDays >= 365 * 5,
    },
  };
}

async function fetchLocalNavHistory(schemeCode: string): Promise<HistoryRow[]> {
  const fetchRowsForFilter = async (codeFilter: string | number, maxRows = 3000): Promise<HistoryRow[]> => {
    const batchSize = 1000;
    let offset = 0;
    const collected: HistoryRow[] = [];

    while (offset < maxRows) {
      const { data, error } = await supabase
        .from('mutual_fund_nav_history')
        .select('nav, nav_date')
        .eq('scheme_code', codeFilter)
        .order('nav_date', { ascending: false })
        .range(offset, offset + batchSize - 1);
      if (error || !data?.length) break;
      collected.push(...(data as HistoryRow[]));
      if (data.length < batchSize) break;
      offset += batchSize;
    }

    return collected.slice(0, maxRows);
  };

  const stringRows = await fetchRowsForFilter(schemeCode);

  const numericSchemeCode = Number.parseInt(schemeCode, 10);
  if (!Number.isFinite(numericSchemeCode)) return stringRows;

  const numberRows = await fetchRowsForFilter(numericSchemeCode);

  return numberRows.length > stringRows.length ? numberRows : stringRows;
}

async function fetchFromBackend(schemeCode: string, request: Request) {
  const target = process.env.NODE_ENV === 'development'
    ? `http://127.0.0.1:8000/api/mf/${schemeCode}`
    : `${process.env.NEXT_PUBLIC_API_URL}/api/mf/${schemeCode}`;

  try {
    const res = await fetch(target, {
      cache: 'no-store',
      headers: {
        'X-Forwarded-For': getClientIp(request),
      },
    });
    if (!res.ok) return null;
    const json = await res.json();
    if (!isMfPayload(json)) return null;
    return json;
  } catch {
    return null;
  }
}

export async function GET(request: Request, context: { params: Promise<{ schemeCode: string }>}) {
  const { schemeCode } = await context.params;
  const debugNavPipeline = process.env.NODE_ENV === 'development' && process.env.DEBUG_MF_NAV_PIPELINE === '1';
  if (!/^\d+$/.test(schemeCode)) {
    return NextResponse.json({ error: 'Invalid scheme code' }, { status: 400 });
  }

  try {
    const limited = await enforceRateLimit(request, 'mf-detail');
    if (limited) return limited;

    // Primary source: backend API uses the same DB path as chat resolution.
    const backendJson = await fetchFromBackend(schemeCode, request);
    if (backendJson) {
      // Enrich backend payload with local full history when backend fullData is short/missing.
      const localHistory = await fetchLocalNavHistory(schemeCode);
      const localFullData = toFullData(localHistory);
      const backendFullData = Array.isArray(backendJson.fullData) ? backendJson.fullData : [];
      const localCoverage = buildHistoryCoverage(localFullData);
      if (debugNavPipeline) {
        console.log(
          `[mf-pipeline] scheme=${schemeCode} backendPoints=${backendFullData.length} localPoints=${localFullData.length} localFirst=${localCoverage.firstNavDate} localLast=${localCoverage.lastNavDate}`
        );
      }

      if (localFullData.length > backendFullData.length) {
        const merged: MfPayload = {
          ...backendJson,
          fullData: localFullData,
          chartData: localFullData.slice(0, 250).reverse(),
          historyCoverage: localCoverage,
        };
        const computed = buildMetricsFromFullData(localFullData);
        if (!merged.returns) merged.returns = computed.returns;
        if (!merged.riskMetrics && computed.riskMetrics) {
          merged.riskMetrics = computed.riskMetrics as Record<string, number | null>;
        }
        return NextResponse.json(merged);
      }

      if (!backendJson.historyCoverage) {
        const backendCoverage = buildHistoryCoverage(backendFullData);
        return NextResponse.json({
          ...backendJson,
          historyCoverage: backendCoverage,
        });
      }

      return NextResponse.json(backendJson);
    }

    // Fallback: local Supabase query (for local-only runs)
    let detailsQuery = await supabase
      .from('mutual_fund_core_snapshot')
      .select('*')
      .eq('scheme_code', schemeCode)
      .limit(1)
      .maybeSingle();
    if (!detailsQuery.data) {
      detailsQuery = await supabase
        .from('mutual_funds')
        .select('*')
        .eq('scheme_code', parseInt(schemeCode, 10))
        .limit(1)
        .maybeSingle();
    }
    const mfDetails = detailsQuery.data;
    const error = detailsQuery.error;

    if (error || !mfDetails) {
      return NextResponse.json({ error: 'Mutual fund not found' }, { status: 404 });
    }

    const localHistory = await fetchLocalNavHistory(schemeCode);
    const fullData = toFullData(localHistory);
    const history = fullData.map((h) => ({
      date: h.date,
      nav: h.value.toString(),
    }));

    // Calculate returns
    const cagr1Y = calculateCAGR(history, 1);
    const cagr3Y = calculateCAGR(history, 3);
    const cagr5Y = calculateCAGR(history, 5);

    // Calculate risk metrics from full NAV history
    const riskMetrics = calculateRiskMetrics(history);
    const historyCoverage = buildHistoryCoverage(fullData);

    // Filter last 365 days of NAV history for charting
    const recentHistory = fullData.slice(0, 250).reverse();
    if (debugNavPipeline) {
      console.log(
        `[mf-pipeline] local-only scheme=${schemeCode} points=${historyCoverage.historyPoints} first=${historyCoverage.firstNavDate} last=${historyCoverage.lastNavDate}`
      );
    }

    // --- FALLBACK FOR AUM/EXPENSE RATIO ---
    // If they are null in Supabase, we could theoretically fetch them from yfinance here.
    // But since this is a serverless function, we should keep it fast.
    // For now, we will return what we have.

    return NextResponse.json({
      details: mfDetails,
      returns: {
        '1Y': cagr1Y,
        '3Y': cagr3Y,
        '5Y': cagr5Y
      },
      riskMetrics,
      chartData: recentHistory,
      fullData,
      historyCoverage
    });

  } catch (error) {
    return NextResponse.json({ error: (error as Error).message }, { status: 500 });
  }
}
