'use client';

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import { FUND_REGISTRY, FundEntry, getComparePair } from '@/lib/fund-registry';
import {
  getHoldingsForScheme,
  calculateDetailedOverlap,
  DetailedOverlapResult,
} from '@/lib/fund-holdings';
import { Search, ArrowRight, Layers, PieChart, ShieldCheck, AlertTriangle, Sparkles, CheckCircle2, ChevronRight, Share2, Check } from 'lucide-react';

interface PopularPair {
  label: string;
  schemeCodeA: number;
  schemeCodeB: number;
  tag: string;
}

const POPULAR_PAIRS: PopularPair[] = [
  {
    label: 'PPFAS Flexi Cap vs HDFC Flexi Cap',
    schemeCodeA: 122639,
    schemeCodeB: 120503,
    tag: 'Flexi Cap Battle',
  },
  {
    label: 'Quant Small Cap vs Nippon Small Cap',
    schemeCodeA: 120828,
    schemeCodeB: 118778,
    tag: 'Small Cap Heavyweights',
  },
  {
    label: 'SBI Bluechip vs ICICI Pru Bluechip',
    schemeCodeA: 119598,
    schemeCodeB: 120586,
    tag: 'Large Cap Anchors',
  },
  {
    label: 'Tata Digital vs ICICI Tech',
    schemeCodeA: 135781,
    schemeCodeB: 120594,
    tag: 'Sectoral Tech Duel',
  },
  {
    label: 'Mirae Large & Midcap vs Kotak Flexicap',
    schemeCodeA: 120038,
    schemeCodeB: 120166,
    tag: 'Core Equity Blend',
  },
];

