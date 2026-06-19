'use client';

import { useEffect, useState } from 'react';
import { useCanvasStore } from '@/store/useCanvasStore';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Sparkles, MessageSquare, TrendingUp, AlertTriangle } from 'lucide-react';
import { motion } from 'framer-motion';
import { MagicCard } from '@/components/ui/magic-card';
import { NumberTicker } from '@/components/ui/number-ticker';
import { ShimmerButton } from '@/components/ui/shimmer-button';
import InlineCopilot from './InlineCopilot';
import type { MFDetailApiResponse } from '@/types/funds';

const SUGGESTED_COMPARISONS = [
  { code: '119062', name: 'Axis Bluechip Fund' },
  { code: '120503', name: 'Nippon India Small Cap Fund' },
  { code: '118269', name: 'HDFC Mid-Cap Opportunities Fund' }
];

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        className="rounded-xl border border-[#00FF9D]/30 bg-[#050505]/95 p-4 shadow-[0_8px_30px_rgba(0,255,157,0.12)] backdrop-blur-md"
      >
        <p className="text-xs font-semibold text-slate-400 mb-1">{label}</p>
        <p className="text-xl font-mono font-bold text-[#00FF9D]">
          ₹{payload[0].value.toFixed(2)}
        </p>
      </motion.div>
    );
  }
  return null;
};

function MFDetailSkeleton() {
  return (
    <div className="flex-1 space-y-6 overflow-hidden p-6">
      <div className="space-y-3 pb-4 border-b border-white/5">
        <div className="h-8 w-2/3 rounded-lg bg-white/[0.05] animate-pulse" />
        <div className="flex gap-2">
          <div className="h-5 w-24 rounded bg-white/[0.05] animate-pulse" />
          <div className="h-5 w-20 rounded bg-white/[0.05] animate-pulse" />
          <div className="h-5 w-28 rounded bg-white/[0.05] animate-pulse" />
        </div>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white/[0.03] h-28 rounded-xl border border-white/5 animate-pulse" />
        ))}
      </div>
      <div className="space-y-3">
        <div className="h-6 w-36 rounded bg-white/[0.05] animate-pulse" />
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 rounded-lg bg-white/[0.03] border border-white/5 animate-pulse" />
          ))}
        </div>
      </div>
      <div className="h-64 rounded-xl bg-white/[0.02] border border-white/5 animate-pulse mt-4" />
    </div>
  );
}

