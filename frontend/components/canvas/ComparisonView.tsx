'use client';

import { useEffect, useState } from 'react';
import { useFundData } from '../../hooks/useFundData';
import { useBenchmarkData } from '../../hooks/useBenchmarkData';
import FundComparisonChart, { Period } from '../funds/FundComparisonChart';
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { CanvasPayload, MetricValue as SharedMetricValue } from '@/types/funds';
import type { NavPoint } from '@/types/funds';
import { calculateAlpha, calculateBeta } from '@/lib/quantUtils';

type MetricValue = SharedMetricValue;
type FundamentalMetric = Record<string, MetricValue>;
type ComparisonMetric = Record<string, unknown>;
type QuantRecord = Record<string, unknown>;

interface QuantFinancialRow {
  period_type?: string;
  revenue?: MetricValue;
  net_profit?: MetricValue;
}

interface QuantPriceRow {
  date?: string;
  close?: MetricValue;
}

interface QuantResponsePayload {
  comparison?: Record<string, ComparisonMetric>;
  why_better?: WhyBetterPayload;
  verdict_context?: string;
  profiles?: Record<string, QuantRecord>;
  ratios?: Record<string, QuantRecord>;
  financials?: Record<string, QuantFinancialRow[]>;
  shareholding?: Record<string, QuantRecord[]>;
  price_history?: Record<string, QuantPriceRow[]>;
  available?: string[];
}

type StockComparisonMetric = ComparisonMetric & {
  source_summary?: { stale?: boolean };
  fundamentals?: FundamentalMetric;
  price_history?: QuantPriceRow[];
  beta?: MetricValue;
  alpha_vs_nifty?: MetricValue;
};

interface Props {
  ids: string[];
  type: 'STOCK' | 'MUTUAL_FUND';
  auxiliaryData?: CanvasPayload | null;
}

type WhyWinner = {
  entity_id?: string | null;
  entity_name?: string | null;
  asset_type?: string;
  status?: 'winner' | 'tie' | 'insufficient_data' | string;
  score_delta?: number;
};

type WhyConfidence = {
  score?: number;
  label?: string;
};

type WhyFactor = {
  factor?: string;
  weight?: number;
  winner?: string | null;
  coverage?: number;
};

type WhyBetterPayload = {
  winner?: WhyWinner;
  confidence?: WhyConfidence;
  summary?: string;
  factor_results?: WhyFactor[];
  strengths?: string[];
  tradeoffs?: string[];
  data_limitations?: string[];
  source_freshness?: Record<string, {
    source?: string | null;
    stale?: boolean;
    price_date?: string | null;
    nav_date?: string | null;
    snapshot_last_updated?: string | null;
  }>;
  verdict_context?: string;
  holdings_based_reasoning?: { status?: string; reason?: string | null };
};

type MFComparisonRecord = {
  scheme_code?: string | number | null;
  name?: string;
  return_3y?: string | number | null;
  volatility_1y?: string | number | null;
  expense_ratio?: string | number | null;
  aum?: string | number | null;
  beta?: string | number | null;
  alpha?: string | number | null;
  alpha_vs_nifty?: string | number | null;
  sharpe_ratio?: string | number | null;
  max_drawdown_1y?: string | number | null;
};

const formatValue = (value: MetricValue) => {
  if (value === null || value === undefined || value === '' || value === 'N/A') return 'Not available';
  if (typeof value === 'number') return Number.isInteger(value) ? value.toLocaleString('en-IN') : value.toLocaleString('en-IN', { maximumFractionDigits: 2 });
  return value;
};

const formatMarketCap = (value: MetricValue) => {
  if (value === null || value === undefined || value === '' || value === 'N/A') return 'Not available';
  const amount = Number(value);
  if (!Number.isFinite(amount)) return String(value);
  if (amount >= 1_00_00_00_00_000) return `₹${(amount / 1_00_00_00_00_000).toFixed(2)} lakh crore`;
  if (amount >= 1_00_00_000) return `₹${(amount / 1_00_00_000).toFixed(2)} crore`;
  return `₹${amount.toLocaleString('en-IN')}`;
};

