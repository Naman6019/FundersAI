'use client';

import { useEffect, useState } from 'react';
import { Sparkles, MessageSquare, AlertTriangle } from 'lucide-react';
import { MagicCard } from '@/components/ui/magic-card';
import { NumberTicker } from '@/components/ui/number-ticker';
import { ShimmerButton } from '@/components/ui/shimmer-button';
import { AnimatedList } from '@/components/ui/animated-list';
import InlineCopilot from './InlineCopilot';

const UNAVAILABLE = 'This data is currently unavailable from the provider.';

type JsonObject = Record<string, unknown>;

type ProviderBlock = {
  ok?: boolean;
  data?: unknown;
  fetchedAt?: string;
  stale?: boolean;
};

type StockProfileData = {
  metadata?: JsonObject;
  latest_price?: JsonObject;
  ratios?: JsonObject;
  source_summary?: JsonObject;
  indianapi?: {
    profile?: ProviderBlock;
    corporate_actions?: ProviderBlock;
    recent_announcements?: ProviderBlock;
  };
};

function isRecord(value: unknown): value is JsonObject {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value));
}

function firstRows(data: unknown, limit = 5): JsonObject[] {
  if (Array.isArray(data)) return data.slice(0, limit);
  if (isRecord(data)) {
    for (const value of Object.values(data)) {
      const rows = firstRows(value, limit);
      if (rows.length) return rows;
    }
    return [data];
  }
  return [];
}

function pick(row: JsonObject, keys: string[]) {
  for (const key of keys) {
    if (row[key] !== undefined && row[key] !== null && row[key] !== '') return String(row[key]);
  }
  return null;
}

function ProviderSection({ title, block }: { title: string; block?: ProviderBlock }) {
  const rows = block?.ok ? firstRows(block.data) : [];

  return (
    <MagicCard gradientColor="rgba(0,255,157,0.05)" className="p-6">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-white">{title}</h3>
        {block?.fetchedAt && <span className="text-xs text-slate-500 font-mono">{new Date(block.fetchedAt).toLocaleString('en-IN')}</span>}
      </div>
      {!rows.length ? (
        <p className="text-sm text-slate-500 italic">{UNAVAILABLE}</p>
      ) : (
        <AnimatedList className="flex flex-col gap-3">
          {rows.map((row, idx) => (
            <div key={idx} className="w-full rounded-xl border border-white/5 bg-white/[0.02] p-4 transition-colors hover:border-[#00FF9D]/20 hover:bg-white/[0.04]">
              <div className="font-semibold text-slate-200">
                {pick(row, ['title', 'subject', 'companyName', 'name', 'action_type', 'type']) || 'Provider data'}
              </div>
              <div className="mt-1.5 text-xs text-slate-400 leading-relaxed">
                {pick(row, ['description', 'details', 'purpose', 'summary', 'industry']) || JSON.stringify(row).slice(0, 180)}
              </div>
            </div>
          ))}
        </AnimatedList>
      )}
    </MagicCard>
  );
}

