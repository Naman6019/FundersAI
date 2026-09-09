'use client';

import React, { useState, useMemo, useEffect } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import type { FundEntry, AmcEntry } from '@/lib/fund-registry';

interface MutualFundExplorerProps {
  initialFunds: FundEntry[];
  amcs: AmcEntry[];
  categories: readonly string[];
}

export default function MutualFundExplorer({
  initialFunds,
  amcs,
  categories,
}: MutualFundExplorerProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  // URL state synchronization
  const [searchQuery, setSearchQuery] = useState(() => searchParams.get('q') || '');
  const [selectedAmc, setSelectedAmc] = useState<string>(() => searchParams.get('amc') || 'all');
  const [selectedCategory, setSelectedCategory] = useState<string>(() => searchParams.get('category') || 'all');
  const [selectedFundSlug, setSelectedFundSlug] = useState<string>(() => searchParams.get('fund') || '');
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  // Sync from URL params on searchParams update
  useEffect(() => {
    const qParam = searchParams.get('q') || '';
    const amcParam = searchParams.get('amc') || 'all';
    const catParam = searchParams.get('category') || 'all';
    const fundParam = searchParams.get('fund') || '';

    requestAnimationFrame(() => {
      setSearchQuery((prev) => (prev !== qParam ? qParam : prev));
      setSelectedAmc((prev) => (prev !== amcParam ? amcParam : prev));
      setSelectedCategory((prev) => (prev !== catParam ? catParam : prev));
      setSelectedFundSlug((prev) => (prev !== fundParam ? fundParam : prev));
    });
  }, [searchParams]);

  // Filtered funds list
  const filteredFunds = useMemo(() => {
    return initialFunds.filter((fund) => {
      // 1. AMC Family filter
      if (selectedAmc !== 'all' && fund.amcSlug !== selectedAmc) {
        return false;
      }
      // 2. Category filter
      if (
        selectedCategory !== 'all' &&
        fund.category.toLowerCase() !== selectedCategory.toLowerCase()
      ) {
        return false;
      }
      // 3. Search query filter (Fund name, AMC, scheme code, benchmark)
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase().trim();
        const matchesName = fund.schemeName.toLowerCase().includes(query);
        const matchesAmc = fund.amcName.toLowerCase().includes(query);
        const matchesCat = fund.category.toLowerCase().includes(query);
        const matchesBenchmark = fund.benchmark.toLowerCase().includes(query);
        const matchesCode = fund.schemeCode.toString().includes(query);
        return matchesName || matchesAmc || matchesCat || matchesBenchmark || matchesCode;
      }
      return true;
    });
  }, [initialFunds, selectedAmc, selectedCategory, searchQuery]);

  // Active highlighted fund in inspector
  const activeFund = useMemo(() => {
    if (selectedFundSlug) {
      const match = filteredFunds.find((f) => f.fundSlug === selectedFundSlug);
      if (match) return match;
    }
    return filteredFunds[0] || initialFunds[0];
  }, [filteredFunds, selectedFundSlug, initialFunds]);

  // Category counts for badges
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    categories.forEach((cat) => {
      counts[cat] = initialFunds.filter(
        (f) =>
          f.category.toLowerCase() === cat.toLowerCase() &&
          (selectedAmc === 'all' || f.amcSlug === selectedAmc)
      ).length;
    });
    return counts;
  }, [categories, initialFunds, selectedAmc]);

  // AMC counts for badges
  const amcCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    amcs.forEach((amc) => {
      counts[amc.slug] = initialFunds.filter(
        (f) =>
          f.amcSlug === amc.slug &&
          (selectedCategory === 'all' ||
            f.category.toLowerCase() === selectedCategory.toLowerCase())
      ).length;
    });
    return counts;
  }, [amcs, initialFunds, selectedCategory]);

  const handleResetFilters = () => {
    setSearchQuery('');
    setSelectedAmc('all');
    setSelectedCategory('all');
    setSelectedFundSlug('');
  };

  return (
    <div className="space-y-10">
      {/* ─── Control Bar: Live Search & View Switcher ─── */}
      <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5 backdrop-blur-xl shadow-2xl">
        <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
          {/* Search Input */}
          <div className="relative w-full md:max-w-xl">
            <div className="absolute inset-y-0 left-0 flex items-center pl-4 pointer-events-none text-[#7183a0]">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by fund name, AMC, category, or AMFI code..."
              className="w-full pl-11 pr-10 py-3 rounded-xl bg-[#0b101b] border border-white/10 text-sm text-white placeholder-[#7183a0] focus:outline-none focus:border-[#00FF9D]/60 focus:ring-1 focus:ring-[#00FF9D]/40 transition"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="absolute inset-y-0 right-0 flex items-center pr-3 text-[#7183a0] hover:text-white transition"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>

          {/* Results Summary & View Switcher */}
          <div className="flex items-center justify-between w-full md:w-auto gap-4">
            <span className="text-xs text-[#7183a0] whitespace-nowrap">
              Showing <strong className="text-[#00FF9D]">{filteredFunds.length}</strong> of {initialFunds.length} funds
            </span>

            <div className="inline-flex rounded-lg border border-white/10 bg-white/[0.02] p-1">
              <button
                onClick={() => setViewMode('grid')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition ${
                  viewMode === 'grid'
                    ? 'bg-[#00FF9D]/15 text-[#00FF9D] border border-[#00FF9D]/30 shadow-sm'
                    : 'text-[#7183a0] hover:text-white'
                }`}
              >
                Grid
              </button>
              <button
                onClick={() => setViewMode('table')}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold transition ${
                  viewMode === 'table'
                    ? 'bg-[#00FF9D]/15 text-[#00FF9D] border border-[#00FF9D]/30 shadow-sm'
                    : 'text-[#7183a0] hover:text-white'
                }`}
              >
                Table
              </button>
            </div>
          </div>
        </div>

        {/* ─── Dual Filter Section ─── */}
        <div className="mt-6 pt-6 border-t border-white/5 space-y-5">
          {/* 1. AMC Family Filter */}
          <div>
            <div className="flex items-center justify-between mb-2.5">
              <label className="text-[11px] font-bold uppercase tracking-widest text-[#7183a0]">
                Fund House (AMC Family)
              </label>
              {selectedAmc !== 'all' && (
                <button
                  onClick={() => setSelectedAmc('all')}
                  className="text-[10px] font-semibold text-[#82aff6] hover:underline"
                >
                  Reset AMC
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setSelectedAmc('all')}
                className={`px-3 py-1.5 rounded-full text-xs font-semibold transition ${
                  selectedAmc === 'all'
                    ? 'bg-[#00FF9D] text-black shadow-md shadow-[#00FF9D]/20'
                    : 'bg-white/[0.03] border border-white/10 text-[#aebed6] hover:border-white/25 hover:text-white'
                }`}
              >
                All AMCs
              </button>
              {amcs.map((amc) => {
                const count = amcCounts[amc.slug] || 0;
                const isSelected = selectedAmc === amc.slug;
                if (count === 0 && selectedCategory !== 'all') return null;
                return (
                  <button
                    key={amc.slug}
                    onClick={() => setSelectedAmc(isSelected ? 'all' : amc.slug)}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition ${
                      isSelected
                        ? 'bg-[#00FF9D] text-black font-semibold shadow-md shadow-[#00FF9D]/20'
                        : 'bg-white/[0.03] border border-white/10 text-[#aebed6] hover:border-white/25 hover:text-white'
                    }`}
                  >
                    <span>{amc.shortName}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                        isSelected
                          ? 'bg-black/20 text-black'
                          : 'bg-white/10 text-[#7183a0]'
                      }`}
                    >
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 2. SEBI Category Filter */}
          <div>
            <div className="flex items-center justify-between mb-2.5">
              <label className="text-[11px] font-bold uppercase tracking-widest text-[#7183a0]">
                SEBI Category
              </label>
              {selectedCategory !== 'all' && (
                <button
                  onClick={() => setSelectedCategory('all')}
                  className="text-[10px] font-semibold text-[#82aff6] hover:underline"
                >
                  Reset Category
                </button>
              )}
            </div>
            <div className="flex flex-wrap gap-2">
              <button
                onClick={() => setSelectedCategory('all')}
                className={`px-3 py-1.5 rounded-full text-xs font-semibold transition ${
                  selectedCategory === 'all'
                    ? 'bg-[#66a3ff] text-black shadow-md shadow-[#66a3ff]/20'
                    : 'bg-white/[0.03] border border-white/10 text-[#aebed6] hover:border-white/25 hover:text-white'
                }`}
              >
                All Categories
              </button>
              {categories.map((cat) => {
                const count = categoryCounts[cat] || 0;
                const isSelected = selectedCategory === cat;
                if (count === 0 && selectedAmc !== 'all') return null;
                return (
                  <button
                    key={cat}
                    onClick={() => setSelectedCategory(isSelected ? 'all' : cat)}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition ${
                      isSelected
                        ? 'bg-[#66a3ff] text-black font-semibold shadow-md shadow-[#66a3ff]/20'
                        : 'bg-white/[0.03] border border-white/10 text-[#aebed6] hover:border-white/25 hover:text-white'
                    }`}
                  >
                    <span>{cat}</span>
                    <span
                      className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                        isSelected
                          ? 'bg-black/20 text-black'
                          : 'bg-white/10 text-[#7183a0]'
                      }`}
                    >
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Active filter summary bar */}
          {(selectedAmc !== 'all' || selectedCategory !== 'all' || searchQuery) && (
            <div className="flex items-center gap-2 pt-2 text-xs">
              <span className="text-[#7183a0]">Active Filters:</span>
              {selectedAmc !== 'all' && (
                <span className="inline-flex items-center gap-1 bg-primary/10 text-primary border border-primary/30 px-2.5 py-0.5 rounded-md font-semibold">
                  AMC: {amcs.find((a) => a.slug === selectedAmc)?.shortName || selectedAmc}
                  <button type="button" aria-label="Remove AMC filter" onClick={() => setSelectedAmc('all')}>×</button>
                </span>
              )}
              {selectedCategory !== 'all' && (
                <span className="inline-flex items-center gap-1 bg-blue-500/10 text-blue-400 border border-blue-500/30 px-2.5 py-0.5 rounded-md font-semibold">
                  Category: {selectedCategory}
                  <button type="button" aria-label="Remove category filter" onClick={() => setSelectedCategory('all')}>×</button>
                </span>
              )}
              {searchQuery && (
                <span className="inline-flex items-center gap-1 bg-white/10 text-white border border-white/20 px-2.5 py-0.5 rounded-md">
                  &ldquo;{searchQuery}&rdquo;
                  <button type="button" aria-label="Clear search query" onClick={() => setSearchQuery('')}>×</button>
                </span>
              )}
              <button
                onClick={handleResetFilters}
                className="text-xs text-rose-400 hover:text-rose-300 underline ml-2"
              >
                Clear all
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ─── Selected Fund "Inspector Metric Canvas" ─── */}
      {activeFund && (
        <section className="relative overflow-hidden rounded-3xl border border-[#00FF9D]/30 bg-gradient-to-b from-[#00FF9D]/[0.06] via-white/[0.02] to-transparent p-6 sm:p-8 backdrop-blur-2xl shadow-2xl">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
            <div className="flex items-center gap-2">
              <span className="inline-block h-2 w-2 rounded-full bg-[#00FF9D] animate-pulse" />
              <p className="text-[10px] font-bold uppercase tracking-[0.25em] text-[#00FF9D]">
                Active Fund Inspector
              </p>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-[#7183a0]">
                AMFI Code: <strong className="text-white font-mono">{activeFund.schemeCode}</strong>
              </span>
              <span className="text-white/20">|</span>
              <span className="text-xs text-[#7183a0]">
                Plan: <strong className="text-white">{activeFund.plan} ({activeFund.option})</strong>
              </span>
            </div>
          </div>

          <div className="grid lg:grid-cols-3 gap-6 items-start">
            {/* Left Col: Overview */}
            <div className="lg:col-span-2 space-y-4">
              <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
                {activeFund.schemeName}
              </h2>
              <p className="text-sm leading-6 text-[#aebed6]">
                Managed by <strong className="text-white">{activeFund.amcName}</strong> in the SEBI <span className="text-[#00FF9D] font-semibold">{activeFund.category}</span> category. Primary benchmark: <span className="text-white font-medium">{activeFund.benchmark}</span>.
              </p>

              {/* Vitals Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
                <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5 text-center">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-[#7183a0] mb-0.5">AMC House</p>
                  <p className="text-sm font-bold text-white truncate">{activeFund.amcName.split(' ')[0]}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5 text-center">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-[#7183a0] mb-0.5">Category</p>
                  <p className="text-sm font-bold text-[#00FF9D] truncate">{activeFund.category}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5 text-center">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-[#7183a0] mb-0.5">Benchmark</p>
                  <p className="text-sm font-bold text-white truncate">{activeFund.benchmark.split(' ')[0]} Index</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3.5 text-center">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-[#7183a0] mb-0.5">Structure</p>
                  <p className="text-sm font-bold text-white truncate">Direct Growth</p>
                </div>
              </div>
            </div>

            {/* Right Col: 1-Click Action Hub */}
            <div className="rounded-2xl border border-white/10 bg-black/40 p-5 space-y-3">
              <p className="text-xs font-bold uppercase tracking-wider text-[#7183a0] mb-1">
                Deep Research Actions
              </p>

              <Link
                href={`/mutual-funds/${activeFund.amcSlug}/${activeFund.fundSlug}`}
                className="flex items-center justify-between w-full px-4 py-2.5 rounded-xl bg-[#00FF9D]/15 border border-[#00FF9D]/30 text-xs font-semibold text-[#00FF9D] hover:bg-[#00FF9D]/25 transition"
              >
                <span>View Full SEO Factsheet</span>
                <span>→</span>
              </Link>

              <Link
                rel="nofollow"
                href={`/dashboard?query=Run a complete quantitative analysis on ${activeFund.schemeName} vs ${activeFund.benchmark}`}
                className="flex items-center justify-between w-full px-4 py-2.5 rounded-xl bg-white/[0.04] border border-white/10 text-xs font-semibold text-white hover:bg-white/[0.08] transition"
              >
                <span>Run Analysis in Workspace</span>
                <span>⚡</span>
              </Link>

              <Link
                href={`/mutual-funds/${activeFund.amcSlug}`}
                className="flex items-center justify-between w-full px-4 py-2.5 rounded-xl bg-white/[0.02] border border-white/5 text-xs text-[#82aff6] hover:text-white transition"
              >
                <span>More from {activeFund.amcName.split(' ')[0]}</span>
                <span>↗</span>
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ─── Fund Results: Grid or Table Mode ─── */}
      {filteredFunds.length === 0 ? (
        <div className="text-center py-16 rounded-2xl border border-white/10 bg-white/[0.02] p-8 space-y-4">
          <p className="text-lg font-semibold text-white">No funds found matching your filters</p>
          <p className="text-xs text-[#7183a0] max-w-md mx-auto">
            Try adjusting your search query, or clear your AMC/Category selections. You can also search the full Supabase directory directly in the workspace.
          </p>
          <div className="pt-2 flex justify-center gap-3">
            <button
              onClick={handleResetFilters}
              className="px-4 py-2 rounded-xl bg-[#00FF9D] text-black text-xs font-bold hover:bg-[#00FF9D]/90 transition"
            >
              Reset Filters
            </button>
            <Link
              rel="nofollow"
              href={`/dashboard?query=${searchQuery || 'Search Indian mutual funds'}`}
              className="px-4 py-2 rounded-xl bg-white/10 border border-white/10 text-white text-xs font-semibold hover:bg-white/15 transition"
            >
              Search full database in workspace →
            </Link>
          </div>
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredFunds.map((fund) => {
            const isSelected = activeFund?.fundSlug === fund.fundSlug;
            return (
              <div
                key={`${fund.amcSlug}-${fund.fundSlug}`}
                role="button"
                tabIndex={0}
                onClick={() => setSelectedFundSlug(fund.fundSlug)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setSelectedFundSlug(fund.fundSlug);
                  }
                }}
                className={`cursor-pointer group flex flex-col justify-between rounded-2xl border p-5 transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary/40 ${
                  isSelected
                    ? 'border-primary bg-primary/10 shadow-lg shadow-primary/10'
                    : 'border-line bg-surface-1 hover:border-border-active hover:bg-surface-hover'
                }`}
              >
                <div>
                  {/* Category & Plan Badge */}
                  <div className="flex items-center justify-between gap-2 mb-3">
                    <span className="inline-flex items-center rounded-full border border-white/10 bg-white/[0.03] px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-[#00FF9D]">
                      {fund.category}
                    </span>
                    <span className="text-[10px] font-mono text-[#7183a0]">
                      #{fund.schemeCode}
                    </span>
                  </div>

                  {/* Fund Name */}
                  <h3 className="text-base font-bold text-white group-hover:text-[#00FF9D] transition-colors mb-2 leading-snug">
                    {fund.schemeName}
                  </h3>

                  <p className="text-xs text-[#7183a0] mb-4">
                    {fund.amcName} · {fund.benchmark}
                  </p>
                </div>

                <div className="pt-4 border-t border-white/5 flex items-center justify-between">
                  <span className="text-[11px] text-[#7183a0]">
                    {fund.plan} · {fund.option}
                  </span>
                  <Link
                    href={`/mutual-funds/${fund.amcSlug}/${fund.fundSlug}`}
                    onClick={(e) => e.stopPropagation()}
                    className="text-xs font-semibold text-[#82aff6] group-hover:text-[#b8d3ff] transition-colors"
                  >
                    Factsheet →
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* Table Mode */
        <div className="overflow-x-auto rounded-2xl border border-white/10 bg-white/[0.015]">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 bg-white/[0.02]">
                <th className="text-left px-5 py-4 font-semibold text-white text-xs uppercase tracking-wider">Fund Name</th>
                <th className="text-left px-4 py-4 font-semibold text-white text-xs uppercase tracking-wider">AMC House</th>
                <th className="text-left px-4 py-4 font-semibold text-white text-xs uppercase tracking-wider">Category</th>
                <th className="text-left px-4 py-4 font-semibold text-white text-xs uppercase tracking-wider">Benchmark</th>
                <th className="text-left px-4 py-4 font-semibold text-white text-xs uppercase tracking-wider">AMFI Code</th>
                <th className="text-right px-5 py-4 font-semibold text-white text-xs uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {filteredFunds.map((fund) => {
                const isSelected = activeFund?.fundSlug === fund.fundSlug;
                return (
                  <tr
                    key={`${fund.amcSlug}-${fund.fundSlug}`}
                    onClick={() => setSelectedFundSlug(fund.fundSlug)}
                    className={`cursor-pointer transition ${
                      isSelected
                        ? 'bg-[#00FF9D]/[0.08]'
                        : 'hover:bg-white/[0.025]'
                    }`}
                  >
                    <td className="px-5 py-4 text-white font-medium">
                      <div className="flex items-center gap-2">
                        {isSelected && <span className="h-1.5 w-1.5 rounded-full bg-[#00FF9D]" />}
                        <span>{fund.schemeName}</span>
                      </div>
                    </td>
                    <td className="px-4 py-4 text-[#aebed6]">{fund.amcName}</td>
                    <td className="px-4 py-4 text-[#00FF9D] text-xs font-semibold">{fund.category}</td>
                    <td className="px-4 py-4 text-[#7183a0] text-xs">{fund.benchmark}</td>
                    <td className="px-4 py-4 font-mono text-xs text-[#7183a0]">{fund.schemeCode}</td>
                    <td className="px-5 py-4 text-right whitespace-nowrap">
                      <Link
                        href={`/mutual-funds/${fund.amcSlug}/${fund.fundSlug}`}
                        onClick={(e) => e.stopPropagation()}
                        className="text-xs font-semibold text-[#82aff6] hover:text-[#b8d3ff] transition-colors"
                      >
                        Factsheet →
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
