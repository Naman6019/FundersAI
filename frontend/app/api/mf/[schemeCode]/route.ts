import { NextResponse } from 'next/server';
import { supabase } from '@/lib/supabase';
import { calculateCAGR, calculateRiskMetrics } from '@/lib/mf/returns';

export const dynamic = 'force-dynamic';

type MfPoint = { date: string; value: number };
type MfPayload = {
  details: Record<string, unknown>;
  chartData: MfPoint[];
  fullData?: MfPoint[];
  returns?: Record<string, number | null>;
  riskMetrics?: Record<string, number | null>;
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

async function fetchFromBackend(schemeCode: string) {
  const target = process.env.NODE_ENV === 'development'
    ? `http://127.0.0.1:8000/api/mf/${schemeCode}`
    : `${process.env.NEXT_PUBLIC_API_URL}/api/mf/${schemeCode}`;

  try {
    const res = await fetch(target, { cache: 'no-store' });
    if (!res.ok) return null;
    const json = await res.json();
    if (!isMfPayload(json)) return null;
    return json;
  } catch {
    return null;
  }
}

export async function GET(_request: Request, context: { params: Promise<{ schemeCode: string }>}) {
  const { schemeCode } = await context.params;
  if (!/^\d+$/.test(schemeCode)) {
    return NextResponse.json({ error: 'Invalid scheme code' }, { status: 400 });
  }

  try {
    // Primary source: backend API uses the same DB path as chat resolution.
    const backendJson = await fetchFromBackend(schemeCode);
    if (backendJson) {
      // Enrich backend payload with local full history when backend fullData is short/missing.
      const historyQuery = await supabase
        .from('mutual_fund_nav_history')
        .select('nav, nav_date')
        .eq('scheme_code', schemeCode)
        .order('nav_date', { ascending: false });
      const localHistory = (historyQuery.data || []) as HistoryRow[];
      const localFullData = toFullData(localHistory);
      const backendFullData = Array.isArray(backendJson.fullData) ? backendJson.fullData : [];

      if (localFullData.length > backendFullData.length) {
        const merged: MfPayload = {
          ...backendJson,
          fullData: localFullData,
          chartData: localFullData.slice(0, 250).reverse(),
        };
        const computed = buildMetricsFromFullData(localFullData);
        if (!merged.returns) merged.returns = computed.returns;
        if (!merged.riskMetrics && computed.riskMetrics) {
          merged.riskMetrics = computed.riskMetrics as Record<string, number | null>;
        }
        return NextResponse.json(merged);
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

    const historyQuery = await supabase
      .from('mutual_fund_nav_history')
      .select('nav, nav_date')
      .eq('scheme_code', schemeCode)
      .order('nav_date', { ascending: false });
    const localHistory = historyQuery.data;

    const fullData = toFullData((localHistory || []) as HistoryRow[]);
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

    // Filter last 365 days of NAV history for charting
    const recentHistory = fullData.slice(0, 250).reverse();

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
      fullData
    });

  } catch (error) {
    return NextResponse.json({ error: (error as Error).message }, { status: 500 });
  }
}