export default function MFDetailView({ schemeCode }: { schemeCode: string }) {
  const [data, setData] = useState<MFDetailApiResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { setView, setIds } = useCanvasStore();
  const [aiSummary, setAiSummary] = useState<string | null>(null);
  const [isGeneratingSummary, setIsGeneratingSummary] = useState(false);

  useEffect(() => {
    if (!schemeCode) return;
    const fetchMF = async () => {
      setLoading(true);
      setError('');
      setAiSummary(null);
      try {
        const res = await fetch(`/api/mf/${schemeCode}`);
        if (!res.ok) throw new Error('Failed to load Mutual Fund details');
        const json = (await res.json()) as MFDetailApiResponse;
        setData(json);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to load Mutual Fund details');
      }
      setLoading(false);
    };
    fetchMF();
  }, [schemeCode]);

  const generateSummary = async () => {
    if (!data) return;
    setIsGeneratingSummary(true);
    // Simulated AI fetch for now. Real implementation would hit OpenRouter endpoint.
    setTimeout(() => {
      setAiSummary(
        "This fund has demonstrated strong momentum over the past 3 years, consistently outperforming its category average. " +
        "However, its high expense ratio and significant sector concentration in Financials introduce higher volatility. " +
        "Best suited for aggressive long-term portfolios."
      );
      setIsGeneratingSummary(false);
    }, 1500);
  };

  if (!schemeCode) return <div className="p-6 text-slate-400">No fund selected.</div>;

  const navDateLabel = data?.details.nav_date ? new Date(data.details.nav_date).toLocaleDateString() : 'Not available';
  const returns = data?.returns;
  const riskMetrics = data?.riskMetrics ?? null;
  const riskLabel = typeof data?.details.risk_level === 'string' && data.details.risk_level.trim()
    ? data.details.risk_level.trim()
    : null;

  return (
    <div className="mf-detail h-full flex flex-col text-slate-100 overflow-hidden relative">
      {loading && <MFDetailSkeleton />}
      {error && (
        <div className="m-6 rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-400 shadow-lg">
          <AlertTriangle className="inline-block w-4 h-4 mr-2" /> Error: {error}
        </div>
      )}
      
      {!loading && !error && data && (
        <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar relative">
          
          {/* Header Section */}
          <div className="flex items-start justify-between border-b border-white/5 pb-6">
            <div>
              <h2 className="text-3xl font-bold tracking-tight text-white mb-3">{data.details.scheme_name}</h2>
              <div className="flex gap-2 flex-wrap text-xs font-medium">
                <span className="bg-white/5 border border-white/10 px-3 py-1 rounded-full text-slate-300">{data.details.fund_house}</span>
                <span className="bg-[#00FF9D]/10 border border-[#00FF9D]/20 text-[#00FF9D] px-3 py-1 rounded-full">{data.details.category}</span>
                <span className="bg-purple-500/10 border border-purple-500/20 text-purple-300 px-3 py-1 rounded-full">{data.details.sub_category}</span>
                <span className="bg-amber-500/10 border border-amber-500/20 text-amber-200 px-3 py-1 rounded-full">
                  Risk: {riskLabel || 'Unavailable'}
                </span>
              </div>
            </div>
          </div>

          {/* AI One-Minute Read */}
          <MagicCard 
            className="w-full flex-col items-center justify-center shadow-2xl p-6"
            gradientColor="rgba(0, 255, 157, 0.15)"
          >
            <div className="flex items-center gap-2 mb-3">
              <Sparkles className="w-5 h-5 text-[#00FF9D]" />
              <h3 className="text-sm font-semibold tracking-wide text-white uppercase">One-Minute AI Read</h3>
            </div>
            {!aiSummary ? (
              <div className="flex items-center justify-between">
                <p className="text-sm text-slate-400">Generate an instant, contextual summary of this fund's performance and risk profile using Nemotron 3 Ultra.</p>
                <button 
                  onClick={generateSummary}
                  disabled={isGeneratingSummary}
                  className="bg-white/10 hover:bg-white/20 text-white px-4 py-2 rounded-md text-sm font-medium transition-colors border border-white/5"
                >
                  {isGeneratingSummary ? 'Analyzing...' : 'Generate Summary'}
                </button>
              </div>
            ) : (
              <p className="text-sm text-slate-200 leading-relaxed border-l-2 border-[#00FF9D] pl-4">{aiSummary}</p>
            )}
          </MagicCard>

          {/* Core Metrics Bento Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MagicCard gradientColor="rgba(255,255,255,0.05)" className="p-5 flex flex-col gap-1">
              <div className="text-slate-400 text-[10px] uppercase tracking-widest font-medium">NAV ({navDateLabel})</div>
              <div className="font-mono text-3xl font-bold text-white mt-1">
                ₹<NumberTicker value={Number(data.details.nav) || 0} decimalPlaces={2} className="text-white" />
              </div>
            </MagicCard>
            <MagicCard gradientColor="rgba(255,255,255,0.05)" className="p-5 flex flex-col gap-1">
              <div className="text-slate-400 text-[10px] uppercase tracking-widest font-medium">AUM (Cr)</div>
              <div className="font-mono text-3xl font-bold text-white mt-1">
                {data.details.aum ? <>₹<NumberTicker value={Number(data.details.aum) || 0} className="text-white" /></> : 'N/A'}
              </div>
            </MagicCard>
            <MagicCard gradientColor="rgba(255,255,255,0.05)" className="p-5 flex flex-col gap-1">
              <div className="text-slate-400 text-[10px] uppercase tracking-widest font-medium">Expense Ratio</div>
              <div className="font-mono text-3xl font-bold text-white mt-1">
                {data.details.expense_ratio ? <><NumberTicker value={Number(data.details.expense_ratio) || 0} decimalPlaces={2} className="text-white" />%</> : 'N/A'}
              </div>
            </MagicCard>
            <MagicCard gradientColor="rgba(255,255,255,0.05)" className="p-5 flex flex-col gap-1">
              <div className="text-slate-400 text-[10px] uppercase tracking-widest font-medium">Exit Load</div>
              <div className="text-sm font-medium text-slate-300 mt-auto leading-tight" title={data.details.exit_load || 'Not available'}>
                {data.details.exit_load || 'Not available'}
              </div>
            </MagicCard>
          </div>

          {/* Returns & Risk Layout */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <h3 className="text-xs font-semibold text-slate-400 tracking-widest uppercase ml-1">Historical Returns (CAGR)</h3>
              <div className="grid grid-cols-3 gap-3 text-center">
                <div className="bg-[#0f172a]/50 rounded-xl border border-white/5 p-4">
                  <div className="text-slate-500 text-[10px] uppercase tracking-widest font-medium mb-1">1 Year</div>
                  <div className={`font-mono font-bold text-xl ${(returns?.['1Y'] ?? 0) > 0 ? 'text-[#00FF9D]' : 'text-rose-400'}`}>
                    {returns?.['1Y'] != null ? <><NumberTicker value={returns['1Y']} decimalPlaces={2} className={(returns['1Y'] ?? 0) > 0 ? 'text-[#00FF9D]' : 'text-rose-400'} />%</> : 'N/A'}
                  </div>
                </div>
                <div className="bg-[#0f172a]/50 rounded-xl border border-white/5 p-4">
                  <div className="text-slate-500 text-[10px] uppercase tracking-widest font-medium mb-1">3 Years</div>
                  <div className={`font-mono font-bold text-xl ${(returns?.['3Y'] ?? 0) > 0 ? 'text-[#00FF9D]' : 'text-rose-400'}`}>
                    {returns?.['3Y'] != null ? <><NumberTicker value={returns['3Y']} decimalPlaces={2} className={(returns['3Y'] ?? 0) > 0 ? 'text-[#00FF9D]' : 'text-rose-400'} />%</> : 'N/A'}
                  </div>
                </div>
                <div className="bg-[#0f172a]/50 rounded-xl border border-white/5 p-4">
                  <div className="text-slate-500 text-[10px] uppercase tracking-widest font-medium mb-1">5 Years</div>
                  <div className={`font-mono font-bold text-xl ${(returns?.['5Y'] ?? 0) > 0 ? 'text-[#00FF9D]' : 'text-rose-400'}`}>
                    {returns?.['5Y'] != null ? <><NumberTicker value={returns['5Y']} decimalPlaces={2} className={(returns['5Y'] ?? 0) > 0 ? 'text-[#00FF9D]' : 'text-rose-400'} />%</> : 'N/A'}
                  </div>
                </div>
              </div>
            </div>

            {riskMetrics && (
              <div className="space-y-4">
                <h3 className="text-xs font-semibold text-slate-400 tracking-widest uppercase ml-1">Risk Metrics</h3>
                <div className="grid grid-cols-2 gap-3 text-center">
                  <div className="bg-[#0f172a]/50 rounded-xl border border-white/5 p-4">
                    <div className="text-slate-500 text-[10px] uppercase tracking-widest font-medium mb-1">Sharpe Ratio</div>
                    <div className={`font-mono font-bold text-xl ${(riskMetrics.sharpeRatio ?? 0) >= 1 ? 'text-[#00FF9D]' : (riskMetrics.sharpeRatio ?? 0) >= 0 ? 'text-amber-300' : 'text-rose-400'}`}>
                      {riskMetrics.sharpeRatio != null ? <NumberTicker value={riskMetrics.sharpeRatio} decimalPlaces={2} className={(riskMetrics.sharpeRatio ?? 0) >= 1 ? 'text-[#00FF9D]' : (riskMetrics.sharpeRatio ?? 0) >= 0 ? 'text-amber-300' : 'text-rose-400'} /> : 'N/A'}
                    </div>
                  </div>
                  <div className="bg-[#0f172a]/50 rounded-xl border border-white/5 p-4">
                    <div className="text-slate-500 text-[10px] uppercase tracking-widest font-medium mb-1">Sortino Ratio</div>
                    <div className={`font-mono font-bold text-xl ${(riskMetrics.sortinoRatio ?? 0) >= 1 ? 'text-[#00FF9D]' : (riskMetrics.sortinoRatio ?? 0) >= 0 ? 'text-amber-300' : 'text-rose-400'}`}>
                      {riskMetrics.sortinoRatio != null ? <NumberTicker value={riskMetrics.sortinoRatio} decimalPlaces={2} className={(riskMetrics.sortinoRatio ?? 0) >= 1 ? 'text-[#00FF9D]' : (riskMetrics.sortinoRatio ?? 0) >= 0 ? 'text-amber-300' : 'text-rose-400'} /> : 'N/A'}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Interactive Chart */}
          <MagicCard gradientColor="rgba(0, 255, 157, 0.05)" className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-sm font-semibold text-white tracking-wide">1Y NAV Performance</h3>
              <div className="text-[10px] text-[#00FF9D] bg-[#00FF9D]/10 px-2 py-1 rounded border border-[#00FF9D]/20">Rebased Index</div>
            </div>
            
            <div className="h-72 w-full">
              {data.chartData && data.chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={data.chartData} margin={{ top: 10, right: 0, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#00FF9D" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#00FF9D" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                    <XAxis 
                      dataKey="date" 
                      stroke="#475569" 
                      fontSize={11} 
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(val) => {
                         const d = new Date(val.split('-').reverse().join('-'));
                         return `${d.getMonth()+1}/${d.getFullYear().toString().substr(-2)}`;
                      }}
                    />
                    <YAxis 
                      stroke="#475569" 
                      fontSize={11} 
                      domain={['dataMin', 'dataMax']} 
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1, strokeDasharray: '4 4' }} />
                    <Area 
                      type="monotone" 
                      dataKey="value" 
                      stroke="#00FF9D" 
                      strokeWidth={2} 
                      fillOpacity={1} 
                      fill="url(#colorValue)" 
                      activeDot={{ r: 6, fill: '#00FF9D', stroke: '#050505', strokeWidth: 2 }} 
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-slate-500 text-sm">No charting data available.</div>
              )}
            </div>
          </MagicCard>
          
          {/* Suggested Comparisons Section */}
          <div className="pt-6 border-t border-white/5">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-white mb-4 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#00FF9D]" />
              AI Suggested Comparisons
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {SUGGESTED_COMPARISONS.map((fund, idx) => (
                <div key={idx} onClick={() => { setIds([schemeCode, fund.code]); setView('COMPARISON'); }} className="cursor-pointer group">
                  <MagicCard gradientColor="rgba(0,255,157,0.1)" className="p-4 group-hover:border-[#00FF9D]/30 transition-colors">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-xs text-[#00FF9D] font-mono mb-1">VS</div>
                      <div className="text-sm font-semibold text-slate-200">{fund.name}</div>
                    </div>
                    <button className="bg-white/5 hover:bg-white/10 p-2 rounded-lg transition-colors">
                      <TrendingUp className="w-4 h-4 text-slate-300" />
                    </button>
                  </div>
                  </MagicCard>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
