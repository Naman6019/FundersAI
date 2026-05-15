'use client';

import { useMemo, useState, useEffect } from 'react';
import { useFundData } from '../../hooks/useFundData';
import { useBenchmarkData } from '../../hooks/useBenchmarkData';
import { 
  toReturnsArray, 
  computeCAGR, 
  computeReturns, 
  computeSharpe, 
  computeStdDev 
} from '../../lib/fundMetrics';
import { 
  calculateBeta, 
  calculateAlpha
} from '../../lib/quantUtils';
import { useCanvasStore } from '@/store/useCanvasStore';
import { TrendingUp, ShieldAlert, PieChart, Activity, Wallet, type LucideIcon } from 'lucide-react';


interface Props {
  schemeCodeA: string;
  schemeCodeB: string;
}

type FundExtraMeta = {
  aum?: string | number | null;
  expense_ratio?: string | number | null;
};

type ComparisonFundData = {
  scheme_code?: string | number | null;
  name?: string;
  beta?: string | number | null;
  alpha_vs_nifty?: string | number | null;
  aum?: string | number | null;
  expense_ratio?: string | number | null;
  holdings?: Array<Record<string, unknown>> | null;
  sector_allocation?: Array<Record<string, unknown>> | null;
  source_summary?: { holdings_as_of_date?: string | null } | null;
};

function MetricCard({ label, value, tooltip, icon: Icon, subValue }: { label: string, value: string | null, tooltip: string, icon?: LucideIcon, subValue?: string }) {
  return (
    <div className="group relative cursor-help rounded-xl border border-[#324562] bg-[#12203a] p-4 shadow-lg transition-all duration-200 hover:border-[#5f8ed6] sm:rounded-2xl sm:p-5">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {Icon && <Icon size={16} className="text-[#7cadff]" />}
          <div className="text-xs font-bold uppercase tracking-widest text-[#9fb8df]">{label}</div>
        </div>
      </div>
      <div className="flex flex-col gap-1">
        <div className="text-xl font-black tracking-tight text-white sm:text-2xl">{value ?? '—'}</div>
        {subValue && <div className="text-[10px] font-medium text-[#7d94b7]">{subValue}</div>}
      </div>
      <div className="pointer-events-none absolute bottom-full left-1/2 z-30 mb-3 invisible w-64 -translate-x-1/2 rounded-xl border border-[#3b4f70] bg-[#0e182a] p-3 text-xs leading-relaxed text-[#c5d7f2] opacity-0 shadow-2xl transition-all group-hover:visible group-hover:opacity-100">
        {tooltip}
        <div className="absolute left-1/2 top-full -translate-x-1/2 border-8 border-transparent border-t-[#0e182a]"></div>
      </div>
    </div>
  );
}

