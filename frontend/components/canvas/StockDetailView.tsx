'use client';

import { useEffect, useState } from 'react';

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
    <section className="rounded-2xl border border-white/10 bg-[#0f172a]/60 p-5 shadow-lg backdrop-blur-md">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-white">{title}</h3>
        {block?.fetchedAt && <span className="text-xs text-slate-400 font-mono">{new Date(block.fetchedAt).toLocaleString('en-IN')}</span>}
      </div>
      {!rows.length ? (
        <p className="text-sm text-slate-400 italic">{UNAVAILABLE}</p>
      ) : (
        <div className="space-y-3">
          {rows.map((row, idx) => (
            <div key={idx} className="rounded-xl border border-white/10 bg-white/[0.03] p-4 transition-colors hover:border-[#66a3ff]/20">
              <div className="font-semibold text-slate-200">
                {pick(row, ['title', 'subject', 'companyName', 'name', 'action_type', 'type']) || 'Provider data'}
              </div>
              <div className="mt-1.5 text-xs text-slate-400 leading-relaxed">
                {pick(row, ['description', 'details', 'purpose', 'summary', 'industry']) || JSON.stringify(row).slice(0, 180)}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default function StockDetailView({ stockId }: { stockId?: string }) {
  const [data, setData] = useState<StockProfileData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!stockId) return;

    const fetchStock = async () => {
      setLoading(true);
      setError('');
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

  if (!stockId) return <div className="p-4 text-slate-400">No stock selected.</div>;

  const metadata = data?.metadata || {};
  const provider = data?.indianapi || {};

  const Skeleton = () => (
    <div className="space-y-6 animate-pulse">
      <div className="space-y-2 pb-4 border-b border-white/5">
        <div className="h-8 w-2/3 rounded-lg bg-white/[0.05]" />
        <div className="h-4 w-1/3 rounded-md bg-white/[0.05]" />
      </div>

      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-16 rounded-xl border border-white/10 bg-white/[0.03]" />
        ))}
      </div>

      <div className="space-y-4 pt-4 border-t border-white/5">
        <div className="h-6 w-32 rounded bg-white/[0.05]" />
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="h-20 rounded-xl border border-white/10 bg-white/[0.02]" />
          ))}
        </div>
      </div>
    </div>
  );

  return (
    <div className="stock-detail h-full flex flex-col text-slate-100 overflow-hidden">
      {loading && <Skeleton />}
      {error && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-400">
          {UNAVAILABLE}
        </div>
      )}

      {!loading && !error && (
        <div className="flex-1 overflow-y-auto pr-2 custom-scroll space-y-6 pb-6">
          <div className="mb-4 border-b border-white/10 pb-4">
            <h2 className="text-2xl font-bold tracking-tight text-white mb-1">{String(metadata.company_name || stockId)}</h2>
            <p className="text-xs text-slate-400">{String(metadata.industry || metadata.sector || 'NSE stock research')}</p>
          </div>
          
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 transition-colors hover:border-[#66a3ff]/20 flex flex-col gap-1">
              <div className="text-slate-400 text-[10px] uppercase tracking-wider font-medium">Price</div>
              <div className="font-serif-display text-2xl font-bold text-[#66a3ff]">{String(data?.latest_price?.close ?? 'N/A')}</div>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 transition-colors hover:border-[#66a3ff]/20 flex flex-col gap-1">
              <div className="text-slate-400 text-[10px] uppercase tracking-wider font-medium">P/E Ratio</div>
              <div className="font-serif-display text-2xl font-bold text-slate-200">{String(data?.ratios?.pe ?? 'N/A')}</div>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 transition-colors hover:border-[#66a3ff]/20 flex flex-col gap-1">
              <div className="text-slate-400 text-[10px] uppercase tracking-wider font-medium">Market Cap</div>
              <div className="font-serif-display text-2xl font-bold text-slate-200">{String(data?.ratios?.market_cap ?? 'N/A')}</div>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 transition-colors hover:border-[#66a3ff]/20 flex flex-col gap-1">
              <div className="text-slate-400 text-[10px] uppercase tracking-wider font-medium">Source</div>
              <div className="text-sm font-semibold text-slate-300 truncate mt-auto" title={String(data?.source_summary?.metadata || 'N/A')}>
                {String(data?.source_summary?.metadata || 'N/A')}
              </div>
            </div>
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