export default function PortfolioOverlapCalculator() {
  const [codeA, setCodeA] = useState<number>(122639); // PPFAS Flexi Cap
  const [codeB, setCodeB] = useState<number>(120503); // HDFC Flexi Cap
  const [searchA, setSearchA] = useState<string>('');
  const [searchB, setSearchB] = useState<string>('');
  const [openSelectorA, setOpenSelectorA] = useState<boolean>(false);
  const [openSelectorB, setOpenSelectorB] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<'overlapping' | 'uniqueA' | 'uniqueB' | 'sectors'>('overlapping');
  const [copied, setCopied] = useState<boolean>(false);

  const handleShare = () => {
    if (typeof window !== 'undefined') {
      const shareUrl = `${window.location.origin}/tools/portfolio-overlap?fundA=${codeA}&fundB=${codeB}`;
      navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    }
  };

  const fundA = useMemo(
    () => FUND_REGISTRY.find((f) => f.schemeCode === codeA) || FUND_REGISTRY[0],
    [codeA]
  );
  const fundB = useMemo(
    () => FUND_REGISTRY.find((f) => f.schemeCode === codeB) || FUND_REGISTRY[1],
    [codeB]
  );

  const comparePair = getComparePair(fundA.fundSlug, fundB.fundSlug);

  const filteredFundsA = useMemo(() => {
    if (!searchA.trim()) return FUND_REGISTRY;
    const q = searchA.toLowerCase();
    return FUND_REGISTRY.filter(
      (f) =>
        f.schemeName.toLowerCase().includes(q) ||
        f.amcName.toLowerCase().includes(q) ||
        f.category.toLowerCase().includes(q)
    );
  }, [searchA]);

  const filteredFundsB = useMemo(() => {
    if (!searchB.trim()) return FUND_REGISTRY;
    const q = searchB.toLowerCase();
    return FUND_REGISTRY.filter(
      (f) =>
        f.schemeName.toLowerCase().includes(q) ||
        f.amcName.toLowerCase().includes(q) ||
        f.category.toLowerCase().includes(q)
    );
  }, [searchB]);

  const overlapResult: DetailedOverlapResult = useMemo(() => {
    const holdingsA = getHoldingsForScheme(fundA.schemeCode, fundA.category);
    const holdingsB = getHoldingsForScheme(fundB.schemeCode, fundB.category);
    return calculateDetailedOverlap(holdingsA, holdingsB);
  }, [fundA, fundB]);

  const handleSelectPair = (pair: PopularPair) => {
    setCodeA(pair.schemeCodeA);
    setCodeB(pair.schemeCodeB);
  };

  return (
    <div className="space-y-10">
      {/* ─── Popular Comparison Presets ───────────────────────────────────────── */}
      <section className="space-y-3">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[#7183a0]">
          <Sparkles className="w-3.5 h-3.5 text-[#00FF9D]" />
          <span>Trending Portfolio Overlap Duels</span>
        </div>
        <div className="flex flex-wrap gap-2">
          {POPULAR_PAIRS.map((pair) => {
            const isSelected = codeA === pair.schemeCodeA && codeB === pair.schemeCodeB;
            return (
              <button
                key={pair.label}
                onClick={() => handleSelectPair(pair)}
                className={`group flex items-center gap-2 rounded-xl border px-3.5 py-2 text-xs font-medium transition-all ${
                  isSelected
                    ? 'border-[#00FF9D]/60 bg-[#00FF9D]/10 text-white shadow-lg shadow-[#00FF9D]/10'
                    : 'border-white/10 bg-white/[0.02] text-[#aebed6] hover:border-white/20 hover:bg-white/[0.05] hover:text-white'
                }`}
              >
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-white/10 text-[#7183a0] group-hover:text-[#00FF9D]">
                  {pair.tag}
                </span>
                <span>{pair.label}</span>
              </button>
            );
          })}
        </div>
      </section>

      {/* ─── Scheme Selectors (Dual Glassmorphism Pickers) ────────────────────── */}
      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6 relative">
        {/* Fund A Picker */}
        <div className="relative rounded-2xl border border-white/10 bg-gradient-to-b from-[#0b1220] to-[#070b14] p-6 shadow-2xl space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-[#00FF9D]">
              Scheme A (Base Fund)
            </span>
            <span className="text-xs text-[#7183a0] font-mono">{fundA.category}</span>
          </div>

          <div className="relative">
            <button
              onClick={() => setOpenSelectorA(!openSelectorA)}
              className="w-full text-left rounded-xl border border-white/15 bg-white/[0.03] hover:bg-white/[0.06] px-4 py-3 text-sm font-semibold text-white flex items-center justify-between transition-colors"
            >
              <div className="truncate pr-2">
                <p className="truncate text-white font-bold">{fundA.schemeName}</p>
                <p className="text-xs text-[#7183a0] font-normal">{fundA.amcName} • AMFI: {fundA.schemeCode}</p>
              </div>
              <ChevronRight className={`w-4 h-4 text-[#7183a0] transition-transform ${openSelectorA ? 'rotate-90' : ''}`} />
            </button>

            {openSelectorA && (
              <div className="absolute z-30 left-0 right-0 mt-2 rounded-xl border border-white/15 bg-[#0b1220] shadow-2xl p-3 space-y-2 max-h-72 overflow-y-auto">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#7183a0]" />
                  <input
                    type="text"
                    placeholder="Search scheme name, AMC, category..."
                    value={searchA}
                    onChange={(e) => setSearchA(e.target.value)}
                    className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-white/10 bg-black/40 text-white placeholder-[#7183a0] focus:outline-none focus:border-[#00FF9D]"
                    autoFocus
                  />
                </div>
                <div className="space-y-1">
                  {filteredFundsA.map((f) => (
                    <button
                      key={f.schemeCode}
                      onClick={() => {
                        setCodeA(f.schemeCode);
                        setOpenSelectorA(false);
                      }}
                      className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors flex items-center justify-between ${
                        f.schemeCode === fundA.schemeCode
                          ? 'bg-[#00FF9D]/15 text-[#00FF9D] font-bold'
                          : 'text-[#aebed6] hover:bg-white/5 hover:text-white'
                      }`}
                    >
                      <span className="truncate pr-2">{f.schemeName}</span>
                      <span className="text-[10px] text-[#7183a0] shrink-0">{f.category}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Fund B Picker */}
        <div className="relative rounded-2xl border border-white/10 bg-gradient-to-b from-[#0b1220] to-[#070b14] p-6 shadow-2xl space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-[#66a3ff]">
              Scheme B (Comparison Fund)
            </span>
            <span className="text-xs text-[#7183a0] font-mono">{fundB.category}</span>
          </div>

          <div className="relative">
            <button
              onClick={() => setOpenSelectorB(!openSelectorB)}
              className="w-full text-left rounded-xl border border-white/15 bg-white/[0.03] hover:bg-white/[0.06] px-4 py-3 text-sm font-semibold text-white flex items-center justify-between transition-colors"
            >
              <div className="truncate pr-2">
                <p className="truncate text-white font-bold">{fundB.schemeName}</p>
                <p className="text-xs text-[#7183a0] font-normal">{fundB.amcName} • AMFI: {fundB.schemeCode}</p>
              </div>
              <ChevronRight className={`w-4 h-4 text-[#7183a0] transition-transform ${openSelectorB ? 'rotate-90' : ''}`} />
            </button>

            {openSelectorB && (
              <div className="absolute z-30 left-0 right-0 mt-2 rounded-xl border border-white/15 bg-[#0b1220] shadow-2xl p-3 space-y-2 max-h-72 overflow-y-auto">
                <div className="relative">
                  <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-[#7183a0]" />
                  <input
                    type="text"
                    placeholder="Search scheme name, AMC, category..."
                    value={searchB}
                    onChange={(e) => setSearchB(e.target.value)}
                    className="w-full pl-9 pr-3 py-1.5 text-xs rounded-lg border border-white/10 bg-black/40 text-white placeholder-[#7183a0] focus:outline-none focus:border-[#66a3ff]"
                    autoFocus
                  />
                </div>
                <div className="space-y-1">
                  {filteredFundsB.map((f) => (
                    <button
                      key={f.schemeCode}
                      onClick={() => {
                        setCodeB(f.schemeCode);
                        setOpenSelectorB(false);
                      }}
                      className={`w-full text-left px-3 py-2 rounded-lg text-xs transition-colors flex items-center justify-between ${
                        f.schemeCode === fundB.schemeCode
                          ? 'bg-[#66a3ff]/15 text-[#66a3ff] font-bold'
                          : 'text-[#aebed6] hover:bg-white/5 hover:text-white'
                      }`}
                    >
                      <span className="truncate pr-2">{f.schemeName}</span>
                      <span className="text-[10px] text-[#7183a0] shrink-0">{f.category}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* ─── Overlap Master Scorecard & Diversification Verdict ───────────────── */}
      <section className="rounded-3xl border border-white/10 bg-gradient-to-br from-[#0c1527] via-[#080e1a] to-[#050811] p-6 sm:p-10 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-[#00FF9D]/5 rounded-full blur-3xl pointer-events-none" />

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
          {/* Overlap Percentage Dial */}
          <div className="lg:col-span-4 text-center lg:text-left space-y-4">
            <span className="text-xs font-mono font-bold uppercase tracking-[0.2em] text-[#7183a0]">
              Total Portfolio Overlap
            </span>
            <div className="flex items-baseline justify-center lg:justify-start gap-3">
              <span
                className="text-6xl sm:text-7xl font-extrabold tracking-tight"
                style={{ color: overlapResult.verdict.color }}
              >
                {overlapResult.percentage}%
              </span>
              <span className="text-sm font-semibold text-[#7183a0]">shared weight</span>
            </div>

            {/* Visual Overlap Bar */}
            <div className="w-full bg-white/10 h-3 rounded-full overflow-hidden flex">
              <div
                className="h-full transition-all duration-700 rounded-full"
                style={{
                  width: `${Math.min(100, Math.max(0, overlapResult.percentage))}%`,
                  backgroundColor: overlapResult.verdict.color,
                }}
              />
            </div>
            <div className="flex justify-between text-[11px] font-mono text-[#7183a0]">
              <span>0% (Disjoint)</span>
              <span>40% (Redundant)</span>
              <span>100% (Identical)</span>
            </div>
          </div>

          {/* Verdict Box */}
          <div className="lg:col-span-8 space-y-4 rounded-2xl border border-white/10 bg-white/[0.02] p-6 backdrop-blur-md">
            <div className="flex items-center gap-3">
              {overlapResult.verdict.level === 'Low' ? (
                <div className="p-2 rounded-xl bg-[#00FF9D]/10 text-[#00FF9D]">
                  <ShieldCheck className="w-6 h-6" />
                </div>
              ) : overlapResult.verdict.level === 'Moderate' ? (
                <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
              ) : (
                <div className="p-2 rounded-xl bg-rose-500/10 text-rose-400">
                  <AlertTriangle className="w-6 h-6" />
                </div>
              )}
              <div>
                <h2 className="text-base sm:text-lg font-bold text-white">
                  {overlapResult.verdict.title}
                </h2>
                <p className="text-xs text-[#7183a0] font-mono">
                  {overlapResult.overlappingCount} common stocks identified across {overlapResult.totalUniqueCount} total distinct holdings
                </p>
              </div>
            </div>
            <p className="text-xs sm:text-sm text-[#aebed6] leading-relaxed">
              {overlapResult.verdict.description}
            </p>

            <div className="pt-2 flex flex-wrap items-center justify-between gap-4 border-t border-white/5 text-xs text-[#7183a0]">
              <div className="flex flex-wrap items-center gap-4">
                <span>
                  <strong className="text-white">{overlapResult.uniqueA.length}</strong> unique to {fundA.schemeName.split(' ')[0]}
                </span>
                <span>•</span>
                <span>
                  <strong className="text-white">{overlapResult.overlappingCount}</strong> common overlap
                </span>
                <span>•</span>
                <span>
                  <strong className="text-white">{overlapResult.uniqueB.length}</strong> unique to {fundB.schemeName.split(' ')[0]}
                </span>
              </div>

              {/* 1-Click Share & Copy Link */}
              <button
                onClick={handleShare}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/15 bg-white/5 hover:bg-white/10 text-white font-medium transition-colors text-xs"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 text-[#00FF9D]" />
                    <span className="text-[#00FF9D] font-bold">Link Copied!</span>
                  </>
                ) : (
                  <>
                    <Share2 className="w-3.5 h-3.5 text-[#7183a0]" />
                    <span>Share Duel</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* ─── Visual Venn Diagram Diagram Section ─── */}
        <div className="mt-8 pt-6 border-t border-white/10 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="space-y-1 text-center md:text-left">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-[#7183a0]">Portfolio Overlap Venn Diagram</span>
            <p className="text-xs text-[#aebed6]">Visual representation of distinct vs duplicated equity allocation</p>
          </div>

          <div className="relative w-full max-w-sm flex items-center justify-center">
            <svg viewBox="0 0 320 150" className="w-full h-auto max-h-36 drop-shadow-lg">
              {/* Left Circle - Fund A */}
              <circle
                cx="120"
                cy="75"
                r="55"
                fill="rgba(0, 255, 157, 0.12)"
                stroke="#00FF9D"
                strokeWidth="1.5"
                strokeDasharray="4 2"
              />
              {/* Right Circle - Fund B */}
              <circle
                cx="200"
                cy="75"
                r="55"
                fill="rgba(102, 163, 255, 0.12)"
                stroke="#66a3ff"
                strokeWidth="1.5"
                strokeDasharray="4 2"
              />

              {/* Fund A Label */}
              <text x="85" y="70" textAnchor="middle" fill="#00FF9D" fontSize="12" fontWeight="bold">
                {fundA.schemeName.split(' ')[0]}
              </text>
              <text x="85" y="85" textAnchor="middle" fill="#7183a0" fontSize="9" fontFamily="monospace">
                {(100 - overlapResult.percentage).toFixed(0)}% Unique
              </text>

              {/* Overlap Intersection Label */}
              <text x="160" y="68" textAnchor="middle" fill={overlapResult.verdict.color} fontSize="14" fontWeight="900">
                {overlapResult.percentage}%
              </text>
              <text x="160" y="83" textAnchor="middle" fill="#ffffff" fontSize="8" fontWeight="bold" letterSpacing="0.05em">
                SHARED
              </text>

              {/* Fund B Label */}
              <text x="235" y="70" textAnchor="middle" fill="#66a3ff" fontSize="12" fontWeight="bold">
                {fundB.schemeName.split(' ')[0]}
              </text>
              <text x="235" y="85" textAnchor="middle" fill="#7183a0" fontSize="9" fontFamily="monospace">
                {(100 - overlapResult.percentage).toFixed(0)}% Unique
              </text>
            </svg>
          </div>
        </div>
      </section>

      {/* ─── Tab Navigation for Holdings Breakdown ───────────────────────────── */}
      <section className="space-y-6">
        <div className="flex items-center justify-between border-b border-white/10 pb-4">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setActiveTab('overlapping')}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                activeTab === 'overlapping'
                  ? 'bg-white/10 text-white border border-white/20'
                  : 'text-[#7183a0] hover:text-white'
              }`}
            >
              Overlapping Stocks ({overlapResult.overlappingCount})
            </button>
            <button
              onClick={() => setActiveTab('uniqueA')}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                activeTab === 'uniqueA'
                  ? 'bg-[#00FF9D]/15 text-[#00FF9D] border border-[#00FF9D]/30'
                  : 'text-[#7183a0] hover:text-white'
              }`}
            >
              Unique to {fundA.schemeName.split(' ')[0]} ({overlapResult.uniqueA.length})
            </button>
            <button
              onClick={() => setActiveTab('uniqueB')}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                activeTab === 'uniqueB'
                  ? 'bg-[#66a3ff]/15 text-[#66a3ff] border border-[#66a3ff]/30'
                  : 'text-[#7183a0] hover:text-white'
              }`}
            >
              Unique to {fundB.schemeName.split(' ')[0]} ({overlapResult.uniqueB.length})
            </button>
            <button
              onClick={() => setActiveTab('sectors')}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                activeTab === 'sectors'
                  ? 'bg-purple-500/15 text-purple-300 border border-purple-500/30'
                  : 'text-[#7183a0] hover:text-white'
              }`}
            >
              Sector Overlap
            </button>
          </div>

          {comparePair && (
            <Link
              href={`/compare/${comparePair.pair}`}
              className="hidden sm:inline-flex items-center gap-1.5 text-xs font-semibold text-[#00FF9D] hover:underline"
            >
              <span>Full Head-to-Head Comparison</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          )}
        </div>

        {/* Tab 1: Overlapping Stocks */}
        {activeTab === 'overlapping' && (
          <div className="rounded-2xl border border-white/10 bg-[#080e1a] overflow-hidden">
            {overlapResult.overlapping.length === 0 ? (
              <div className="p-12 text-center text-[#7183a0] space-y-2">
                <ShieldCheck className="w-8 h-8 mx-auto text-[#00FF9D]" />
                <p className="text-sm font-semibold text-white">Zero Overlapping Holdings Found</p>
                <p className="text-xs">These two schemes do not share any common underlying stock positions.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-white/10 bg-white/[0.02] text-[#7183a0] uppercase font-mono text-[10px]">
                    <tr>
                      <th className="py-3 px-4">Stock Name</th>
                      <th className="py-3 px-4">Sector</th>
                      <th className="py-3 px-4 text-right">{fundA.schemeName.split(' ')[0]} Weight</th>
                      <th className="py-3 px-4 text-right">{fundB.schemeName.split(' ')[0]} Weight</th>
                      <th className="py-3 px-4 text-right font-bold text-[#00FF9D]">Overlap Weight</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {overlapResult.overlapping.map((stock) => (
                      <tr key={stock.isin} className="hover:bg-white/[0.02] transition-colors">
                        <td className="py-3.5 px-4">
                          <p className="font-semibold text-white">{stock.name}</p>
                          <p className="text-[10px] font-mono text-[#7183a0]">{stock.isin}</p>
                        </td>
                        <td className="py-3.5 px-4 text-[#aebed6]">
                          <span className="px-2 py-0.5 rounded bg-white/5 border border-white/5 text-[10px]">
                            {stock.sector}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-right font-mono text-[#00FF9D]">
                          {stock.weightA.toFixed(2)}%
                        </td>
                        <td className="py-3.5 px-4 text-right font-mono text-[#66a3ff]">
                          {stock.weightB.toFixed(2)}%
                        </td>
                        <td className="py-3.5 px-4 text-right font-mono font-bold text-white bg-white/[0.015]">
                          {stock.overlap.toFixed(2)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Unique to Fund A */}
        {activeTab === 'uniqueA' && (
          <div className="rounded-2xl border border-white/10 bg-[#080e1a] p-6">
            <h3 className="text-sm font-bold text-white mb-4">
              Holdings held exclusively by {fundA.schemeName}
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {overlapResult.uniqueA.map((stock) => (
                <div key={stock.isin} className="rounded-xl border border-white/5 bg-white/[0.02] p-3 space-y-1">
                  <div className="flex justify-between items-start">
                    <p className="text-xs font-semibold text-white truncate pr-2">{stock.name}</p>
                    <span className="text-xs font-mono font-bold text-[#00FF9D]">{stock.weight.toFixed(2)}%</span>
                  </div>
                  <p className="text-[10px] text-[#7183a0]">{stock.sector}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 3: Unique to Fund B */}
        {activeTab === 'uniqueB' && (
          <div className="rounded-2xl border border-white/10 bg-[#080e1a] p-6">
            <h3 className="text-sm font-bold text-white mb-4">
              Holdings held exclusively by {fundB.schemeName}
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {overlapResult.uniqueB.map((stock) => (
                <div key={stock.isin} className="rounded-xl border border-white/5 bg-white/[0.02] p-3 space-y-1">
                  <div className="flex justify-between items-start">
                    <p className="text-xs font-semibold text-white truncate pr-2">{stock.name}</p>
                    <span className="text-xs font-mono font-bold text-[#66a3ff]">{stock.weight.toFixed(2)}%</span>
                  </div>
                  <p className="text-[10px] text-[#7183a0]">{stock.sector}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tab 4: Sector Overlap */}
        {activeTab === 'sectors' && (
          <div className="rounded-2xl border border-white/10 bg-[#080e1a] p-6 space-y-5">
            <h3 className="text-sm font-bold text-white">
              Sector Allocation & Overlap Breakdown
            </h3>
            <div className="space-y-4">
              {overlapResult.sectorBreakdown.map((sec) => (
                <div key={sec.sector} className="space-y-1.5">
                  <div className="flex justify-between text-xs">
                    <span className="font-semibold text-white">{sec.sector}</span>
                    <span className="font-mono text-[#7183a0]">
                      {fundA.schemeName.split(' ')[0]}: <strong className="text-[#00FF9D]">{sec.weightA}%</strong> | {fundB.schemeName.split(' ')[0]}: <strong className="text-[#66a3ff]">{sec.weightB}%</strong> | Overlap: <strong className="text-white">{sec.overlap}%</strong>
                    </span>
                  </div>
                  <div className="h-2 w-full bg-white/5 rounded-full overflow-hidden flex">
                    <div className="h-full bg-[#00FF9D]/80" style={{ width: `${Math.min(100, sec.weightA)}%` }} title={`${fundA.schemeName}: ${sec.weightA}%`} />
                    <div className="h-full bg-[#66a3ff]/80 ml-1" style={{ width: `${Math.min(100, sec.weightB)}%` }} title={`${fundB.schemeName}: ${sec.weightB}%`} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* ─── Bottom CTA Hub ─────────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-white/10 bg-gradient-to-r from-blue-950/30 to-emerald-950/20 p-6 sm:p-8 flex flex-col sm:flex-row items-center justify-between gap-6">
        <div>
          <h3 className="text-base font-bold text-white mb-1">
            Want deeper quantitative analysis between these two funds?
          </h3>
          <p className="text-xs text-[#aebed6]">
            Analyze 3-Year CAGR, Sharpe Ratios, Downside Capture, TER expense drag, and NAV freshness.
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <Link
            rel={comparePair ? undefined : 'nofollow'}
            href={
              comparePair
                ? `/compare/${comparePair.pair}`
                : `/dashboard?query=${encodeURIComponent(`Compare ${fundA.schemeName} and ${fundB.schemeName} with full metrics`)}`
            }
            className="px-5 py-2.5 rounded-xl bg-[#00FF9D] text-black font-bold text-xs hover:bg-[#00FF9D]/90 transition-colors shadow-lg shadow-[#00FF9D]/20 flex items-center gap-2"
          >
            <span>Compare Returns & Risk</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            href="/mutual-funds"
            className="px-4 py-2.5 rounded-xl border border-white/15 bg-white/5 text-white font-semibold text-xs hover:bg-white/10 transition-colors"
          >
            Browse All Funds
          </Link>
        </div>
      </section>
    </div>
  );
}