const formatPrice = (value: MetricValue) => {
  if (value === null || value === undefined || value === '' || value === 'N/A') return 'Not available';
  const amount = Number(value);
  if (!Number.isFinite(amount)) return String(value);
  return `₹${amount.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
};

const formatRatioPercent = (value: MetricValue) => {
  if (value === null || value === undefined || value === '' || value === 'N/A') return 'Not available';
  if (typeof value === 'string' && value.endsWith('%')) return value;
  const amount = Number(value);
  if (!Number.isFinite(amount)) return String(value);
  const percent = Math.abs(amount) <= 1 ? amount * 100 : amount;
  return `${percent.toFixed(2)}%`;
};

const metricValue = (data: ComparisonMetric | undefined, key: string): MetricValue => {
  if (!data) return undefined;
  if (!key.includes('.')) return data[key] as MetricValue;
  const [parent, child] = key.split('.');
  const nested = data[parent];
  if (nested && typeof nested === 'object') return (nested as FundamentalMetric)[child];
  return undefined;
};

const metricNumber = (data: ComparisonMetric | undefined, key: string) => {
  const value = metricValue(data, key);
  const num = Number(value);
  return Number.isFinite(num) ? num : null;
};

const chartRows = (
  comparison: Record<string, ComparisonMetric>,
  metrics: Array<[string, string]>,
) => {
  return metrics.map(([label, key]) => {
    const row: Record<string, string | number | null> = { metric: label };
    Object.entries(comparison).forEach(([entity, data]) => {
      row[entity] = metricNumber(data, key);
    });
    return row;
  });
};

const buildPriceRows = (comparison: Record<string, ComparisonMetric>) => {
  const byDate = new Map<string, Record<string, string | number | null>>();

  Object.entries(comparison).forEach(([entity, data]) => {
    const history = data.price_history;
    if (!Array.isArray(history)) return;

    history.slice(-180).forEach((point) => {
      if (!point || typeof point !== 'object') return;
      const row = point as Record<string, unknown>;
      const date = String(row.date || '');
      const close = Number(row.close);
      if (!date || !Number.isFinite(close)) return;
      const existing = byDate.get(date) || { date };
      existing[entity] = close;
      byDate.set(date, existing);
    });
  });

  return Array.from(byDate.values()).sort((a, b) => String(a.date).localeCompare(String(b.date)));
};

const hasComparisonPayload = (value: unknown): boolean => {
  if (!value || typeof value !== 'object') return false;
  const payload = value as Record<string, unknown>;
  return Boolean(payload.comparison || payload.profiles);
};

const mapQuantResponse = (data: unknown): Record<string, StockComparisonMetric> => {
  if (!data || typeof data !== 'object') return {};
  const payload = data as QuantResponsePayload;
  if (!payload.profiles) return (payload.comparison as Record<string, StockComparisonMetric> | undefined) || {};

  const mapped: Record<string, StockComparisonMetric> = {};
  for (const sym of payload.available || []) {
    const profile = payload.profiles[sym] || {};
    const ratios = payload.ratios?.[sym] || {};
    const fin = payload.financials?.[sym] || [];
    const latest_qtr = fin.find((f) => f.period_type === 'quarterly') || {};
    const latest_ann = fin.find((f) => f.period_type === 'annual') || {};
    const sh = payload.shareholding?.[sym] || [];
    const latest_sh = sh[0] || {};
    const price_hist = payload.price_history?.[sym] || [];
    const latest_price = price_hist.length > 0 ? price_hist[price_hist.length - 1].close : null;
    
    mapped[sym] = {
      price: latest_price,
      market_cap: ratios['market_cap'] as MetricValue,
      enterprise_value: ratios['enterprise_value'] as MetricValue,
      beta: ratios['beta'] as MetricValue,
      alpha_vs_nifty: ratios['alpha_vs_nifty'] as MetricValue,
      fundamentals: {
        industry: profile['industry'] as MetricValue,
        pe: ratios['pe'] as MetricValue,
        pb: ratios['pb'] as MetricValue,
        ps: ratios['ps'] as MetricValue,
        ev_ebitda: ratios['ev_ebitda'] as MetricValue,
        roe: ratios['roe'] as MetricValue,
        roce: ratios['roce'] as MetricValue,
        roa: ratios['roa'] as MetricValue,
        debt_to_equity: ratios['debt_to_equity'] as MetricValue,
        dividend_yield: ratios['dividend_yield'] as MetricValue,
        sales_growth_1y: ratios['sales_growth_1y'] as MetricValue,
        sales_growth_3y: ratios['sales_growth_3y'] as MetricValue,
        profit_growth_1y: ratios['profit_growth_1y'] as MetricValue,
        profit_growth_3y: ratios['profit_growth_3y'] as MetricValue,
        eps_growth_1y: ratios['eps_growth_1y'] as MetricValue,
        eps_growth_3y: ratios['eps_growth_3y'] as MetricValue,
        revenue_qtr: latest_qtr.revenue,
        net_profit_qtr: latest_qtr.net_profit,
        revenue_ann: latest_ann.revenue,
        net_profit_ann: latest_ann.net_profit,
        promoter_holding: latest_sh['promoter_holding'] as MetricValue,
        fii_holding: latest_sh['fii_holding'] as MetricValue,
        dii_holding: latest_sh['dii_holding'] as MetricValue,
        public_holding: latest_sh['public_holding'] as MetricValue,
        source: profile['source'] as MetricValue
      },
      price_history: price_hist
    };
  }
  return mapped;
};

const getWhyBetter = (data: unknown): WhyBetterPayload | null => {
  if (!data || typeof data !== 'object') return null;
  const payload = data as Record<string, unknown>;
  const why = payload.why_better;
  if (!why || typeof why !== 'object') return null;
  return why as WhyBetterPayload;
};

const computeAlphaBetaFromNav = (
  navData: NavPoint[] | null,
  benchmarkData: Array<{ date: string; close: number }> | null,
) => {
  if (!navData || navData.length < 20 || !benchmarkData || benchmarkData.length < 20) {
    return { alpha: null as number | null, beta: null as number | null };
  }

  const chronologicalFund = [...navData].reverse();
  const benchMap = new Map<string, number>();
  benchmarkData.forEach((row) => benchMap.set(row.date, row.close));

  const getBenchClose = (dateStr: string): number | null => {
    const direct = benchMap.get(dateStr);
    if (typeof direct === 'number') return direct;

    const [d, m, y] = dateStr.split('-').map(Number);
    const anchor = new Date(Date.UTC(y, m - 1, d));
    for (let offset = -1; offset >= -3; offset--) {
      const adj = new Date(anchor);
      adj.setUTCDate(anchor.getUTCDate() + offset);
      const adjStr = `${String(adj.getUTCDate()).padStart(2, '0')}-${String(adj.getUTCMonth() + 1).padStart(2, '0')}-${adj.getUTCFullYear()}`;
      const value = benchMap.get(adjStr);
      if (typeof value === 'number') return value;
    }
    return null;
  };

  const fundReturns: number[] = [];
  const benchReturns: number[] = [];
  for (let index = 1; index < chronologicalFund.length; index++) {
    const currentBench = getBenchClose(chronologicalFund[index].date);
    const previousBench = getBenchClose(chronologicalFund[index - 1].date);
    if (currentBench === null || previousBench === null) continue;

    const currentNav = Number(chronologicalFund[index].nav);
    const previousNav = Number(chronologicalFund[index - 1].nav);
    if (!Number.isFinite(currentNav) || !Number.isFinite(previousNav) || previousNav <= 0 || previousBench <= 0) continue;

    fundReturns.push((currentNav / previousNav) - 1);
    benchReturns.push((currentBench / previousBench) - 1);
  }

  if (fundReturns.length < 10 || fundReturns.length !== benchReturns.length) {
    return { alpha: null as number | null, beta: null as number | null };
  }

  const beta = calculateBeta(fundReturns, benchReturns);
  const totalFundReturn = fundReturns.reduce((acc, value) => acc * (1 + value), 1);
  const totalBenchReturn = benchReturns.reduce((acc, value) => acc * (1 + value), 1);
  const years = fundReturns.length / 252;
  if (!Number.isFinite(beta) || years <= 0.05) {
    return { alpha: null as number | null, beta: Number.isFinite(beta) ? beta : null };
  }

  const fundCagr = Math.pow(totalFundReturn, 1 / years) - 1;
  const benchCagr = Math.pow(totalBenchReturn, 1 / years) - 1;
  const alpha = calculateAlpha(fundCagr, benchCagr, beta) * 100;

  return {
    alpha: Number.isFinite(alpha) ? alpha : null,
    beta: Number.isFinite(beta) ? beta : null,
  };
};

const toNumber = (value: unknown): number | null => {
  if (value === null || value === undefined || value === '' || value === 'N/A') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const normalizePercent = (value: unknown, scaleUnitToPercent = true): number | null => {
  const parsed = toNumber(value);
  if (parsed === null) return null;
  if (scaleUnitToPercent && Math.abs(parsed) <= 1) return parsed * 100;
  return parsed;
};

const formatPlain = (value: number | null, digits = 2) => {
  if (value === null) return 'N/A';
  return value.toFixed(digits);
};

const formatPercent = (value: number | null, digits = 2) => {
  if (value === null) return 'N/A';
  return `${value >= 0 ? '+' : ''}${value.toFixed(digits)}%`;
};

const formatAum = (value: unknown) => {
  const parsed = toNumber(value);
  if (parsed === null) return 'N/A';
  return `₹${parsed.toLocaleString('en-IN')} Cr`;
};

const formatExpense = (value: unknown) => {
  const parsed = toNumber(value);
  if (parsed === null) return 'N/A';
  return `${parsed.toFixed(2)}%`;
};

const compactSchemeName = (name: string | null | undefined) => {
  if (!name) return 'N/A';
  return name
    .replace(/\s*-\s*Direct Plan\s*-\s*Growth/gi, '')
    .replace(/\s*-\s*Regular Plan\s*-\s*Growth/gi, '')
    .replace(/\s*-\s*Growth/gi, '')
    .replace(/\s*of Funds/gi, ' FoF')
    .trim();
};

const getMfComparisonRecord = (
  map: unknown,
  schemeCode: string | null,
  schemeName: string | null,
): MFComparisonRecord | null => {
  if (!map || typeof map !== 'object') return null;
  const entries = Object.values(map as Record<string, unknown>);
  const nameLower = (schemeName || '').toLowerCase();

  for (const raw of entries) {
    const row = raw as MFComparisonRecord;
    if (row?.scheme_code !== null && row?.scheme_code !== undefined && String(row.scheme_code) === String(schemeCode)) {
      return row;
    }
    const rowName = (row?.name || '').toLowerCase();
    if (rowName && nameLower && (rowName.includes(nameLower) || nameLower.includes(rowName))) {
      return row;
    }
  }
  return null;
};

function WhyBetterPanel({ payload }: { payload: WhyBetterPayload | null }) {
  if (!payload) return null;
  const winner = payload.winner;
  const confidence = payload.confidence;
  const factors = payload.factor_results || [];
  const freshness = payload.source_freshness || {};
  const freshnessRows = Object.entries(freshness);
  const holdingsBlocked = payload.holdings_based_reasoning?.status === 'blocked';
  const isMf = winner?.asset_type === 'mutual_fund';

  return (
    <section className="rounded-2xl border border-[#35588f] bg-[#16243a] p-4 sm:p-5">
      <h3 className="mb-2 text-sm font-semibold tracking-wide text-[#9ec5ff]">Why this is better?</h3>
      <p className="whitespace-pre-line text-sm leading-relaxed text-[#d7e4fb]">
        {payload.summary || 'Deterministic comparison summary unavailable.'}
      </p>
      <div className="mt-3 flex flex-wrap gap-2 text-xs">
        <span className="rounded-md border border-white/20 bg-[#0e182a] px-2 py-1 text-[#d7e4fb]">
          Winner: {winner?.status === 'winner' ? (winner.entity_name || winner.entity_id || 'N/A') : winner?.status || 'N/A'}
        </span>
        <span className="rounded-md border border-white/20 bg-[#0e182a] px-2 py-1 text-[#d7e4fb]">
          Confidence: {confidence?.label || 'N/A'} ({typeof confidence?.score === 'number' ? confidence.score.toFixed(2) : 'N/A'})
        </span>
        <span className="rounded-md border border-white/20 bg-[#0e182a] px-2 py-1 text-[#d7e4fb]">
          Coverage: {factors.length > 0 && factors.every((f) => (f.coverage ?? 0) >= 1) ? 'Complete' : 'Incomplete'}
        </span>
      </div>
      {isMf && (
        <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-[#bcd0f0]">
          <li>Flexi-cap and multi-asset funds should not be judged only by returns.</li>
          <li>Risk profile differs by mandate, volatility, and downside behavior.</li>
          <li>Asset allocation changes the comparison baseline and expected outcomes.</li>
          <li>Sharpe, volatility, drawdown, and rolling-return consistency matter.</li>
          <li>Coverage is currently limited but still useful for validating comparison logic.</li>
        </ul>
      )}
      {holdingsBlocked && (
        <div className="mt-3 rounded-md border border-amber-300/35 bg-amber-300/10 px-3 py-2 text-xs text-amber-100">
          Holdings-based reasoning unavailable. Holdings sync pending.
        </div>
      )}
      {factors.length > 0 && (
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {factors.map((factor, idx) => (
            <div key={`${factor.factor || 'factor'}-${idx}`} className="rounded-md border border-white/15 bg-[#0e182a] p-2 text-xs">
              <div className="font-semibold text-white">{factor.factor || 'Factor'}</div>
              <div className="text-[#c8d8f6]">Winner: {factor.winner || 'No clear edge'}</div>
              <div className="text-[#8ea7cd]">Coverage: {typeof factor.coverage === 'number' ? `${Math.round(factor.coverage * 100)}%` : 'N/A'}</div>
            </div>
          ))}
        </div>
      )}
      {freshnessRows.length > 0 && (
        <div className="mt-3 grid gap-2 md:grid-cols-2">
          {freshnessRows.map(([entity, meta]) => (
            <div key={entity} className="rounded-md border border-white/15 bg-[#0e182a] p-2 text-xs">
              <div className="font-semibold text-white">{entity}</div>
              <div className="text-[#c8d8f6]">Source: {meta?.source || 'N/A'}</div>
              <div className="text-[#c8d8f6]">Last Updated: {meta?.snapshot_last_updated || meta?.price_date || meta?.nav_date || 'N/A'}</div>
              <div className={meta?.stale ? 'text-amber-200' : 'text-emerald-200'}>
                {meta?.stale ? 'Stale' : 'Fresh'}
              </div>
            </div>
          ))}
        </div>
      )}
      {payload.verdict_context && <p className="mt-3 text-xs text-[#8ea7cd]">{payload.verdict_context}</p>}
    </section>
  );
}

export default function ComparisonView({ ids, type, auxiliaryData }: Props) {
  const [period, setPeriod] = useState<Period>('1Y');

  // Heuristic: if IDs are numeric, they are mutual fund scheme codes
  const idA = ids?.[0] || null;
  const idB = ids?.[1] || null;
  const isMF = type === 'MUTUAL_FUND' || Boolean(idA && /^[0-9]+$/.test(idA));

  const fundA = useFundData(isMF ? idA : null);
  const fundB = useFundData(isMF ? idB : null);
  const benchmark = useBenchmarkData();
  const [fetchedComparison, setFetchedComparison] = useState<Record<string, StockComparisonMetric>>({});
  const [fetchedWhyBetter, setFetchedWhyBetter] = useState<WhyBetterPayload | null>(null);
  const [stockError, setStockError] = useState<string | null>(null);

  useEffect(() => {
    const hasAuxComparison = hasComparisonPayload(auxiliaryData?.quant_data);
    if (isMF || hasAuxComparison || ids.length < 2) return;

    let cancelled = false;
    const symbols = ids.map(id => encodeURIComponent(id)).join(',');

    fetch(`/api/quant/stocks/compare?symbols=${symbols}`)
      .then(res => {
        if (!res.ok) throw new Error('Failed to load stock comparison');
        return res.json();
      })
      .then(data => {
        if (!cancelled) {
          setFetchedComparison(mapQuantResponse(data));
          setFetchedWhyBetter(getWhyBetter(data));
        }
      })
      .catch(error => {
        if (!cancelled) setStockError((error as Error).message);
      });

    return () => {
      cancelled = true;
    };
  }, [auxiliaryData, ids, isMF]);

  if (!ids || ids.length < 2) {
    return <div className="p-6 text-gray-400">Insufficient data for comparison.</div>;
  }

  if (!isMF) {
    const comparison = mapQuantResponse(auxiliaryData?.quant_data) || fetchedComparison;
    const whyBetter = getWhyBetter(auxiliaryData?.quant_data) || fetchedWhyBetter;
    const entities = Object.keys(comparison);
    const colors = ['#5eead4', '#60a5fa', '#f97316', '#a78bfa'];
    const hasFundamentals = entities.some(entity => {
      const fundamentals = comparison[entity]?.fundamentals as FundamentalMetric | undefined;
      return fundamentals && Object.values(fundamentals).some(value => value !== null && value !== undefined && value !== '');
    });
    const valuationRows = chartRows(comparison, [['PE', 'fundamentals.pe'], ['PB', 'fundamentals.pb'], ['EV/EBITDA', 'fundamentals.ev_ebitda'], ['Div Yield', 'fundamentals.dividend_yield']]);
    const quarterlyRows = chartRows(comparison, [['Revenue Qtr', 'fundamentals.revenue_qtr'], ['NP Qtr', 'fundamentals.net_profit_qtr']]);
    const qualityRows = chartRows(comparison, [['ROCE', 'fundamentals.roce'], ['ROE', 'fundamentals.roe'], ['ROA', 'fundamentals.roa']]);
    const growthRows = chartRows(comparison, [['Sales 3Y', 'fundamentals.sales_growth_3y'], ['Profit 3Y', 'fundamentals.profit_growth_3y'], ['EPS 3Y', 'fundamentals.eps_growth_3y']]);
    const holdingRows = chartRows(comparison, [['Promoter', 'fundamentals.promoter_holding'], ['FII', 'fundamentals.fii_holding'], ['DII', 'fundamentals.dii_holding']]);
    const priceRows = buildPriceRows(comparison);
    const staleEntities = entities.filter(entity => Boolean(comparison[entity]?.source_summary?.stale));

    const renderBarChart = (title: string, rows: Record<string, string | number | null>[], suffix = '%') => (
      <section className="rounded-2xl border border-[#2d3b55] bg-[#111b2d] p-4 shadow-md">
        <h3 className="mb-3 text-sm font-semibold text-[#d7e4fb]">{title}</h3>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={rows}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
              <XAxis dataKey="metric" stroke="#9ca3af" fontSize={12} />
              <YAxis stroke="#9ca3af" fontSize={12} tickFormatter={(value) => `${value}${suffix}`} />
              <Tooltip
                cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                contentStyle={{ background: '#111827', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 8, color: '#fff' }}
                formatter={(value) => {
                  const formatted = formatValue(value as MetricValue);
                  return [formatted === 'Not available' ? formatted : `${formatted}${suffix}`, ''];
                }}
              />
              {entities.map((entity, index) => (
                <Bar key={entity} dataKey={entity} fill={colors[index % colors.length]} radius={[4, 4, 0, 0]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>
    );

    const scaleGroup = [
      { label: 'Price', key: 'price', formatter: formatPrice },
      { label: 'Market Cap', key: 'market_cap', formatter: formatMarketCap },
      { label: 'Enterprise Value', key: 'enterprise_value', formatter: formatMarketCap },
    ];

    const valuationGroup = [
      { label: 'P/E Ratio', key: 'fundamentals.pe', formatter: formatValue },
      { label: 'P/B Ratio', key: 'fundamentals.pb', formatter: formatValue },
      { label: 'P/S Ratio', key: 'fundamentals.ps', formatter: formatValue },
      { label: 'EV/EBITDA', key: 'fundamentals.ev_ebitda', formatter: formatValue },
      { label: 'Dividend Yield', key: 'fundamentals.dividend_yield', formatter: formatRatioPercent },
    ];

    const qualityGroup = [
      { label: 'Beta', key: 'beta', formatter: formatValue },
      { label: 'Alpha vs Nifty', key: 'alpha_vs_nifty', formatter: (val: MetricValue) => {
        const num = toNumber(val);
        return num !== null ? formatPercent(num) : 'Not available';
      }},
      { label: 'ROE', key: 'fundamentals.roe', formatter: formatRatioPercent },
      { label: 'ROCE', key: 'fundamentals.roce', formatter: formatRatioPercent },
      { label: 'ROA', key: 'fundamentals.roa', formatter: formatRatioPercent },
      { label: 'Debt/Equity', key: 'fundamentals.debt_to_equity', formatter: formatValue },
    ];

    const growthGroup = [
      { label: 'Sales Growth (1Y)', key: 'fundamentals.sales_growth_1y', formatter: formatRatioPercent },
      { label: 'Sales Growth (3Y)', key: 'fundamentals.sales_growth_3y', formatter: formatRatioPercent },
      { label: 'Profit Growth (1Y)', key: 'fundamentals.profit_growth_1y', formatter: formatRatioPercent },
      { label: 'Profit Growth (3Y)', key: 'fundamentals.profit_growth_3y', formatter: formatRatioPercent },
      { label: 'EPS Growth (1Y)', key: 'fundamentals.eps_growth_1y', formatter: formatRatioPercent },
      { label: 'EPS Growth (3Y)', key: 'fundamentals.eps_growth_3y', formatter: formatRatioPercent },
    ];

    const financialsGroup = [
      { label: 'Latest Qtr Revenue', key: 'fundamentals.revenue_qtr', formatter: formatValue },
      { label: 'Latest Qtr Net Profit', key: 'fundamentals.net_profit_qtr', formatter: formatValue },
      { label: 'Latest Annual Revenue', key: 'fundamentals.revenue_ann', formatter: formatValue },
      { label: 'Latest Annual Net Profit', key: 'fundamentals.net_profit_ann', formatter: formatValue },
    ];

    const shareholdingGroup = [
      { label: 'Promoter Holding', key: 'fundamentals.promoter_holding', formatter: formatRatioPercent },
      { label: 'FII Holding', key: 'fundamentals.fii_holding', formatter: formatRatioPercent },
      { label: 'DII Holding', key: 'fundamentals.dii_holding', formatter: formatRatioPercent },
      { label: 'Public Holding', key: 'fundamentals.public_holding', formatter: formatRatioPercent },
      { label: 'Data Source', key: 'fundamentals.source', formatter: formatValue },
    ];

    const renderStockGroupedTable = (title: string, rows: Array<{ label: string; key: string; formatter: (val: MetricValue) => string }>) => {
      const getStockWinner = (label: string, valA: number | null, valB: number | null): 'a' | 'b' | null => {
        if (valA === null || valB === null) return null;
        if (valA === valB) return null;
        const labelLower = label.toLowerCase();
        
        if (labelLower.includes('p/e') || labelLower.includes('p/b') || labelLower.includes('p/s') || labelLower.includes('ev/ebitda') || labelLower.includes('debt/equity')) {
          return valA < valB ? 'a' : 'b';
        }
        return valA > valB ? 'a' : 'b';
      };

      return (
        <div className="rounded-2xl border border-white/10 bg-[#0f172a]/60 overflow-hidden shadow-lg backdrop-blur-md">
          <div className="px-5 py-3.5 border-b border-white/10 bg-white/[0.02]">
            <h4 className="text-sm font-semibold text-white tracking-wide">{title}</h4>
          </div>
          <div className="divide-y divide-white/5">
            {rows.map((row) => {
              const valA = metricValue(comparison[entities[0]], row.key);
              const valB = metricValue(comparison[entities[1]], row.key);
              const numA = toNumber(valA);
              const numB = toNumber(valB);
              const winner = getStockWinner(row.label, numA, numB);

              return (
                <div key={row.label} className="grid grid-cols-[1.5fr_1fr_1fr] text-sm items-center hover:bg-white/[0.01] transition-colors">
                  <div className="px-5 py-3 font-medium text-slate-300">{row.label}</div>
                  <div className={`px-5 py-3 text-left ${winner === 'a' ? 'text-emerald-300 font-semibold bg-emerald-500/5' : 'text-slate-200'}`}>
                    <span className="flex items-center gap-1.5 font-mono">
                      {row.formatter(valA)}
                      {winner === 'a' && <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400" />}
                    </span>
                  </div>
                  <div className={`px-5 py-3 text-left ${winner === 'b' ? 'text-emerald-300 font-semibold bg-emerald-500/5' : 'text-slate-200'}`}>
                    <span className="flex items-center gap-1.5 font-mono">
                      {row.formatter(valB)}
                      {winner === 'b' && <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400" />}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      );
    };

    return (
      <div className="comparison-detail finance-compare-wrap p-3 sm:p-6 h-full flex flex-col overflow-hidden max-w-7xl mx-auto w-full">
        <div className="mb-5 rounded-2xl border border-[#2d3b55] bg-[#111b2d] px-5 py-4 shadow-md">
          <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">Stock Comparison Console</h2>
          <p className="text-sm text-[#a7bad9] mt-1">
            Source-neutral valuation, growth, quality, and ownership comparison
          </p>
        </div>
        <div className="custom-scroll flex-1 space-y-5 overflow-y-auto pr-2 pb-10">
          {staleEntities.length > 0 && (
            <div className="rounded-xl border border-amber-400/20 bg-amber-400/10 p-4 text-sm text-amber-100">
              Data may be stale for: {staleEntities.join(', ')}.
            </div>
          )}
          <WhyBetterPanel payload={whyBetter} />
          {priceRows.length > 0 && (
            <section className="rounded-2xl border border-[#2d3b55] bg-[#111b2d] p-4 shadow-md">
              <h3 className="mb-3 text-sm font-semibold text-[#d7e4fb]">Price History</h3>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={priceRows}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                    <XAxis dataKey="date" stroke="#9ca3af" fontSize={12} />
                    <YAxis stroke="#9ca3af" fontSize={12} />
                    <Tooltip contentStyle={{ background: '#111827', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 8, color: '#fff' }} />
                    {entities.map((entity, index) => (
                      <Line key={entity} type="monotone" dataKey={entity} stroke={colors[index % colors.length]} strokeWidth={2} dot={false} connectNulls />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </section>
          )}
          {hasFundamentals && (
            <div className="grid gap-4 xl:grid-cols-2">
              {renderBarChart('Valuation Metrics', valuationRows, '')}
              {renderBarChart('Latest Quarterly Revenue and Profit', quarterlyRows, '')}
              {renderBarChart('Quality Metrics', qualityRows)}
              {renderBarChart('Growth Metrics', growthRows)}
              {renderBarChart('Shareholding Mix', holdingRows)}
              {renderBarChart('Debt to Equity', chartRows(comparison, [['Debt/Equity', 'fundamentals.debt_to_equity']]), '')}
            </div>
          )}
          {!hasFundamentals && (
            <div className="rounded-xl border border-amber-400/20 bg-amber-400/10 p-4 text-sm text-amber-100">
              {stockError || 'Fundamentals are unavailable because no fundamentals provider has supplied these fields yet.'}
            </div>
          )}
          
          <div className="space-y-4">
            <h3 className="text-base font-bold text-white tracking-tight mt-6 mb-2">Detailed Metric Comparison</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {renderStockGroupedTable('Scale & Pricing', scaleGroup)}
              {renderStockGroupedTable('Valuation Ratios', valuationGroup)}
              {renderStockGroupedTable('Quality & Risk', qualityGroup)}
              {renderStockGroupedTable('Growth Profile', growthGroup)}
              {renderStockGroupedTable('Financial Position', financialsGroup)}
              {renderStockGroupedTable('Shareholding & Metadata', shareholdingGroup)}
            </div>
          </div>
        </div>
      </div>
    );
  }

  const loading = fundA.loading || fundB.loading;
  const error = fundA.error || fundB.error;
  const mfWhyBetter = getWhyBetter(auxiliaryData?.quant_data);
  const periods: Period[] = ['1D', '6M', '1Y', '3Y', '5Y'];
  const comparisonMap =
    auxiliaryData?.quant_data && typeof auxiliaryData.quant_data === 'object'
      ? (auxiliaryData.quant_data as { comparison?: Record<string, unknown> }).comparison
      : auxiliaryData?.comparison;

  const getWinner = (
    label: string, 
    valA: number | null, 
    valB: number | null
  ): 'a' | 'b' | null => {
    if (valA === null || valB === null) return null;
    if (valA === valB) return null;

    const labelLower = label.toLowerCase();
    if (labelLower.includes('expense')) {
      return valA < valB ? 'a' : 'b';
    }
    if (labelLower.includes('drawdown')) {
      return valA > valB ? 'a' : 'b';
    }
    if (labelLower.includes('volatility')) {
      return valA < valB ? 'a' : 'b';
    }
    return valA > valB ? 'a' : 'b';
  };

  const renderGroupedTable = (title: string, rows: Array<{ label: string; a: string | number | null; b: string | number | null; winner: 'a' | 'b' | null }>) => (
    <div className="rounded-2xl border border-white/10 bg-[#0f172a]/60 overflow-hidden shadow-lg backdrop-blur-md">
      <div className="px-5 py-3.5 border-b border-white/10 bg-white/[0.02]">
        <h4 className="text-sm font-semibold text-white tracking-wide">{title}</h4>
      </div>
      <div className="divide-y divide-white/5">
        {rows.map((row) => (
          <div key={row.label} className="grid grid-cols-[1.5fr_1fr_1fr] text-sm items-center hover:bg-white/[0.01] transition-colors">
            <div className="px-5 py-3 font-medium text-slate-300">{row.label}</div>
            <div className={`px-5 py-3 text-left ${row.winner === 'a' ? 'text-emerald-300 font-semibold bg-emerald-500/5' : 'text-slate-200'}`}>
              <span className="flex items-center gap-1.5 font-mono">
                {row.a === 'N/A' || row.a === null ? <span className="text-slate-500">N/A</span> : row.a}
                {row.winner === 'a' && <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400" />}
              </span>
            </div>
            <div className={`px-5 py-3 text-left ${row.winner === 'b' ? 'text-emerald-300 font-semibold bg-emerald-500/5' : 'text-slate-200'}`}>
              <span className="flex items-center gap-1.5 font-mono">
                {row.b === 'N/A' || row.b === null ? <span className="text-slate-500">N/A</span> : row.b}
                {row.winner === 'b' && <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400" />}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  const Skeleton = () => (
    <div className="flex-1 space-y-6 overflow-hidden animate-pulse max-w-7xl mx-auto w-full p-3 sm:p-6">
      <div className="h-24 rounded-3xl border border-[#2d3b55] bg-[#101b2d] p-5 space-y-3">
        <div className="h-6 w-1/3 rounded bg-white/[0.05]" />
        <div className="h-4 w-1/2 rounded bg-white/[0.05]" />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {[1, 2].map((i) => (
          <div key={i} className="rounded-3xl border border-[#2d3b55] bg-[#101b2d] p-5 space-y-3">
            <div className="h-6 w-1/2 rounded bg-white/[0.05]" />
            <div className="h-4 w-3/4 rounded bg-white/[0.05]" />
            <div className="h-5 w-24 rounded bg-white/[0.05]" />
          </div>
        ))}
      </div>

      <div className="rounded-3xl border border-[#2d3b55] bg-[#101b2d] p-5 space-y-2">
        <div className="h-5 w-32 rounded bg-white/[0.05]" />
        <div className="h-4 w-full rounded bg-white/[0.05]" />
        <div className="h-4 w-5/6 rounded bg-white/[0.05]" />
      </div>

      <div className="rounded-3xl border border-[#2d3b55] bg-[#0e182b] p-5 h-72 flex items-end justify-between gap-4">
        {[...Array(12)].map((_, i) => (
          <div key={i} className="bg-white/[0.03] rounded-t-lg w-full" style={{ height: `${20 + Math.random() * 60}%` }} />
        ))}
      </div>

      <div className="space-y-4">
        <div className="h-6 w-44 rounded bg-white/[0.05]" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2].map((i) => (
            <div key={i} className="rounded-2xl border border-white/10 bg-[#0f172a]/60 overflow-hidden">
              <div className="p-4 border-b border-white/10 bg-white/[0.02]">
                <div className="h-4 w-32 rounded bg-white/[0.05]" />
              </div>
              <div className="p-4 space-y-3">
                {[1, 2, 3].map((j) => (
                  <div key={j} className="flex justify-between">
                    <div className="h-3 w-20 rounded bg-white/[0.05]" />
                    <div className="h-3 w-12 rounded bg-white/[0.05]" />
                    <div className="h-3 w-12 rounded bg-white/[0.05]" />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  return (
    <div className="comparison-detail finance-compare-wrap p-3 sm:p-6 h-full flex flex-col overflow-hidden max-w-7xl mx-auto w-full">
      <div className="mb-5 flex flex-col gap-4 rounded-3xl border border-[#2f3b57] bg-[#121a2d] px-5 py-5 sm:mb-6 sm:flex-row sm:items-center sm:justify-between shrink-0">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="rounded bg-[#1a2740] px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider text-[#8ea7cd] border border-[#2f3b57]">Research-only</span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight sm:text-2xl">Mutual Fund Comparison</h2>
          {fundA.meta && fundB.meta && (
            <p className="text-sm text-[#a7bad9] mt-1">{compactSchemeName(fundA.meta.scheme_name)} vs {compactSchemeName(fundB.meta.scheme_name)}</p>
          )}
        </div>

        <div className="flex max-w-full overflow-x-auto rounded-xl bg-[#0d1628] p-1.5 border border-white/10 shadow-inner gap-1.5 shrink-0">
          {periods.map(p => {
            const isSupported = (() => {
               if (p === '1D' || p === '6M') return true;
               const aCov = fundA.coverage as any;
               const bCov = fundB.coverage as any;
               if (!aCov || !bCov) return true;
               
               const aSup = aCov.supports_1y !== undefined ? aCov : (aCov.supports || {});
               const bSup = bCov.supports_1y !== undefined ? bCov : (bCov.supports || {});
               
               if (p === '1Y') return (aSup.supports_1y ?? aSup['1Y']) && (bSup.supports_1y ?? bSup['1Y']);
               if (p === '3Y') return (aSup.supports_3y ?? aSup['3Y']) && (bSup.supports_3y ?? bSup['3Y']);
               if (p === '5Y') return (aSup.supports_5y ?? aSup['5Y']) && (bSup.supports_5y ?? bSup['5Y']);
               return true;
            })();

            return (
              <button
                key={p}
                onClick={() => isSupported && setPeriod(p)}
                disabled={!isSupported}
                title={!isSupported ? "Not enough NAV history for this period" : ""}
                className={`shrink-0 rounded-md px-3 py-2 text-xs font-semibold transition-colors duration-200 sm:px-4 ${
                  !isSupported ? 'opacity-40 cursor-not-allowed bg-transparent text-[#6e85a6]' :
                  period === p ? 'bg-[#4f8ff7] text-white shadow-lg' : 'text-[#9eb5d8] hover:text-white hover:bg-white/5'}`}
              >
                {p}
              </button>
            )
          })}
        </div>
      </div>

      {loading && <Skeleton />}

      {error && (
        <div className="flex-1 flex flex-col items-center justify-center p-8 bg-red-500/10 rounded-3xl border border-red-500/20 mx-4">
          <svg className="w-12 h-12 text-red-500 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <p className="text-red-400 text-center font-medium">{error}</p>
          <button 
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-colors"
          >
            Retry Connection
          </button>
        </div>
      )}
      
      {!loading && !error && fundA.meta && fundB.meta && (
        <div className="flex-1 overflow-y-auto pr-2 custom-scroll pb-10">
          {(() => {
            const aRecord = getMfComparisonRecord(comparisonMap, ids[0], fundA.meta.scheme_name);
            const bRecord = getMfComparisonRecord(comparisonMap, ids[1], fundB.meta.scheme_name);
            const aLabel = compactSchemeName(fundA.meta.scheme_name);
            const bLabel = compactSchemeName(fundB.meta.scheme_name);

            const aReturn1Y = toNumber(fundA.returns?.['1Y']);
            const bReturn1Y = toNumber(fundB.returns?.['1Y']);
            const aReturn3Y = toNumber(aRecord?.return_3y ?? fundA.returns?.['3Y']);
            const bReturn3Y = toNumber(bRecord?.return_3y ?? fundB.returns?.['3Y']);
            const aReturn5Y = toNumber(fundA.returns?.['5Y']);
            const bReturn5Y = toNumber(fundB.returns?.['5Y']);
            
            const aVol = normalizePercent(aRecord?.volatility_1y ?? fundA.riskMetrics?.stdDev);
            const bVol = normalizePercent(bRecord?.volatility_1y ?? fundB.riskMetrics?.stdDev);
            const aSharpe = toNumber(aRecord?.sharpe_ratio ?? fundA.riskMetrics?.sharpeRatio);
            const bSharpe = toNumber(bRecord?.sharpe_ratio ?? fundB.riskMetrics?.sharpeRatio);
            const aAlphaRaw = toNumber(aRecord?.alpha_vs_nifty ?? aRecord?.alpha ?? fundA.riskMetrics?.alpha_vs_nifty ?? fundA.riskMetrics?.alpha);
            const bAlphaRaw = toNumber(bRecord?.alpha_vs_nifty ?? bRecord?.alpha ?? fundB.riskMetrics?.alpha_vs_nifty ?? fundB.riskMetrics?.alpha);
            const aBetaRaw = toNumber(aRecord?.beta ?? fundA.riskMetrics?.beta);
            const bBetaRaw = toNumber(bRecord?.beta ?? fundB.riskMetrics?.beta);
            const aFallback = (aAlphaRaw === null || aBetaRaw === null)
              ? computeAlphaBetaFromNav(fundA.navData, benchmark.data)
              : { alpha: null as number | null, beta: null as number | null };
            const bFallback = (bAlphaRaw === null || bBetaRaw === null)
              ? computeAlphaBetaFromNav(fundB.navData, benchmark.data)
              : { alpha: null as number | null, beta: null as number | null };
            const aAlpha = aAlphaRaw ?? aFallback.alpha;
            const bAlpha = bAlphaRaw ?? bFallback.alpha;
            const aBeta = aBetaRaw ?? aFallback.beta;
            const bBeta = bBetaRaw ?? bFallback.beta;
            const aDrawdown = normalizePercent(aRecord?.max_drawdown_1y ?? fundA.riskMetrics?.maxDrawdown);
            const bDrawdown = normalizePercent(bRecord?.max_drawdown_1y ?? fundB.riskMetrics?.maxDrawdown);

            const aCov = fundA.coverage as Record<string, unknown> | undefined;
            const bCov = fundB.coverage as Record<string, unknown> | undefined;

            const formatStringOrNA = (val: unknown) => {
              if (val === null || val === undefined || val === '') return 'N/A';
              return String(val);
            };

            const aHistoryPts = aCov?.history_points;
            const bHistoryPts = bCov?.history_points;
            const aLastNav = aCov?.last_nav_date;
            const bLastNav = bCov?.last_nav_date;

            const pGroup = [
              { label: '1Y Return', a: formatPercent(aReturn1Y), b: formatPercent(bReturn1Y), winner: getWinner('1Y Return', aReturn1Y, bReturn1Y) },
              { label: '3Y Return', a: formatPercent(aReturn3Y), b: formatPercent(bReturn3Y), winner: getWinner('3Y Return', aReturn3Y, bReturn3Y) },
              { label: '5Y Return', a: formatPercent(aReturn5Y), b: formatPercent(bReturn5Y), winner: getWinner('5Y Return', aReturn5Y, bReturn5Y) },
              { label: 'Alpha vs Nifty', a: formatPercent(aAlpha), b: formatPercent(bAlpha), winner: getWinner('Alpha', aAlpha, bAlpha) },
            ];

            const rGroup = [
              { label: 'Volatility (1Y)', a: formatPercent(aVol), b: formatPercent(bVol), winner: getWinner('Volatility', aVol, bVol) },
              { label: 'Sharpe Ratio', a: formatPlain(aSharpe), b: formatPlain(bSharpe), winner: getWinner('Sharpe', aSharpe, bSharpe) },
              { label: 'Beta', a: formatPlain(aBeta), b: formatPlain(bBeta), winner: getWinner('Beta', aBeta, bBeta) },
              { label: 'Max Drawdown', a: formatPercent(aDrawdown), b: formatPercent(bDrawdown), winner: getWinner('Drawdown', aDrawdown, bDrawdown) },
            ];

            const dGroup = [
              { label: 'Expense Ratio', a: formatExpense(aRecord?.expense_ratio ?? fundA.details?.expense_ratio), b: formatExpense(bRecord?.expense_ratio ?? fundB.details?.expense_ratio), winner: getWinner('Expense Ratio', toNumber(aRecord?.expense_ratio ?? fundA.details?.expense_ratio), toNumber(bRecord?.expense_ratio ?? fundB.details?.expense_ratio)) },
              { label: 'AUM', a: formatAum(aRecord?.aum ?? fundA.details?.aum), b: formatAum(bRecord?.aum ?? fundB.details?.aum), winner: getWinner('AUM', toNumber(aRecord?.aum ?? fundA.details?.aum), toNumber(bRecord?.aum ?? fundB.details?.aum)) },
              { label: 'NAV points synced', a: aHistoryPts ? String(aHistoryPts) : 'N/A', b: bHistoryPts ? String(bHistoryPts) : 'N/A', winner: getWinner('NAV points', toNumber(aHistoryPts), toNumber(bHistoryPts)) },
              { label: 'Latest NAV Date', a: aLastNav ? String(aLastNav) : 'N/A', b: bLastNav ? String(bLastNav) : 'N/A', winner: null },
            ];

            const aFreshness = fundA.freshness as Record<string, unknown> | undefined;
            const bFreshness = fundB.freshness as Record<string, unknown> | undefined;

            return (
              <div className="grid gap-6">
                
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="rounded-3xl border border-[#2d3b55] bg-[#101b2d] p-5">
                    <h3 className="text-lg font-bold text-white">{aLabel}</h3>
                    <p className="text-xs text-[#8ea7cd] mt-1 line-clamp-1" title={fundA.meta.scheme_name}>{fundA.meta.scheme_name}</p>
                    <div className="mt-4 flex flex-wrap items-center gap-2">
                       {aFreshness?.status === 'fresh' || aFreshness?.stale === false ? (
                          <span className="rounded bg-emerald-500/10 px-2 py-1 text-[10px] font-medium text-emerald-300 border border-emerald-500/20">Fresh NAV</span>
                       ) : (
                          <span className="rounded bg-amber-500/10 px-2 py-1 text-[10px] font-medium text-amber-300 border border-amber-500/20">Stale NAV</span>
                       )}
                       {(aCov as any)?.supports?.['5Y'] || (aCov as any)?.supports_5y ? (
                          <span className="rounded bg-sky-500/10 px-2 py-1 text-[10px] font-medium text-sky-300 border border-sky-500/20">5Y+ Data</span>
                       ) : (aCov as any)?.supports?.['3Y'] || (aCov as any)?.supports_3y ? (
                          <span className="rounded bg-sky-500/10 px-2 py-1 text-[10px] font-medium text-sky-300 border border-sky-500/20">3Y Data</span>
                       ) : (
                          <span className="rounded bg-slate-500/10 px-2 py-1 text-[10px] font-medium text-slate-300 border border-slate-500/20">Limited Data</span>
                       )}
                    </div>
                  </div>
                  <div className="rounded-3xl border border-[#2d3b55] bg-[#101b2d] p-5">
                    <h3 className="text-lg font-bold text-white">{bLabel}</h3>
                    <p className="text-xs text-[#8ea7cd] mt-1 line-clamp-1" title={fundB.meta.scheme_name}>{fundB.meta.scheme_name}</p>
                    <div className="mt-4 flex flex-wrap items-center gap-2">
                       {bFreshness?.status === 'fresh' || bFreshness?.stale === false ? (
                          <span className="rounded bg-emerald-500/10 px-2 py-1 text-[10px] font-medium text-emerald-300 border border-emerald-500/20">Fresh NAV</span>
                       ) : (
                          <span className="rounded bg-amber-500/10 px-2 py-1 text-[10px] font-medium text-amber-300 border border-amber-500/20">Stale NAV</span>
                       )}
                       {(bCov as any)?.supports?.['5Y'] || (bCov as any)?.supports_5y ? (
                          <span className="rounded bg-sky-500/10 px-2 py-1 text-[10px] font-medium text-sky-300 border border-sky-500/20">5Y+ Data</span>
                       ) : (bCov as any)?.supports?.['3Y'] || (bCov as any)?.supports_3y ? (
                          <span className="rounded bg-sky-500/10 px-2 py-1 text-[10px] font-medium text-sky-300 border border-sky-500/20">3Y Data</span>
                       ) : (
                          <span className="rounded bg-slate-500/10 px-2 py-1 text-[10px] font-medium text-slate-300 border border-slate-500/20">Limited Data</span>
                       )}
                    </div>
                  </div>
                </div>

                <div className="rounded-3xl border border-[#2d3b55] bg-[#101b2d] p-5">
                  <h3 className="mb-2 text-sm font-semibold text-[#d7e4fb]">Research verdict</h3>
                  <p className="text-sm leading-relaxed text-[#c8d8f6]">
                    {(!aCov?.supports_1y || !bCov?.supports_1y) ? "No strong overall winner due to limited NAV history." : 
                     (mfWhyBetter?.confidence?.score ?? 0) < 0.6 ? "No strong overall winner. Both funds serve different mandates." :
                     "Directional edge based on available data, but qualitative factors (like asset allocation flexibility) play a major role in overall suitability."}
                  </p>
                </div>

                <div className="rounded-3xl border border-[#2d3b55] bg-[#0e182b] p-5">
                  <FundComparisonChart
                    schemeCodeA={ids[0]}
                    schemeCodeB={ids[1]}
                    nameA={fundA.meta.scheme_name}
                    nameB={fundB.meta.scheme_name}
                    period={period}
                  />
                </div>

                <div className="space-y-4 mt-6">
                  <h3 className="text-base font-bold text-white tracking-tight">Detailed Metric Comparison</h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {renderGroupedTable('Returns & Performance', pGroup)}
                    {renderGroupedTable('Risk & Volatility Indicators', rGroup)}
                    {renderGroupedTable('Costs, Scale & Data Quality', dGroup)}
                  </div>
                </div>

                <div className="rounded-3xl border border-[#2d3b55] bg-[#101b2d] p-5">
                  <h3 className="mb-4 text-base font-semibold text-white">Research notes</h3>
                  <div className="grid gap-4 sm:grid-cols-3">
                    <div className="rounded-2xl border border-white/5 bg-[#15233d] p-5">
                      <h4 className="text-sm font-semibold text-[#8ea7cd] mb-3">Different fund mandates</h4>
                      <p className="text-xs text-[#d7e4fb] leading-relaxed">
                        Parag Flexi Cap is primarily an equity-oriented fund, so it should be judged on long-term equity returns, downside control, portfolio quality, and consistency versus flexi-cap peers.
                      </p>
                    </div>
                    <div className="rounded-2xl border border-white/5 bg-[#15233d] p-5">
                      <h4 className="text-sm font-semibold text-[#8ea7cd] mb-3">Multi-asset context</h4>
                      <p className="text-xs text-[#d7e4fb] leading-relaxed">
                        ICICI Multi Asset should be judged differently because it uses multiple asset classes. Its value comes from diversification, allocation decisions, and risk control rather than only maximum equity-like returns.
                      </p>
                    </div>
                    <div className="rounded-2xl border border-white/5 bg-[#15233d] p-5">
                      <h4 className="text-sm font-semibold text-[#8ea7cd] mb-3">Return-only limitation</h4>
                      <p className="text-xs text-[#d7e4fb] leading-relaxed">
                        A direct return-only comparison may be misleading. A better comparison should include rolling returns, volatility, drawdown, Sharpe ratio, expense ratio, AUM, and asset-allocation history.
                      </p>
                    </div>
                  </div>
                </div>

                <div className="rounded-3xl border border-[#2f3b57] bg-[#0d1628] p-5">
                  <p className="text-xs text-[#8ea7cd] leading-relaxed">
                    Deterministic comparison based on available local NAV, risk, cost, and freshness factors for selected funds. Not a universal investment verdict.
                  </p>
                  <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-[10px] font-medium text-slate-400">
                    <span className="flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span> Source: AMFI / Internal API
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span> Coverage: {aHistoryPts && bHistoryPts ? 'Full' : 'Partial'}
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span> Latest NAV: {formatStringOrNA(aLastNav ?? bLastNav)}
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span> NAV rows fetched: {Math.max(Number(aHistoryPts || 0), Number(bHistoryPts || 0))}
                    </span>
                  </div>
                </div>

              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
}
