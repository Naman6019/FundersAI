'use client';

import { useEffect, useState } from 'react';
import { useFundData } from '../../hooks/useFundData';
import { useBenchmarkData } from '../../hooks/useBenchmarkData';
import FundComparisonChart, { Period } from '../funds/FundComparisonChart';
import FundSearchSelect from '../ui/FundSearchSelect';
import { useCanvasStore } from '@/store/useCanvasStore';
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { CanvasPayload, MetricValue as SharedMetricValue } from '@/types/funds';
import type { NavPoint } from '@/types/funds';
import { calculateAlpha, calculateBeta } from '@/lib/quantUtils';
import { Sparkles } from 'lucide-react';
import { MagicCard } from '@/components/ui/magic-card';

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
  risk_analysis?: RiskAnalysisPayload;
  comparison_summary?: ComparisonSummaryPayload;
  holdings_overlap?: HoldingsOverlapPayload;
  verdict_context?: string;
  profiles?: Record<string, QuantRecord>;
  ratios?: Record<string, QuantRecord>;
  financials?: Record<string, QuantFinancialRow[]>;
  shareholding?: Record<string, QuantRecord[]>;
  price_history?: Record<string, QuantPriceRow[]>;
  available?: string[];
}

type ComparisonSummaryPayload = {
  headline?: string;
  verdict_cards?: Array<{ label?: string; value?: string; note?: string }>;
  key_differences?: string[];
  missing_data?: Array<{ entity?: string; fields?: string[] }>;
};

type HoldingsOverlapPayload = {
  coverage_status?: string;
  reason?: string;
  entities?: string[];
  as_of_date?: string | null;
  common_holding_count?: number;
  total_overlap_weight?: number;
  fund_a_top_concentration?: number;
  fund_b_top_concentration?: number;
  top_common_holdings?: Array<{
    name?: string;
    isin?: string | null;
    sector?: string | null;
    weight_a?: number;
    weight_b?: number;
    overlap_weight?: number;
  }>;
  sector_overlap?: Array<{
    sector?: string;
    weight_a?: number;
    weight_b?: number;
    overlap_weight?: number;
  }>;
};

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
  research_notes?: Array<{ title: string; content: string }>;
};

type RiskAnalysisItem = {
  entity?: string;
  label?: string;
  level?: string;
  evidence?: string;
  confidence?: string;
};

type RiskAnalysisPayload = {
  asset_type?: string;
  summary?: string;
  items?: RiskAnalysisItem[];
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
  risk_level?: string | null;
  holdings?: Array<{ security_name?: string; sector?: string; weight_pct?: number | string }>;
  sector_allocation?: Array<{ sector_name?: string; weight_pct?: number | string }>;
};

type FundCoverage = Record<string, unknown> & {
  supports?: Record<string, boolean | undefined>;
  supports_1y?: boolean;
  supports_3y?: boolean;
  supports_5y?: boolean;
  history_points?: string | number | null;
  last_nav_date?: string | null;
};