function FundColumn({ schemeCode, colorHex }: { schemeCode: string, colorHex: string }) {
  const { navData, meta, details, returns: apiReturns, riskMetrics: apiRiskMetrics } = useFundData(schemeCode);
  const benchmark = useBenchmarkData();
  const [extraMeta, setExtraMeta] = useState<FundExtraMeta | null>(null);
  const { auxiliaryData } = useCanvasStore();

  useEffect(() => {
    if (!schemeCode) return;
    fetch(`/api/mf/${schemeCode}`)
      .then(res => res.json())
      .then(json => {
        if (json.details) setExtraMeta(json.details as FundExtraMeta);
      })
      .catch(err => console.error("Error fetching extra meta:", err));
  }, [schemeCode]);

  const portfolioSnapshot = useMemo(() => {
    const quantComparison =
      auxiliaryData?.quant_data && typeof auxiliaryData.quant_data === 'object'
        ? (auxiliaryData.quant_data as { comparison?: Record<string, unknown> }).comparison
        : undefined;
    const comparisonData = quantComparison ?? auxiliaryData?.comparison;
    if (!comparisonData || typeof comparisonData !== 'object') {
      return { holdings: [] as Array<{ name: string; weight: number | null }>, sectors: [] as Array<{ name: string; weight: number | null }>, asOf: null as string | null };
    }

    const fundName = (meta?.scheme_name || '').toLowerCase();
    let matched: ComparisonFundData | null = null;

    for (const val of Object.values(comparisonData)) {
      const data = val as ComparisonFundData;
      const payloadCode = data?.scheme_code;
      if (payloadCode !== null && payloadCode !== undefined && String(payloadCode) === String(schemeCode)) {
        matched = data;
        break;
      }
      const backendName = typeof data?.name === 'string' ? data.name.toLowerCase() : '';
      if (!backendName || !fundName) continue;
      if (fundName.includes(backendName) || backendName.includes(fundName)) {
        matched = data;
        break;
      }
    }

    const toWeight = (value: unknown): number | null => {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : null;
    };

    const holdings = Array.isArray(matched?.holdings)
      ? matched!.holdings
          .map((row) => {
            const rec = row as Record<string, unknown>;
            const name = String(rec.security_name ?? rec.name ?? rec.holding ?? '').trim();
            if (!name) return null;
            return {
              name,
              weight: toWeight(rec.weight_pct ?? rec.weight),
            };
          })
          .filter((row): row is { name: string; weight: number | null } => Boolean(row))
          .sort((a, b) => (b.weight ?? -1) - (a.weight ?? -1))
          .slice(0, 6)
      : [];

    const sectors = Array.isArray(matched?.sector_allocation)
      ? matched!.sector_allocation
          .map((row) => {
            const rec = row as Record<string, unknown>;
            const name = String(rec.sector ?? rec.name ?? '').trim();
            if (!name) return null;
            return {
              name,
              weight: toWeight(rec.weight_pct ?? rec.weight),
            };
          })
          .filter((row): row is { name: string; weight: number | null } => Boolean(row))
          .sort((a, b) => (b.weight ?? -1) - (a.weight ?? -1))
          .slice(0, 6)
      : [];

    return {
      holdings,
      sectors,
      asOf: matched?.source_summary?.holdings_as_of_date || null,
    };
  }, [auxiliaryData, meta?.scheme_name, schemeCode]);

  const metrics = useMemo(() => {
    if (!navData) return null;
    
    const returns = computeReturns(navData);
    const cagr1Y = apiReturns?.['1Y'] ?? computeCAGR(navData, 1);
    const cagr3Y = apiReturns?.['3Y'] ?? computeCAGR(navData, 3);
    const cagr5Y = apiReturns?.['5Y'] ?? computeCAGR(navData, 5);
    const dailyReturns = toReturnsArray(navData);
    
    let beta: number | null = null;
    let alpha: number | null = null;
    let precomputedAum: string | null = null;
    let precomputedExpenseRatio: string | null = null;

    // --- USE PRE-FETCHED DATA FROM CHAT IF AVAILABLE ---
    const quantComparison =
      auxiliaryData?.quant_data && typeof auxiliaryData.quant_data === 'object'
        ? (auxiliaryData.quant_data as { comparison?: Record<string, unknown> }).comparison
        : undefined;
    const comparisonData = quantComparison ?? auxiliaryData?.comparison;

    if (comparisonData) {
       // Look for this fund in comparison data
       // Names might match partially
       const fundName = meta?.scheme_name?.toLowerCase() || '';
       for (const [key, val] of Object.entries(comparisonData)) {
          const keyLower = key.toLowerCase();
          const data = val as ComparisonFundData;
          const backendName = typeof data?.name === 'string' ? data.name.toLowerCase() : '';
          const candidates = [keyLower, backendName].filter(Boolean);

          const isMatch = candidates.some((candidate: string) => {
            const words = candidate.split(/\s+/).filter((w: string) => w.length > 2);
            const isFuzzyMatch = words.length > 0 && words.every((word: string) => fundName.includes(word));
            return isFuzzyMatch || fundName.includes(candidate) || candidate.includes(fundName);
          });

          if (isMatch) {
             if (data.beta && data.beta !== 'N/A') beta = parseFloat(String(data.beta));
             if (data.alpha_vs_nifty && data.alpha_vs_nifty !== 'N/A') alpha = parseFloat(String(data.alpha_vs_nifty));
             if (data.aum && data.aum !== 'N/A') precomputedAum = data.aum.toString();
             if (data.expense_ratio && data.expense_ratio !== 'N/A') precomputedExpenseRatio = data.expense_ratio.toString();
          }
       }
    }

    if (beta === null && typeof apiRiskMetrics?.beta === 'number') {
      beta = apiRiskMetrics.beta;
    }
    if (alpha === null && typeof apiRiskMetrics?.alpha_vs_nifty === 'number') {
      alpha = apiRiskMetrics.alpha_vs_nifty;
    }
    
    // --- FALLBACK TO LOCAL CALCULATION ---
    if ((beta === null || alpha === null) && benchmark.data && navData.length > 20) {
      const chronologicalFund = [...navData].reverse();
      const benchMap = new Map<string, number>();
      benchmark.data.forEach(d => benchMap.set(d.date, d.close));

      const getBenchPrice = (dateStr: string) => {
        if (benchMap.has(dateStr)) return benchMap.get(dateStr);
        const [d, m, y] = dateStr.split('-').map(Number);
        const date = new Date(Date.UTC(y, m - 1, d));
        for (let offset = -1; offset >= -3; offset--) {
          const adj = new Date(date);
          adj.setUTCDate(date.getUTCDate() + offset);
          const adjStr = `${String(adj.getUTCDate()).padStart(2, '0')}-${String(adj.getUTCMonth() + 1).padStart(2, '0')}-${adj.getUTCFullYear()}`;
          if (benchMap.has(adjStr)) return benchMap.get(adjStr);
        }
        return null;
      };

      const alignedFund: number[] = [];
      const alignedBench: number[] = [];
      
      for (let i = 1; i < chronologicalFund.length; i++) {
        const bCurr = getBenchPrice(chronologicalFund[i].date);
        const bPrev = getBenchPrice(chronologicalFund[i-1].date);
        
        if (typeof bCurr === 'number' && typeof bPrev === 'number') {
          const fundRet = (parseFloat(chronologicalFund[i].nav) / parseFloat(chronologicalFund[i-1].nav)) - 1;
          const benchRet = (bCurr / bPrev) - 1;
          alignedFund.push(fundRet);
          alignedBench.push(benchRet);
        }
      }

      if (alignedFund.length > 10) {
        const calcBeta = calculateBeta(alignedFund, alignedBench);
        if (beta === null) beta = calcBeta;

        if (alpha === null) {
          const totalFundRet = alignedFund.reduce((acc, r) => acc * (1 + r), 1);
          const totalBenchRet = alignedBench.reduce((acc, r) => acc * (1 + r), 1);
          const years = alignedFund.length / 252;
          if (years > 0.05) {
            const fCAGR = Math.pow(totalFundRet, 1 / years) - 1;
            const bCAGR = Math.pow(totalBenchRet, 1 / years) - 1;
            alpha = calculateAlpha(fCAGR, bCAGR, beta) * 100;
          }
        }
      }
    }

    const apiStdDev = typeof apiRiskMetrics?.stdDev === 'number'
      ? (Math.abs(apiRiskMetrics.stdDev) <= 1 ? apiRiskMetrics.stdDev * 100 : apiRiskMetrics.stdDev)
      : null;

    return {
      returns, cagr1Y, cagr3Y, cagr5Y, beta, alpha, precomputedAum, precomputedExpenseRatio,
      sharpe: typeof apiRiskMetrics?.sharpeRatio === 'number' ? apiRiskMetrics.sharpeRatio : computeSharpe(dailyReturns),
      stdDev: apiStdDev ?? computeStdDev(dailyReturns)
    };
  }, [navData, benchmark.data, auxiliaryData, meta, apiReturns, apiRiskMetrics]);

  if (!navData || !meta || !metrics) {
    return (
      <div className="flex min-h-[500px] flex-1 flex-col items-center justify-center p-12 text-center text-gray-500">
        <div className="relative w-16 h-16 mb-6">
            <div className="absolute inset-0 rounded-full border-4 border-white/5"></div>
            <div className="absolute inset-0 animate-spin rounded-full border-4 border-t-[#4f8ff7]"></div>
        </div>
        <p className="animate-pulse font-medium text-white">Preparing fund comparison signals...</p>
      </div>
    );
  }

  const latestNav = parseFloat(navData[0].nav).toFixed(2);
  const navDate = navData[0].date;
  const aum = details?.aum ?? extraMeta?.aum;
  const expenseRatio = details?.expense_ratio ?? extraMeta?.expense_ratio;

  const returnRow = (label: string, val: number | null, isCAGR = false) => (
    <div className="group/row flex items-center justify-between rounded-xl border-b border-white/5 px-3 py-3.5 text-sm transition-all hover:bg-white/5">
      <span className="text-[#a6bbdc] transition-colors group-hover/row:text-white">{label}</span>
      <span className={`font-bold flex items-center gap-1.5 ${val === null ? 'text-gray-600' : val > 0 ? 'text-green-400' : 'text-red-400'}`}>
        {val !== null ? `${val > 0 ? '+' : ''}${val.toFixed(2)}%` : 'N/A'}
        {isCAGR && val !== null && <span className="rounded bg-white/5 px-1.5 py-0.5 text-[9px] uppercase tracking-tighter text-[#8ca5cb]">CAGR</span>}
      </span>
    </div>
  );

  return (
    <div className="flex flex-1 flex-col gap-6 p-4 sm:gap-8 sm:p-6">
      <div className="flex flex-col gap-3">
        <h3 className="group relative cursor-default truncate text-2xl font-black leading-tight tracking-tight" style={{ color: colorHex }}>
          <span className="truncate block" title={meta.scheme_name}>{meta.scheme_name}</span>
        </h3>
        <div className="flex items-center gap-3">
          <span className="rounded-lg border border-white/10 bg-white/10 px-3 py-1 text-[10px] font-black uppercase tracking-[0.2em] text-white">
            {meta.scheme_category}
          </span>
          <span className="h-1.5 w-1.5 rounded-full bg-white/20"></span>
          <span className="text-[10px] font-bold uppercase tracking-widest text-[#95abd0]">{meta.fund_house}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:gap-4">
          <div className="flex flex-col gap-1 rounded-xl border border-[#2f4260] bg-[#111d32] p-4 shadow-2xl sm:rounded-2xl sm:p-5">
              <div className="mb-1 text-[10px] font-black uppercase tracking-widest text-[#8ca5cb]">Latest NAV</div>
              <div className="text-xl font-bold tracking-tighter text-white">₹{latestNav}</div>
              <div className="text-[10px] font-medium text-[#7690b6]">As of {navDate}</div>
          </div>
          <div className="flex flex-col gap-1 rounded-xl border border-[#2f4260] bg-[#111d32] p-4 shadow-2xl sm:rounded-2xl sm:p-5">
              <div className="mb-1 text-[10px] font-black uppercase tracking-widest text-[#8ca5cb]">Total AUM</div>
              <div className="text-xl font-bold tracking-tighter text-[#8bb5ff]">
                  {metrics.precomputedAum && metrics.precomputedAum !== 'N/A' ? `₹${metrics.precomputedAum} Cr` : (aum ? `₹${aum} Cr` : 'Unavailable')}
              </div>
              <div className="text-[10px] font-medium leading-none text-[#7690b6]">Based on latest available snapshot</div>
          </div>
      </div>

      <div className="grid grid-cols-1">
          <div className="flex items-center justify-between rounded-xl border border-[#2f4260] bg-[#111d32] p-4 shadow-2xl sm:rounded-2xl sm:p-5">
              <div className="flex items-center gap-3">
                <Wallet size={16} className="text-[#9fb8df]" />
                <div className="text-[10px] font-black uppercase tracking-widest text-[#8ca5cb]">Expense Ratio</div>
              </div>
              <div className="text-lg font-bold tracking-tighter text-white">
                  {metrics.precomputedExpenseRatio && metrics.precomputedExpenseRatio !== 'N/A' ? `${metrics.precomputedExpenseRatio}%` : (expenseRatio ? `${expenseRatio}%` : 'Unavailable')}
              </div>
          </div>
      </div>

      <div className="rounded-2xl border border-[#324562] bg-[#101b2f] p-4 shadow-2xl sm:rounded-3xl sm:p-7">
        <div className="flex items-center gap-3 mb-6">
          <TrendingUp size={18} className="text-green-400" />
          <h4 className="text-xs font-black uppercase tracking-[0.2em] text-white">Absolute Performance</h4>
        </div>
        <div className="space-y-1">
          {returnRow('1 Month', metrics.returns['1M'])}
          {returnRow('6 Months', metrics.returns['6M'])}
          {returnRow('1 Year', metrics.returns['1Y'])}
          {returnRow('3 Years', metrics.cagr3Y, true)}
          {returnRow('5 Years', metrics.cagr5Y, true)}
        </div>
      </div>

      <div className="rounded-2xl border border-[#324562] bg-[#101b2f] p-4 shadow-2xl sm:rounded-3xl sm:p-7">
        <div className="flex items-center gap-3 mb-6">
          <ShieldAlert size={18} className="text-red-400" />
          <h4 className="text-xs font-black uppercase tracking-[0.2em] text-white">Risk Metrics</h4>
        </div>
        <div className="grid grid-cols-2 gap-3 sm:gap-4">
          <MetricCard 
            label="Alpha" 
            value={metrics.alpha !== null ? (metrics.alpha > 0 ? '+' : '') + metrics.alpha.toFixed(2) + '%' : null} 
            tooltip="Jensen's Alpha: Excess return over benchmark (Nifty 50) after risk adjustment. Positive means outperformance." 
            icon={TrendingUp}
            subValue="vs NIFTY 50"
          />
          <MetricCard 
            label="Beta" 
            value={metrics.beta !== null ? metrics.beta.toFixed(2) : null} 
            tooltip="Systematic Risk: Volatility relative to the market. 1.0 = tracks market, >1.0 = high sensitivity." 
            icon={Activity}
            subValue="Volatility Coeff."
          />
          <MetricCard 
            label="Sharpe" 
            value={metrics.sharpe !== null ? metrics.sharpe.toFixed(2) : null} 
            tooltip="Risk-adjusted Return: Efficiency of the fund in generating returns per unit of total risk." 
            icon={ShieldAlert}
            subValue="Efficiency"
          />
          <MetricCard 
            label="Volatility" 
            value={metrics.stdDev !== null ? metrics.stdDev.toFixed(2) + '%' : null} 
            tooltip="Standard Deviation: The degree to which the NAV fluctuates. Lower is more stable." 
            icon={Activity}
            subValue="Ann. Std Dev"
          />
        </div>
      </div>

      <div className="rounded-2xl border border-dashed border-[#3a4e6f] bg-[#0f1a2b] p-5 sm:rounded-3xl sm:p-6">
        <div className="mb-4 flex items-center gap-3">
          <PieChart size={20} className="text-[#8ca5cb]" />
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-[#8ca5cb]">Portfolio Snapshot</div>
        </div>
        {portfolioSnapshot.asOf && (
          <div className="mb-3 text-[10px] text-[#8ea7cd]">As of {portfolioSnapshot.asOf}</div>
        )}
        <div className="grid grid-cols-1 gap-3">
          <div className="rounded-xl border border-white/10 bg-[#101b2f] p-3">
            <div className="mb-2 text-[10px] font-black uppercase tracking-widest text-[#9fb8df]">Top Holdings</div>
            {portfolioSnapshot.holdings.length > 0 ? (
              <div className="space-y-1.5">
                {portfolioSnapshot.holdings.map((row) => (
                  <div key={`h-${row.name}`} className="flex items-center justify-between text-[11px] text-[#d7e4fb]">
                    <span className="truncate pr-2">{row.name}</span>
                    <span>{row.weight !== null ? `${row.weight.toFixed(2)}%` : 'N/A'}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[10px] leading-relaxed text-[#7690b6]">Holdings not available for this matched scheme yet.</p>
            )}
          </div>
          <div className="rounded-xl border border-white/10 bg-[#101b2f] p-3">
            <div className="mb-2 text-[10px] font-black uppercase tracking-widest text-[#9fb8df]">Top Sectors</div>
            {portfolioSnapshot.sectors.length > 0 ? (
              <div className="space-y-1.5">
                {portfolioSnapshot.sectors.map((row) => (
                  <div key={`s-${row.name}`} className="flex items-center justify-between text-[11px] text-[#d7e4fb]">
                    <span className="truncate pr-2">{row.name}</span>
                    <span>{row.weight !== null ? `${row.weight.toFixed(2)}%` : 'N/A'}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[10px] leading-relaxed text-[#7690b6]">Sector allocation not available for this matched scheme yet.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function FundDetailsPanel({ schemeCodeA, schemeCodeB }: Props) {
  return (
    <div className="relative mx-auto mb-12 flex w-full max-w-7xl flex-col">
      <div className="relative flex flex-col items-stretch md:flex-row">
        <FundColumn schemeCode={schemeCodeA} colorHex="#3B82F6" />
        
        <div className="relative flex items-center justify-center p-6 md:flex-col">
          <div className="absolute bottom-0 left-1/2 top-0 hidden w-[1px] bg-gradient-to-b from-transparent via-white/15 to-transparent md:block"></div>
          <div className="relative z-10 flex h-12 w-12 items-center justify-center rounded-full border border-[#3a4e70] bg-[#0f1728] text-[10px] font-black text-[#9cb6df] shadow-2xl ring-8 ring-[#0f1728]/70">
            VS
          </div>
          <div className="ml-4 h-[1px] flex-1 bg-gradient-to-r from-transparent via-white/10 to-transparent md:hidden"></div>
        </div>

        <FundColumn schemeCode={schemeCodeB} colorHex="#F97316" />
      </div>
    </div>
  );
}
