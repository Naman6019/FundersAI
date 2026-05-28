'use client';

import { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { MFDetailApiResponse } from '@/types/funds';

export default function MFDetailView({ schemeCode }: { schemeCode?: string }) {
  const [data, setData] = useState<MFDetailApiResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!schemeCode) return;
    const fetchMF = async () => {
      setLoading(true);
      setError('');
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

  if (!schemeCode) return <div className="p-6">No fund selected.</div>;

  const navDateLabel = data?.details.nav_date ? new Date(data.details.nav_date).toLocaleDateString() : 'N/A';
  const returns = data?.returns;
  const riskMetrics = data?.riskMetrics ?? null;

  const Skeleton = () => (
    <div className="flex-1 space-y-6 overflow-hidden">
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
          <div key={i} className="bg-white/[0.03] p-4 rounded-xl border border-white/5 space-y-2">
            <div className="h-4 w-16 rounded bg-white/[0.05] animate-pulse" />
            <div className="h-7 w-24 rounded bg-white/[0.05] animate-pulse" />
          </div>
        ))}
      </div>

      <div className="space-y-3">
        <div className="h-6 w-36 rounded bg-white/[0.05] animate-pulse" />
        <div className="grid grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 rounded-lg bg-white/[0.03] border border-white/5 animate-pulse" />
          ))}
        </div>
      </div>

      <div className="space-y-3">
        <div className="h-6 w-44 rounded bg-white/[0.05] animate-pulse" />
        <div className="h-56 rounded-xl bg-white/[0.02] border border-white/5 animate-pulse" />
      </div>
    </div>
  );

  return (
    <div className="mf-detail h-full flex flex-col text-slate-100 overflow-hidden">
      {loading && <Skeleton />}
      {error && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-400">
          Error: {error}
        </div>
      )}
      
      {!loading && !error && data && (
        <div className="flex-1 overflow-y-auto pr-2 custom-scroll space-y-6 pb-6">
          <div className="mb-4 border-b border-white/10 pb-4">
            <h2 className="text-2xl font-bold tracking-tight text-white mb-2">{data.details.scheme_name}</h2>
            <div className="flex gap-2 flex-wrap text-xs">
              <span className="bg-white/5 border border-white/10 px-2.5 py-1 rounded text-slate-300">{data.details.fund_house}</span>
              <span className="bg-sky-500/10 border border-sky-500/20 text-sky-300 px-2.5 py-1 rounded">{data.details.category}</span>
              <span className="bg-purple-500/10 border border-purple-500/20 text-purple-300 px-2.5 py-1 rounded">{data.details.sub_category}</span>
            </div>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 transition-colors hover:border-sky-500/20">
              <div className="text-slate-400 text-xs mb-1">NAV ({navDateLabel})</div>
              <div className="text-lg font-bold text-sky-300">₹{data.details.nav}</div>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 transition-colors hover:border-sky-500/20">
              <div className="text-slate-400 text-xs mb-1">AUM (Cr)</div>
              <div className="text-lg font-bold text-slate-200">₹{data.details.aum || 'N/A'}</div>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 transition-colors hover:border-sky-500/20">
              <div className="text-slate-400 text-xs mb-1">Expense Ratio</div>
              <div className="text-lg font-bold text-slate-200">{data.details.expense_ratio ? `${data.details.expense_ratio}%` : 'N/A'}</div>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 transition-colors hover:border-sky-500/20">
              <div className="text-slate-400 text-xs mb-1">Exit Load</div>
              <div className="text-sm font-semibold text-slate-200 truncate" title={data.details.exit_load || 'N/A'}>
                {data.details.exit_load || 'N/A'}
              </div>
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-[#0f172a]/60 p-5 shadow-lg backdrop-blur-md">
            <h3 className="text-sm font-semibold text-white tracking-wide mb-4">Historical Returns (CAGR)</h3>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                <div className="text-slate-400 text-xs mb-1">1 Year</div>
                <div className={`font-bold text-base ${(returns?.['1Y'] ?? 0) > 0 ? 'text-emerald-300' : 'text-rose-300'}`}>
                  {returns?.['1Y'] !== null && returns?.['1Y'] !== undefined ? `${returns['1Y']}%` : 'N/A'}
                </div>
              </div>
              <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                <div className="text-slate-400 text-xs mb-1">3 Years</div>
                <div className={`font-bold text-base ${(returns?.['3Y'] ?? 0) > 0 ? 'text-emerald-300' : 'text-rose-300'}`}>
                  {returns?.['3Y'] !== null && returns?.['3Y'] !== undefined ? `${returns['3Y']}%` : 'N/A'}
                </div>
              </div>
              <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                <div className="text-slate-400 text-xs mb-1">5 Years</div>
                <div className={`font-bold text-base ${(returns?.['5Y'] ?? 0) > 0 ? 'text-emerald-300' : 'text-rose-300'}`}>
                  {returns?.['5Y'] !== null && returns?.['5Y'] !== undefined ? `${returns['5Y']}%` : 'N/A'}
                </div>
              </div>
            </div>
          </div>

          {riskMetrics && (
            <div className="rounded-2xl border border-white/10 bg-[#0f172a]/60 p-5 shadow-lg backdrop-blur-md">
              <h3 className="text-sm font-semibold text-white tracking-wide mb-4 flex items-center justify-between">
                <span>Risk Metrics</span>
                <span className="text-[10px] text-slate-400 font-normal uppercase tracking-wider">Based on full NAV history (RFR 6%)</span>
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
                <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                  <div className="text-slate-400 text-xs mb-1">Sharpe Ratio</div>
                  <div className={`font-bold text-base ${(riskMetrics.sharpeRatio ?? 0) >= 1 ? 'text-emerald-300' : (riskMetrics.sharpeRatio ?? 0) >= 0 ? 'text-amber-300' : 'text-rose-300'}`}>
                    {riskMetrics.sharpeRatio ?? 'N/A'}
                  </div>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                  <div className="text-slate-400 text-xs mb-1">Sortino Ratio</div>
                  <div className={`font-bold text-base ${(riskMetrics.sortinoRatio ?? 0) >= 1 ? 'text-emerald-300' : (riskMetrics.sortinoRatio ?? 0) >= 0 ? 'text-amber-300' : 'text-rose-300'}`}>
                    {riskMetrics.sortinoRatio ?? 'N/A'}
                  </div>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                  <div className="text-slate-400 text-xs mb-1">Std Dev (Ann.)</div>
                  <div className="font-semibold text-base text-slate-200">
                    {typeof riskMetrics.stdDev === 'number' ? `${(riskMetrics.stdDev * 100).toFixed(1)}%` : 'N/A'}
                  </div>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
                  <div className="text-slate-400 text-xs mb-1">Max Drawdown</div>
                  <div className="font-semibold text-base text-rose-300">
                    {typeof riskMetrics.maxDrawdown === 'number' ? `-${(riskMetrics.maxDrawdown * 100).toFixed(1)}%` : 'N/A'}
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="rounded-2xl border border-white/10 bg-[#0f172a]/60 p-5 shadow-lg backdrop-blur-md">
            <h3 className="text-sm font-semibold text-white tracking-wide mb-4">1Y NAV Trend (Rebased)</h3>
            <div className="h-64 w-full bg-black/20 rounded-xl p-2 border border-white/5">
              {data.chartData && data.chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={data.chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis 
                      dataKey="date" 
                      stroke="#8a9199" 
                      fontSize={11} 
                      tickFormatter={(val) => {
                         const d = new Date(val.split('-').reverse().join('-')); // approx parsing
                         return `${d.getMonth()+1}/${d.getFullYear().toString().substr(-2)}`;
                      }} 
                    />
                    <YAxis stroke="#8a9199" fontSize={11} domain={['dataMin', 'dataMax']} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: 'rgba(11, 12, 16, 0.95)', borderColor: 'rgba(56, 189, 248, 0.2)', borderRadius: '12px' }} 
                      itemStyle={{ color: '#38bdf8' }}
                    />
                    <Line type="monotone" dataKey="value" stroke="#38bdf8" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-slate-500 text-sm">No recent history available for charting.</div>
              )}
            </div>
          </div>
          
          <div className="text-xs text-slate-400 border-t border-white/10 pt-4 flex flex-col gap-1">
            <div>Benchmark: {data.details.benchmark || 'N/A'}</div>
            <div>Data synced from AMFI API. Note: Due to limitations, returns may be indicative.</div>
          </div>
        </div>
      )}
    </div>
  );
}