const supportsFundPeriod = (coverage: FundCoverage | undefined, period: Period) => {
  if (!coverage) return false;
  if (period === '1D' || period === '6M') return true;
  if (period === '1Y') return Boolean(coverage.supports_1y ?? coverage.supports?.['1Y']);
  if (period === '3Y') return Boolean(coverage.supports_3y ?? coverage.supports?.['3Y']);
  if (period === '5Y') return Boolean(coverage.supports_5y ?? coverage.supports?.['5Y']);
  return true;
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

const getRiskAnalysis = (data: unknown): RiskAnalysisPayload | null => {
  if (!data || typeof data !== 'object') return null;
  const payload = data as Record<string, unknown>;
  const risk = payload.risk_analysis;
  if (!risk || typeof risk !== 'object') return null;
  return risk as RiskAnalysisPayload;
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
  if (value === null) return 'Not available';
  return value.toFixed(digits);
};

const formatPercent = (value: number | null, digits = 2) => {
  if (value === null) return 'Not available';
  return `${value >= 0 ? '+' : ''}${value.toFixed(digits)}%`;
};

const formatAum = (value: unknown) => {
  const parsed = toNumber(value);
  if (parsed === null) return 'Not available';
  return `₹${parsed.toLocaleString('en-IN')} Cr`;
};

const formatExpense = (value: unknown) => {
  const parsed = toNumber(value);
  if (parsed === null) return 'Not available';
  return `${parsed.toFixed(2)}%`;
};

const formatRiskLabel = (value: unknown) => {
  const label = typeof value === 'string' ? value.trim() : '';
  return label || 'Coverage pending';
};

const compactSchemeName = (name: string | null | undefined) => {
  if (!name) return 'Not available';
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

function PortfolioCompositionPanel({ activeFunds }: { activeFunds: any[] }) {
  const funds = activeFunds.filter(f => f && f.details && (f.details.holdings?.length || f.details.sector_allocation?.length));
  if (funds.length === 0) return null;
  const colsClass = funds.length === 2 ? 'sm:grid-cols-2' : funds.length === 3 ? 'sm:grid-cols-3' : 'sm:grid-cols-4';

  return (
    <div className="space-y-4 mb-6">
      <h3 className="font-serif-display text-xl font-bold text-white tracking-tight">Portfolio Composition</h3>
      <div className={`grid grid-cols-1 ${colsClass} gap-6`}>
        {funds.map((f, i) => {
          const holdings = (f.details.holdings || []).slice(0, 10);
          const sectors = (f.details.sector_allocation || []).slice(0, 5);
          return (
            <div key={i} className="rounded-3xl border border-white/10 bg-white/[0.045] backdrop-blur-md p-5 shadow-[0_24px_90px_rgba(0,0,0,0.18)]">
              <h4 className="font-serif-display text-lg font-bold text-white mb-4 line-clamp-1" title={f.label}>{f.label}</h4>
              
              <div className="mb-6">
                <h5 className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#8ea7cd] mb-3 border-b border-white/10 pb-2">Top Sectors</h5>
                {sectors.length > 0 ? (
                  <div className="space-y-2.5">
                    {sectors.map((s: any, idx: number) => (
                      <div key={idx} className="flex justify-between items-center text-xs">
                        <span className="text-[#c8d8f6] truncate pr-2" title={s.sector_name || s.sector}>{s.sector_name || s.sector || 'Unknown'}</span>
                        <span className="text-white font-mono">{formatPercent(toNumber(s.weight_pct))}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic">No sector data available</p>
                )}
              </div>

              <div>
                <h5 className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#8ea7cd] mb-3 border-b border-white/10 pb-2">Top Holdings</h5>
                {holdings.length > 0 ? (
                  <div className="space-y-2.5">
                    {holdings.map((h: any, idx: number) => (
                      <div key={idx} className="flex justify-between items-center text-xs">
                        <span className="text-[#c8d8f6] truncate pr-2" title={h.security_name}>{h.security_name || 'Unknown'}</span>
                        <span className="text-white font-mono">{formatPercent(toNumber(h.weight_pct))}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 italic">No holdings data available</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function WhyBetterPanel({ payload }: { payload: WhyBetterPayload | null }) {
  if (!payload) return null;
  const winner = payload.winner;
  const confidence = payload.confidence;
  const factors = payload.factor_results || [];
  const freshness = payload.source_freshness || {};
  const freshnessRows = Object.entries(freshness);
  const limitations = payload.data_limitations || [];
  const holdingsBlocked = payload.holdings_based_reasoning?.status === 'blocked';
  const isMf = winner?.asset_type === 'mutual_fund';

  return (
    <MagicCard gradientColor="rgba(0, 255, 157, 0.15)" className="p-6 mb-6">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="w-5 h-5 text-[#00FF9D]" />
        <h3 className="text-sm font-semibold tracking-wide text-white uppercase">Smart Comparative Synthesis</h3>
      </div>
      <p className="whitespace-pre-line text-sm leading-relaxed text-slate-200 border-l-2 border-[#00FF9D] pl-4">
        {payload.summary || 'Deterministic comparison summary unavailable.'}
      </p>
      
      <div className="mt-4 flex flex-wrap gap-2 text-xs">
        <span className="rounded-md border border-white/10 bg-white/[0.03] px-2 py-1 text-slate-300">
          Based on available data: {winner?.status === 'winner' ? (winner.entity_name || winner.entity_id || 'Not available') : winner?.status || 'Not available'}
        </span>
        <span className="rounded-md border border-white/10 bg-white/[0.03] px-2 py-1 text-slate-300">
          Confidence: {confidence?.label || 'Not available'} ({typeof confidence?.score === 'number' ? confidence.score.toFixed(2) : 'Not available'})
        </span>
      </div>

      {factors.length > 0 && (
        <div className="mt-4 grid gap-2 md:grid-cols-2">
          {factors.map((factor, idx) => (
            <div key={`${factor.factor || 'factor'}-${idx}`} className="rounded-md border border-white/5 bg-white/[0.02] p-3 text-xs">
              <div className="font-semibold text-white">{factor.factor || 'Factor'}</div>
              <div className="text-slate-400 mt-1">Winner: <span className="text-[#00FF9D]">{factor.winner || 'No clear edge'}</span></div>
            </div>
          ))}
        </div>
      )}
      
      {limitations.length > 0 && (
        <div className="mt-4 rounded-md border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
          <div className="font-semibold">Data Limitations</div>
          <ul className="mt-1 list-disc space-y-1 pl-4">
            {limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      )}
      {payload.verdict_context && <p className="mt-4 text-xs text-slate-400 italic">{payload.verdict_context}</p>}
    </MagicCard>
  );
}

function RiskAnalysisPanel({ payload }: { payload: RiskAnalysisPayload | null }) {
  const items = payload?.items || [];
  if (!payload || items.length === 0) return null;

  const levelClass = (level: string | undefined) => {
    const value = String(level || '').toLowerCase();
    if (value === 'high') return 'border-rose-300/25 bg-rose-300/10 text-rose-100';
    if (value === 'medium') return 'border-amber-300/25 bg-amber-300/10 text-amber-100';
    if (value === 'not available') return 'border-slate-300/15 bg-slate-300/10 text-slate-200';
    return 'border-emerald-300/20 bg-emerald-300/10 text-emerald-100';
  };

  return (
    <section className="mb-6 rounded-2xl border border-white/10 bg-[#0e182a] p-4">
      <div className="mb-3">
        <h3 className="text-sm font-semibold tracking-wide text-[#9ec5ff]">Risk Analysis</h3>
        <p className="mt-1 text-xs leading-relaxed text-[#8ea7cd]">
          {payload.summary || 'Deterministic risk flags based on available data.'}
        </p>
      </div>
      <div className="grid gap-2 md:grid-cols-2">
        {items.slice(0, 8).map((item, index) => (
          <div key={`${item.entity || 'entity'}-${item.label || 'risk'}-${index}`} className="rounded-xl border border-white/10 bg-white/[0.03] p-3 text-xs">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold text-white">{item.label || 'Risk flag'}</span>
              <span className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.1em] ${levelClass(item.level)}`}>
                {item.level || 'Not available'}
              </span>
            </div>
            <p className="mt-1 text-[#c8d8f6]">{item.entity || 'Entity'}: {item.evidence || 'Evidence unavailable.'}</p>
            <p className="mt-1 text-[#8ea7cd]">Confidence: {item.confidence || 'Not available'}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default function ComparisonView({ ids, type, auxiliaryData }: Props) {
  const [period, setPeriod] = useState<Period>('1Y');
  const { comparisonMode, setComparisonMode } = useCanvasStore();

  const id1 = ids?.[0] || null;
  const id2 = ids?.[1] || null;
  const id3 = ids?.[2] || null;
  const id4 = ids?.[3] || null;
  const isMF = type === 'MUTUAL_FUND' || Boolean(id1 && /^[0-9]+$/.test(id1));

  const fund1 = useFundData(isMF ? id1 : null);
  const fund2 = useFundData(isMF ? id2 : null);
  const fund3 = useFundData(isMF ? id3 : null);
  const fund4 = useFundData(isMF ? id4 : null);
  const fundsData = [fund1, fund2, fund3, fund4].slice(0, Math.max(2, ids.length));

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

  if (!ids || ids.length < 1) {
    return <div className="p-6 text-gray-400">Insufficient data for comparison.</div>;
  }

  const handleReplaceFund = (index: number, newId: string) => {
    const store = useCanvasStore.getState();
    const newIds = [...ids];
    newIds[index] = newId;
    store.setIds(newIds);
  };

  const handleAddFund = (newId: string) => {
    if (ids.length >= 4) return;
    const store = useCanvasStore.getState();
    store.setIds([...ids, newId]);
  };

  const handleRemoveFund = (index: number) => {
    if (ids.length <= 2) return;
    const store = useCanvasStore.getState();
    const newIds = ids.filter((_, i) => i !== index);
    store.setIds(newIds);
  };

  if (!isMF) {
    const comparison = mapQuantResponse(auxiliaryData?.quant_data) || fetchedComparison;
    const whyBetter = getWhyBetter(auxiliaryData?.quant_data) || fetchedWhyBetter;
    const riskAnalysis = getRiskAnalysis(auxiliaryData?.quant_data);
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
      <section className="mb-6">
        <h3 className="mb-3 text-[13px] font-bold uppercase tracking-wider text-[#d7e4fb] pl-1">{title}</h3>
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
        <div className="rounded-2xl bg-white/[0.02] backdrop-blur-md border border-white/5 overflow-hidden shadow-lg">
          <div className="px-5 py-3.5 border-b border-white/10 bg-white/[0.01]">
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
      <div className="comparison-detail finance-compare-wrap p-3 sm:p-6 h-full flex flex-col overflow-hidden max-w-7xl mx-auto w-full bg-[#050505]">
        <div className="mb-5 rounded-2xl bg-white/[0.02] backdrop-blur-md border border-white/5 px-5 py-4 shadow-lg flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl sm:text-2xl font-bold text-white tracking-tight">Stock Comparison Workspace</h2>
            <p className="text-sm text-slate-400 mt-1">
              Source-neutral valuation, growth, quality, and ownership comparison
            </p>
          </div>
          <div className="flex items-center gap-2 w-full sm:w-auto">
            {comparisonMode === 'simple' ? (
              <button
                onClick={() => setComparisonMode('llm')}
                className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#66a3ff] to-[#4f8ff7] px-4 py-2 text-xs font-bold text-slate-950 shadow-lg shadow-[#66a3ff]/20 transition-transform hover:scale-105 active:scale-95 whitespace-nowrap"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Ask AI
              </button>
            ) : (
              <button
                onClick={() => setComparisonMode('simple')}
                className="flex items-center gap-2 rounded-xl bg-[#222] border border-[#333] px-4 py-2 text-xs font-bold text-slate-300 hover:bg-[#333] transition-transform hover:scale-105 active:scale-95 whitespace-nowrap"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
                Hide AI
              </button>
            )}
            <div className="flex-1 sm:w-48">
              <FundSearchSelect
                placeholder={ids[0] || "Select Stock 1"}
                onSelect={(item) => handleReplaceFund(0, item.id)}
              />
            </div>
            <div className="text-slate-500 font-serif font-medium text-xs">VS</div>
            <div className="flex-1 sm:w-48">
              <FundSearchSelect
                placeholder={ids[1] || "Select Stock 2"}
                onSelect={(item) => handleReplaceFund(1, item.id)}
              />
            </div>
          </div>
        </div>
        <div className="custom-scroll flex-1 space-y-5 overflow-y-auto pr-2 pb-10">
          {staleEntities.length > 0 && (
            <div className="rounded-xl border border-amber-400/20 bg-amber-400/10 p-4 text-sm text-amber-100">
              Data may be stale for: {staleEntities.join(', ')}.
            </div>
          )}
          <WhyBetterPanel payload={whyBetter} />
          <RiskAnalysisPanel payload={riskAnalysis} />
          {priceRows.length > 0 && (
            <section className="rounded-2xl bg-white/[0.02] backdrop-blur-md border border-white/5 p-4 shadow-lg">
              <h3 className="mb-3 text-sm font-semibold text-white">Price History</h3>
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

  const loading = fundsData.some((f, i) => i < ids.length && f.loading);
  const error = fundsData.find((f, i) => i < ids.length && f.error)?.error || null;
  const mfQuant = auxiliaryData?.quant_data && typeof auxiliaryData.quant_data === 'object'
    ? auxiliaryData.quant_data as QuantResponsePayload
    : undefined;
  const mfWhyBetter = getWhyBetter(auxiliaryData?.quant_data);
  const mfRiskAnalysis = getRiskAnalysis(auxiliaryData?.quant_data);
  const comparisonSummary = mfQuant?.comparison_summary;
  const holdingsOverlap = mfQuant?.holdings_overlap;
  const periods: Period[] = ['1D', '6M', '1Y', '3Y', '5Y'];
  const comparisonMap =
    auxiliaryData?.quant_data && typeof auxiliaryData.quant_data === 'object'
      ? (auxiliaryData.quant_data as { comparison?: Record<string, unknown> }).comparison
      : auxiliaryData?.comparison;

  const maxFundSlots = Math.min(ids.length + 1, 4);
  const totalCols = maxFundSlots + 1; // 1 label + maxFundSlots
  const colsClass = totalCols === 3 ? 'grid-cols-[1.5fr_1fr_1fr]' :
                    totalCols === 4 ? 'grid-cols-[1.5fr_1fr_1fr_1fr]' :
                    'grid-cols-[1.5fr_1fr_1fr_1fr_1fr]';

  const getWinnerIndex = (label: string, values: (number | null)[]): number | null => {
    const validValues = values.map((v, i) => ({ v, i })).filter(x => x.v !== null);
    if (validValues.length < 2) return null;
    const allSame = validValues.every(x => x.v === validValues[0].v);
    if (allSame) return null;

    const labelLower = label.toLowerCase();
    const isLowerBetter = labelLower.includes('expense') || labelLower.includes('drawdown') || labelLower.includes('volatility');

    validValues.sort((a, b) => isLowerBetter ? a.v! - b.v! : b.v! - a.v!);
    return validValues[0].i;
  };

  const renderGroupedTable = (title: string, rows: Array<{ label: string; values: (string | number | null)[]; winnerIndex: number | null }>) => {
    return (
    <div className="mb-6">
      <div className="py-3 px-1 border-b border-white/10 mb-2">
        <h4 className="text-[13px] font-bold text-white uppercase tracking-wider">{title}</h4>
      </div>
      <div className="flex flex-col">
        {rows.map((row) => (
          <div key={row.label} className={`grid ${colsClass} text-[13px] items-center border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors`}>
            <div className="py-3.5 px-2 font-medium text-slate-400">{row.label}</div>
            {row.values.map((val, i) => (
              <div key={i} className={`py-3.5 px-2 text-left ${row.winnerIndex === i ? 'text-[#66a3ff] font-semibold bg-[#66a3ff]/5' : 'text-slate-200'}`}>
                <span className="flex items-center gap-1.5 font-mono">
                  {val === 'N/A' || val === null ? <span className="text-slate-500">Not available</span> : val}
                  {row.winnerIndex === i && <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#66a3ff] shadow-[0_0_8px_rgba(102,163,255,0.6)]" />}
                </span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )};

  const renderSkeleton = () => (
    <div className="flex-1 space-y-6 overflow-hidden animate-pulse w-full p-3 sm:p-6">
      <div className="h-24 rounded-3xl bg-[#111] border border-[#222] p-5 space-y-3">
        <div className="h-6 w-1/3 rounded bg-white/[0.05]" />
        <div className="h-4 w-1/2 rounded bg-white/[0.05]" />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {[1, 2].map((i) => (
          <div key={i} className="rounded-3xl bg-[#111] border border-[#222] p-5 space-y-3">
            <div className="h-6 w-1/2 rounded bg-white/[0.05]" />
            <div className="h-4 w-3/4 rounded bg-white/[0.05]" />
            <div className="h-5 w-24 rounded bg-white/[0.05]" />
          </div>
        ))}
      </div>

      <div className="rounded-3xl bg-[#111] border border-[#222] p-5 space-y-2">
        <div className="h-5 w-32 rounded bg-white/[0.05]" />
        <div className="h-4 w-full rounded bg-white/[0.05]" />
        <div className="h-4 w-5/6 rounded bg-white/[0.05]" />
      </div>

      <div className="rounded-3xl bg-[#111] border border-[#222] p-5 h-72 flex items-end justify-between gap-4">
        {[...Array(12)].map((_, i) => (
          <div key={i} className="bg-white/[0.03] rounded-t-lg w-full" style={{ height: `${20 + Math.random() * 60}%` }} />
        ))}
      </div>

      <div className="space-y-4">
        <div className="h-6 w-44 rounded bg-white/[0.05]" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2].map((i) => (
            <div key={i} className="rounded-2xl bg-[#111] border border-[#222] overflow-hidden">
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
    <div className="comparison-detail finance-compare-wrap p-3 sm:p-6 h-full flex flex-col overflow-hidden w-full bg-[#050505]">
      <div className="mb-5 px-2 py-4 sm:mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shrink-0">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="rounded bg-[#1a2740] px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider text-[#8ea7cd] border border-[#222]">Research-only</span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight sm:text-2xl">Mutual Fund Workspace</h2>
          <p className="text-sm text-[#a7bad9] mt-1">
            Headline, key differences, tradeoffs, and data limits stay visible before the metric table.
          </p>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
        {comparisonMode === 'simple' ? (
          <button
            onClick={() => setComparisonMode('llm')}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-[#66a3ff] to-[#4f8ff7] px-4 py-2 text-xs font-bold text-slate-950 shadow-lg shadow-[#66a3ff]/20 transition-transform hover:scale-105 active:scale-95 whitespace-nowrap"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Ask AI
          </button>
        ) : (
          <button
            onClick={() => setComparisonMode('simple')}
            className="flex items-center gap-2 rounded-xl bg-[#222] border border-[#333] px-5 py-2.5 text-sm font-bold text-slate-300 hover:bg-[#333] transition-transform hover:scale-105 active:scale-95"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Hide AI
          </button>
        )}
        <div className="flex max-w-full overflow-x-auto rounded-xl bg-white/[0.02] p-1 border border-white/5 gap-1.5 shrink-0 self-end ml-auto">
          {periods.map(p => {
            const isSupported = (() => {
               if (p === '1D' || p === '6M') return true;
               for (let i = 0; i < ids.length; i++) {
                 const cov = fundsData[i]?.coverage as FundCoverage | undefined;
                 if (cov && !supportsFundPeriod(cov, p)) return false;
               }
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

      <div className={`sticky top-0 z-30 bg-[#050505]/95 backdrop-blur-md pb-4 pt-4 mb-6 -mx-3 sm:-mx-6 px-3 sm:px-6`}>
        <div className={`grid ${colsClass} gap-4 items-center`}>
          <div className="font-semibold text-[#8ea7cd] text-sm pl-2">Compare</div>
          {ids.map((id, index) => (
            <div key={index} className="relative">
              <FundSearchSelect
                placeholder={fundsData[index]?.meta?.scheme_name || `Select Fund ${index + 1}`}
                onSelect={(item) => handleReplaceFund(index, item.id)}
              />
              {ids.length > 2 && (
                <button onClick={() => handleRemoveFund(index)} className="absolute -top-2 -right-2 bg-red-500/20 text-red-500 rounded-full w-5 h-5 flex items-center justify-center hover:bg-red-500/40 text-[10px] z-10 shadow-sm border border-red-500/30">
                  &times;
                </button>
              )}
            </div>
          ))}
          {ids.length < 4 && (
            <div>
              <FundSearchSelect
                placeholder="+ Add Fund..."
                onSelect={(item) => handleAddFund(item.id)}
              />
            </div>
          )}
        </div>
      </div>

      {loading && renderSkeleton()}

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

      {!loading && !error && fundsData.every((f, i) => i >= ids.length || f.meta) && (
        <div className="flex-1 overflow-y-auto pr-2 custom-scroll pb-10">
          {(() => {
            const getFundData = (i: number) => {
              const fund = fundsData[i];
              if (!fund || !fund.meta) return null;
              const record = getMfComparisonRecord(comparisonMap, ids[i], fund.meta.scheme_name);

              const alphaRaw = toNumber(record?.alpha_vs_nifty ?? record?.alpha ?? fund.riskMetrics?.alpha_vs_nifty ?? fund.riskMetrics?.alpha);
              const betaRaw = toNumber(record?.beta ?? fund.riskMetrics?.beta);
              const fallback = (alphaRaw === null || betaRaw === null)
                ? computeAlphaBetaFromNav(fund.navData, benchmark.data)
                : { alpha: null as number | null, beta: null as number | null };

              return {
                fund,
                record,
                label: compactSchemeName(fund.meta.scheme_name),
                return1Y: toNumber(fund.returns?.['1Y']),
                return3Y: toNumber(record?.return_3y ?? fund.returns?.['3Y']),
                return5Y: toNumber(fund.returns?.['5Y']),
                volatility: normalizePercent(record?.volatility_1y ?? fund.riskMetrics?.stdDev),
                sharpe: toNumber(record?.sharpe_ratio ?? fund.riskMetrics?.sharpeRatio),
                alpha: alphaRaw ?? fallback.alpha,
                beta: betaRaw ?? fallback.beta,
                drawdown: normalizePercent(record?.max_drawdown_1y ?? fund.riskMetrics?.maxDrawdown),
                riskLabel: formatRiskLabel(record?.risk_level ?? fund.details?.risk_level),
                cov: fund.coverage as FundCoverage | undefined,
                expense: toNumber(record?.expense_ratio ?? fund.details?.expense_ratio),
                aum: toNumber(record?.aum ?? fund.details?.aum),
                historyPts: (fund.coverage as FundCoverage | undefined)?.history_points,
                lastNav: (fund.coverage as FundCoverage | undefined)?.last_nav_date,
                freshness: fund.freshness as Record<string, unknown> | undefined,
                details: fund.details || record
              };
            };

            const activeFunds = Array.from({ length: ids.length }).map((_, i) => getFundData(i)).filter(Boolean) as ReturnType<typeof getFundData>[];
            const freshnessLabel = (fund: NonNullable<ReturnType<typeof getFundData>>) => {
              if (fund.freshness?.status === 'fresh' || fund.freshness?.stale === false) return 'NAV synced';
              if (fund.freshness?.status) return String(fund.freshness.status);
              return fund.lastNav ? 'NAV date available' : 'Coverage pending';
            };
            const keyDifferences = comparisonSummary?.key_differences?.length
              ? comparisonSummary.key_differences
              : ['Compare returns with risk, cost, and source freshness before interpreting any edge.'];
            const tradeoffs = mfWhyBetter?.tradeoffs?.length
              ? mfWhyBetter.tradeoffs
              : ['Different mandates can make direct return-only comparisons incomplete.'];
            const dataLimitations = mfWhyBetter?.data_limitations?.length
              ? mfWhyBetter.data_limitations
              : ['Coverage is limited to available NAV, factsheet, and mapped risk data.'];

            const pGroup = [
              { label: '1Y Return', values: activeFunds.map(f => formatPercent(f!.return1Y)), winnerIndex: getWinnerIndex('1Y Return', activeFunds.map(f => f!.return1Y)) },
              { label: '3Y Return', values: activeFunds.map(f => formatPercent(f!.return3Y)), winnerIndex: getWinnerIndex('3Y Return', activeFunds.map(f => f!.return3Y)) },
              { label: '5Y Return', values: activeFunds.map(f => formatPercent(f!.return5Y)), winnerIndex: getWinnerIndex('5Y Return', activeFunds.map(f => f!.return5Y)) },
              { label: 'Alpha vs Nifty', values: activeFunds.map(f => formatPercent(f!.alpha)), winnerIndex: getWinnerIndex('Alpha', activeFunds.map(f => f!.alpha)) },
            ];

            const rGroup = [
              { label: 'Official Risk Label', values: activeFunds.map(f => f!.riskLabel), winnerIndex: null },
              { label: 'Volatility (1Y)', values: activeFunds.map(f => formatPercent(f!.volatility)), winnerIndex: getWinnerIndex('Volatility', activeFunds.map(f => f!.volatility)) },
              { label: 'Sharpe Ratio', values: activeFunds.map(f => formatPlain(f!.sharpe)), winnerIndex: getWinnerIndex('Sharpe', activeFunds.map(f => f!.sharpe)) },
              { label: 'Beta', values: activeFunds.map(f => formatPlain(f!.beta)), winnerIndex: getWinnerIndex('Beta', activeFunds.map(f => f!.beta)) },
              { label: 'Max Drawdown', values: activeFunds.map(f => formatPercent(f!.drawdown)), winnerIndex: getWinnerIndex('Drawdown', activeFunds.map(f => f!.drawdown)) },
            ];

            const dGroup = [
              { label: 'Expense Ratio', values: activeFunds.map(f => formatExpense(f!.expense)), winnerIndex: getWinnerIndex('Expense Ratio', activeFunds.map(f => f!.expense)) },
              { label: 'AUM', values: activeFunds.map(f => formatAum(f!.aum)), winnerIndex: getWinnerIndex('AUM', activeFunds.map(f => f!.aum)) },
            ];

            const qGroup = [
              { label: 'AMC factsheet', values: activeFunds.map(f => f!.riskLabel === 'Coverage pending' ? 'Coverage pending' : 'Mapped'), winnerIndex: null },
              { label: 'Source freshness', values: activeFunds.map(f => freshnessLabel(f!)), winnerIndex: null },
              { label: 'Risk label source', values: activeFunds.map(f => f!.riskLabel === 'Coverage pending' ? 'Coverage pending' : 'Official'), winnerIndex: null },
              { label: 'NAV points synced', values: activeFunds.map(f => f!.historyPts ? String(f!.historyPts) : 'Not available'), winnerIndex: getWinnerIndex('NAV points', activeFunds.map(f => toNumber(f!.historyPts))) },
              { label: 'Latest NAV Date', values: activeFunds.map(f => f!.lastNav ? String(f!.lastNav) : 'Not available'), winnerIndex: null },
            ];

            const colsClass = ids.length === 2 ? 'sm:grid-cols-2' : ids.length === 3 ? 'sm:grid-cols-3' : 'sm:grid-cols-4';

            return (
              <div className="grid gap-6">

                <div className={`grid grid-cols-1 ${colsClass} gap-4`}>
                  {activeFunds.map((f, index) => (
                    <div key={index} className="rounded-3xl border border-white/10 bg-white/[0.045] backdrop-blur-md shadow-[0_24px_90px_rgba(0,0,0,0.18)] p-5">
                      <h3 className="font-serif-display text-2xl font-bold text-white">{f!.label}</h3>
                      <p className="text-xs text-[#8ea7cd] mt-1 line-clamp-1" title={f!.fund?.meta?.scheme_name}>{f!.fund?.meta?.scheme_name}</p>
                      <div className="mt-4 grid gap-2 text-xs">
                        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                          <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#8ea7cd]">Official risk label</p>
                          <p className="mt-1 font-medium text-white">{f!.riskLabel}</p>
                        </div>
                        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-3">
                          <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[#8ea7cd]">Source freshness</p>
                          <p className="mt-1 font-medium text-white">{freshnessLabel(f!)}</p>
                        </div>
                      </div>
                      <div className="mt-4 flex flex-wrap items-center gap-2">
                         {f!.freshness?.status === 'fresh' || f!.freshness?.stale === false ? (
                            <span className="rounded bg-emerald-500/10 px-2 py-1 text-[10px] font-medium text-emerald-300 border border-emerald-500/20">Fresh NAV</span>
                         ) : (
                            <span className="rounded bg-amber-500/10 px-2 py-1 text-[10px] font-medium text-amber-300 border border-amber-500/20">Stale NAV</span>
                         )}
                         {supportsFundPeriod(f!.cov, '5Y') ? (
                            <span className="rounded bg-[#66a3ff]/10 px-2 py-1 text-[10px] font-medium text-[#66a3ff] border border-[#66a3ff]/20">5Y+ Data</span>
                         ) : supportsFundPeriod(f!.cov, '3Y') ? (
                            <span className="rounded bg-[#66a3ff]/10 px-2 py-1 text-[10px] font-medium text-[#66a3ff] border border-[#66a3ff]/20">3Y Data</span>
                          ) : (
                            <span className="rounded bg-slate-500/10 px-2 py-1 text-[10px] font-medium text-slate-300 border border-slate-500/20">Coverage pending</span>
                         )}
                      </div>
                    </div>
                  ))}
                </div>

                <RiskAnalysisPanel payload={mfRiskAnalysis} />

                <div className="rounded-3xl border border-white/10 bg-white/[0.045] backdrop-blur-md shadow-[0_24px_90px_rgba(0,0,0,0.18)] p-5">
                  <h3 className="mb-2 text-sm font-semibold text-white">Decision clarity</h3>
                  <p className="text-sm leading-relaxed text-[#c8d8f6]">
                    {comparisonSummary?.headline || 'Use this view to compare facts, tradeoffs, and coverage limits before making an independent decision.'}
                  </p>
                  {Array.isArray(comparisonSummary?.verdict_cards) && comparisonSummary.verdict_cards.length > 0 && (
                      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                        {comparisonSummary.verdict_cards.slice(0, 4).map((card) => (
                          <div key={`${card.label}-${card.value}`} className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                            <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#8ea7cd]">{card.label || 'Signal'}</p>
                            <p className="mt-2 text-lg font-semibold text-white">{card.value || 'Not available'}</p>
                            <p className="mt-1 text-xs leading-relaxed text-[#c8d8f6]">{card.note || 'No note available.'}</p>
                          </div>
                        ))}
                      </div>
                  )}
                  <div className="mt-4 grid gap-3 lg:grid-cols-3">
                    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#8ea7cd]">Key differences</p>
                      <ul className="mt-3 list-disc space-y-1 pl-4 text-xs leading-relaxed text-[#c8d8f6]">
                        {keyDifferences.slice(0, 4).map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#8ea7cd]">Tradeoffs</p>
                      <ul className="mt-3 list-disc space-y-1 pl-4 text-xs leading-relaxed text-[#c8d8f6]">
                        {tradeoffs.slice(0, 4).map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                    <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[#8ea7cd]">Data limitations</p>
                      <ul className="mt-3 list-disc space-y-1 pl-4 text-xs leading-relaxed text-[#c8d8f6]">
                        {dataLimitations.slice(0, 4).map((item) => (
                          <li key={item}>{item}</li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>

                <div className="rounded-3xl border border-white/10 bg-white/[0.045] backdrop-blur-md shadow-[0_24px_90px_rgba(0,0,0,0.18)] p-5">
                  <h3 className="mb-2 text-sm font-semibold text-white">Research frame</h3>
                  <p className="text-sm leading-relaxed text-[#c8d8f6]">
                    {activeFunds.some(f => !f!.cov?.supports_1y) ? "No strong overall winner due to limited NAV history." :
                     (mfWhyBetter?.confidence?.score ?? 0) < 0.6 ? "No strong overall winner. Both funds serve different mandates." :
                     "Directional edge based on available data. Asset allocation flexibility and mandate differences still need independent review."}
                  </p>
                </div>

                {holdingsOverlap && (
                  <div className="rounded-3xl border border-white/10 bg-white/[0.045] backdrop-blur-md shadow-[0_24px_90px_rgba(0,0,0,0.18)] p-5">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                      <div>
                        <h3 className="text-sm font-semibold text-white">Holdings overlap</h3>
                        <p className="mt-1 text-xs text-[#8ea7cd]">
                          {holdingsOverlap.coverage_status === 'available'
                            ? `Latest holdings: ${holdingsOverlap.as_of_date || 'date unavailable'}`
                            : holdingsOverlap.reason || 'Holdings overlap unavailable.'}
                        </p>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-right">
                        <p className="text-[11px] uppercase tracking-[0.12em] text-[#8ea7cd]">Overlap weight</p>
                        <p className="text-xl font-semibold text-white">{formatPercent(toNumber(holdingsOverlap.total_overlap_weight), 2)}</p>
                      </div>
                    </div>

                    {holdingsOverlap.coverage_status === 'available' ? (
                      <div className="mt-4 grid gap-4 xl:grid-cols-[1.4fr_1fr]">
                        <div className="overflow-hidden rounded-2xl border border-white/10">
                          <table className="min-w-full text-left text-xs">
                            <thead className="bg-white/[0.05] text-[#8ea7cd]">
                              <tr>
                                <th className="px-3 py-2 font-semibold">Common holding</th>
                                <th className="px-3 py-2 font-semibold">{activeFunds[0]?.label}</th>
                                <th className="px-3 py-2 font-semibold">{activeFunds[1]?.label}</th>
                                <th className="px-3 py-2 font-semibold">Overlap</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-white/10 text-[#d7e4fb]">
                              {(holdingsOverlap.top_common_holdings || []).slice(0, 8).map((item) => (
                                <tr key={`${item.isin || item.name}-${item.overlap_weight}`}>
                                  <td className="px-3 py-2">
                                    <div className="font-medium text-white">{item.name || 'Not available'}</div>
                                    <div className="text-[10px] text-[#8ea7cd]">{item.sector || item.isin || 'Unclassified'}</div>
                                  </td>
                                  <td className="px-3 py-2">{formatPercent(toNumber(item.weight_a), 2)}</td>
                                  <td className="px-3 py-2">{formatPercent(toNumber(item.weight_b), 2)}</td>
                                  <td className="px-3 py-2">{formatPercent(toNumber(item.overlap_weight), 2)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                        <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                          <h4 className="text-xs font-semibold uppercase tracking-[0.12em] text-[#8ea7cd]">Sector overlap</h4>
                          <div className="mt-3 space-y-2">
                            {(holdingsOverlap.sector_overlap || []).slice(0, 6).map((sector) => (
                              <div key={sector.sector} className="flex items-center justify-between gap-3 text-xs text-[#d7e4fb]">
                                <span className="truncate">{sector.sector || 'Unclassified'}</span>
                                <span className="font-mono text-white">{formatPercent(toNumber(sector.overlap_weight), 2)}</span>
                              </div>
                            ))}
                          </div>
                          <div className="mt-4 grid grid-cols-2 gap-3 text-xs">
                            <div>
                              <p className="text-[#8ea7cd]">{activeFunds[0]?.label} top 10</p>
                              <p className="font-semibold text-white">{formatPercent(toNumber(holdingsOverlap.fund_a_top_concentration), 2)}</p>
                            </div>
                            <div>
                              <p className="text-[#8ea7cd]">{activeFunds[1]?.label} top 10</p>
                              <p className="font-semibold text-white">{formatPercent(toNumber(holdingsOverlap.fund_b_top_concentration), 2)}</p>
                            </div>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="mt-4 rounded-2xl bg-white/[0.02] border border-white/5 p-4 text-sm text-slate-300">
                        Holdings overlap will appear when both selected funds have latest holdings data.
                      </div>
                    )}
                  </div>
                )}

                <div className="space-y-4">
                  <h3 className="font-serif-display text-xl font-bold text-white tracking-tight">Grouped Metric Comparison</h3>
                  <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                    {renderGroupedTable('Returns', pGroup)}
                    {renderGroupedTable('Risk', rGroup)}
                    {renderGroupedTable('Cost', dGroup)}
                    {renderGroupedTable('Data quality', qGroup)}
                  </div>
                </div>

                <PortfolioCompositionPanel activeFunds={activeFunds} />

                <div className="rounded-3xl border border-white/10 bg-white/[0.045] backdrop-blur-md shadow-[0_24px_90px_rgba(0,0,0,0.18)] p-5">
                  {ids.length === 2 && activeFunds.length === 2 && activeFunds[0] && activeFunds[1] ? (
                    <FundComparisonChart
                      schemeCodeA={ids[0]}
                      schemeCodeB={ids[1]}
                      nameA={activeFunds[0]?.fund?.meta?.scheme_name ?? 'Fund A'}
                      nameB={activeFunds[1]?.fund?.meta?.scheme_name ?? 'Fund B'}
                      period={period}
                    />
                  ) : ids.length > 2 ? (
                    <div className="text-sm text-[#8ea7cd] text-center p-4">Chart comparison currently supports only 2 funds. Please select 2 funds to view the chart.</div>
                  ) : null}
                </div>

                {mfWhyBetter?.research_notes && mfWhyBetter.research_notes.length > 0 && (
                  <div className="rounded-3xl border border-white/10 bg-white/[0.045] backdrop-blur-md shadow-[0_24px_90px_rgba(0,0,0,0.18)] p-5">
                    <h3 className="mb-4 text-base font-semibold text-white">Research notes</h3>
                    <div className="grid gap-4 sm:grid-cols-3">
                      {mfWhyBetter.research_notes.slice(0, 3).map((note: {title: string; content: string}, idx: number) => (
                        <div key={idx} className="rounded-2xl border border-white/5 bg-white/[0.03] p-5">
                          <h4 className="text-sm font-semibold text-[#8ea7cd] mb-3">{note.title || "Note"}</h4>
                          <p className="text-xs text-[#d7e4fb] leading-relaxed">
                            {note.content}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="rounded-3xl border border-white/10 bg-white/[0.045] backdrop-blur-md shadow-[0_24px_90px_rgba(0,0,0,0.18)] p-5">
                  <p className="text-xs text-slate-400 leading-relaxed">
                    Deterministic comparison based on available local NAV, risk, cost, and freshness factors for selected funds. Not a universal investment verdict.
                  </p>
                  <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-[10px] font-medium text-slate-400">
                    <span className="flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span> Source: AMFI / Internal API
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span> Coverage: {activeFunds.every(f => f?.historyPts) ? 'Full' : 'Partial'}
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span> Latest NAV: {activeFunds.find(f => f?.lastNav)?.lastNav || 'Not available'}
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span> NAV rows fetched: {Math.max(...activeFunds.map(f => Number(f?.historyPts || 0)))}
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