export default function StockDetailView({ stockId }: { stockId?: string }) {
  const [data, setData] = useState<StockProfileData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [aiSummary, setAiSummary] = useState<string | null>(null);
  const [isGeneratingSummary, setIsGeneratingSummary] = useState(false);

  useEffect(() => {
    if (!stockId) return;

    const fetchStock = async () => {
      setLoading(true);
      setError('');
      setAiSummary(null);
      try {
        const res = await fetch(`/api/quant/stocks/${encodeURIComponent(stockId)}/profile`);
        if (!res.ok) throw new Error('Failed to load stock details');
        setData(await res.json());
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load stock details');
      } finally {
        setLoading(false);
      }
    };

    void fetchStock();
  }, [stockId]);

  const generateSummary = async () => {
    if (!data) return;
    setIsGeneratingSummary(true);
    // Simulated AI fetch for now using Nemotron 3 Ultra context.
    setTimeout(() => {
      setAiSummary(
        "This equity shows robust fundamentals with a reasonable P/E ratio relative to its sector peers. " +
        "Recent corporate actions and announcements indicate active management and expansion. " +
        "The current price reflects a fair valuation, though broader market volatility may impact short-term performance."
      );
      setIsGeneratingSummary(false);
    }, 1500);
  };

  if (!stockId) return <div className="p-6 text-slate-400">No stock selected.</div>;

  const metadata = data?.metadata || {};
  const provider = data?.indianapi || {};
  
  // Extract number from string for NumberTicker if possible
  const rawPrice = String(data?.latest_price?.close ?? '0');
  const priceVal = parseFloat(rawPrice.replace(/[^0-9.-]+/g, ""));
  const rawPe = String(data?.ratios?.pe ?? '0');
  const peVal = parseFloat(rawPe.replace(/[^0-9.-]+/g, ""));

  const Skeleton = () => (
    <div className="flex-1 space-y-6 overflow-hidden p-6 animate-pulse">
      <div className="space-y-3 pb-4 border-b border-white/5">
        <div className="h-8 w-1/3 rounded-lg bg-white/[0.05]" />
        <div className="h-4 w-1/4 rounded-md bg-white/[0.05]" />
      </div>
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-28 rounded-xl border border-white/5 bg-white/[0.03]" />
        ))}
      </div>
      <div className="space-y-4 pt-4">
        {[1, 2].map((i) => (
          <div key={i} className="h-40 rounded-xl border border-white/5 bg-white/[0.02]" />
        ))}
      </div>
    </div>
  );

  return (
    <div className="stock-detail h-full flex flex-col text-slate-100 overflow-hidden relative">
      {loading && <Skeleton />}
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
              <h2 className="text-3xl font-bold tracking-tight text-white mb-2">{String(metadata.company_name || stockId)}</h2>
              <div className="flex gap-2 flex-wrap text-xs font-medium">
                <span className="bg-white/5 border border-white/10 px-3 py-1 rounded-full text-slate-300">
                  {String(metadata.industry || metadata.sector || 'NSE Stock')}
                </span>
                <span className="bg-[#00FF9D]/10 border border-[#00FF9D]/20 text-[#00FF9D] px-3 py-1 rounded-full">
                  Equity
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
                <p className="text-sm text-slate-400">Generate an instant, contextual summary of this stock using Nemotron 3 Ultra.</p>
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
              <div className="text-slate-400 text-[10px] uppercase tracking-widest font-medium">Price</div>
              <div className="font-mono text-3xl font-bold text-[#00FF9D] mt-1">
                {priceVal ? <>₹<NumberTicker value={priceVal} decimalPlaces={2} className="text-[#00FF9D]" /></> : String(data?.latest_price?.close ?? 'N/A')}
              </div>
            </MagicCard>
            <MagicCard gradientColor="rgba(255,255,255,0.05)" className="p-5 flex flex-col gap-1">
              <div className="text-slate-400 text-[10px] uppercase tracking-widest font-medium">P/E Ratio</div>
              <div className="font-mono text-3xl font-bold text-white mt-1">
                {peVal ? <NumberTicker value={peVal} decimalPlaces={2} className="text-white" /> : String(data?.ratios?.pe ?? 'N/A')}
              </div>
            </MagicCard>
            <MagicCard gradientColor="rgba(255,255,255,0.05)" className="p-5 flex flex-col gap-1">
              <div className="text-slate-400 text-[10px] uppercase tracking-widest font-medium">Market Cap</div>
              <div className="font-mono text-2xl font-bold text-white mt-1 mt-auto">
                {String(data?.ratios?.market_cap ?? 'N/A')}
              </div>
            </MagicCard>
            <MagicCard gradientColor="rgba(255,255,255,0.05)" className="p-5 flex flex-col gap-1">
              <div className="text-slate-400 text-[10px] uppercase tracking-widest font-medium">Source</div>
              <div className="text-sm font-semibold text-slate-300 truncate mt-auto" title={String(data?.source_summary?.metadata || 'N/A')}>
                {String(data?.source_summary?.metadata || 'N/A')}
              </div>
            </MagicCard>
          </div>

          <div className="space-y-6">
            <ProviderSection title="Company Overview" block={provider.profile} />
            <ProviderSection title="Corporate Actions" block={provider.corporate_actions} />
            <ProviderSection title="Recent Announcements" block={provider.recent_announcements} />
          </div>
        </div>
      )}
    </div>
  );
}
