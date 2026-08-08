'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar';
import { AppSidebar } from '@/components/layout/AppSidebar';
import { motion, useReducedMotion } from 'framer-motion';
import {
  ChartSpline,
  Clock3,
  Database,
  ShieldCheck,
  Landmark,
  Brain,
  AlertCircle,
  CheckCircle2,
  ArrowLeftRight,
  ArrowRight,
  Search,
  PieChart,
  Wallet,
  TrendingUp,
  History,
  Check,
  X,
  Sparkles,
} from 'lucide-react';
import { useCanvasStore } from '@/store/useCanvasStore';
import { useChatStore } from '@/store/useChatStore';
import ChatWindow from '@/components/chat/ChatWindow';
import StockDetailView from '@/components/canvas/StockDetailView';
import MFDetailView from '@/components/canvas/MFDetailView';
import ComparisonView from '@/components/canvas/ComparisonView';
import PortfolioReviewView from '@/components/canvas/PortfolioReviewView';
import CategoryCompareView from '@/components/canvas/CategoryCompareView';
import FundSearchSelect from '@/components/ui/FundSearchSelect';
import { supabaseBrowser } from '@/lib/supabaseBrowser';
import type { CategoryComparePayload, CategoryFundRow, SearchResultItem } from '@/types/funds';
import type { UserTier } from '@/lib/billing/tiers';
import { useDataHealthContext } from '@/components/data-health/DataHealthProvider';
import { dataHealthSummary, statusDotClass } from '@/lib/dataHealth';
import { Panel } from '@/components/ui/Panel';
import LandingThemeToggle from '@/components/landing/LandingThemeToggle';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';

const HEADER_HEIGHT = 64;
const MAIN_PADDING = 24;
const PANEL_GAP = 16;
const RESIZE_HANDLE_WIDTH = 12;
const CHAT_MIN_WIDTH = 320;
const CANVAS_MIN_WIDTH = 420;
const INITIAL_CANVAS_WIDTH = 550;

const FUND_CATEGORIES = [
  { key: 'large_cap', title: 'Large Cap', desc: 'Top 100 companies', icon: Landmark },
  { key: 'mid_cap', title: 'Mid Cap', desc: 'High growth potential', icon: TrendingUp },
  { key: 'small_cap', title: 'Small Cap', desc: 'Aggressive growth', icon: ChartSpline },
  { key: 'flexi_cap', title: 'Flexi Cap', desc: 'Dynamic allocation', icon: PieChart },
  { key: 'index', title: 'Index Funds', desc: 'Low cost tracking', icon: Database },
  { key: 'elss', title: 'ELSS', desc: 'Tax saving funds', icon: ShieldCheck },
];

function CanvasPlaceholder() {
  return (
    <div className="flex h-full flex-col rounded-2xl border border-gray-800/80 bg-[#050810]/95 p-6 shadow-2xl backdrop-blur-xl">
      <div className="flex items-start justify-between">
        <div>
          <div className="font-mono text-[10px] uppercase font-bold tracking-widest text-blue-400 px-2.5 py-0.5 rounded bg-blue-500/10 border border-blue-500/20 mb-2 inline-block">
            [ RESEARCH_ONLY • DATA_BACKED ]
          </div>
          <h2 className="text-2xl font-bold tracking-tight text-white font-serif-display">Comparison Canvas</h2>
          <p className="mt-1 text-xs text-gray-400 font-sans">Ask FundersAI to compare funds and open side-by-side quantitative metrics from stored SEBI disclosures.</p>
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-4">
        {[
          { label: 'RECORD_SEARCH', value: 'Normalized', note: 'Strict DB records' },
          { label: 'DATA_HEALTH', value: 'Verified', note: 'Stale fields flagged' },
          { label: 'COMPARE', value: 'Side-by-side', note: 'Returns, risk, overlap' },
          { label: 'EXPLAIN', value: 'Research Only', note: 'Zero financial advice' },
        ].map((item) => (
          <div key={item.label} className="rounded-xl border border-gray-800/80 bg-[#070b12]/80 p-3.5">
            <p className="font-mono text-[10px] uppercase tracking-wider text-blue-400">{item.label}</p>
            <p className="mt-1 text-base font-bold tracking-tight text-white">{item.value}</p>
            <p className="mt-0.5 text-[11px] text-gray-500">{item.note}</p>
          </div>
        ))}
      </div>

      <div className="mt-5 flex-1 rounded-xl border border-gray-800/80 bg-[#070b12]/60 p-4 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(rgba(59,130,246,0.06)_1px,transparent_1px)] [background-size:20px_20px]" />
        <svg viewBox="0 0 700 260" className="h-full w-full relative z-10" aria-hidden>
          <path d="M30 210 C110 180, 150 192, 220 160 C270 138, 300 150, 360 122 C410 98, 450 112, 510 86 C560 66, 620 82, 670 72" fill="none" stroke="#2563eb" strokeWidth="3.5" strokeLinecap="round"/>
          <path d="M30 224 C105 202, 150 198, 220 188 C280 178, 310 166, 360 172 C412 178, 455 144, 510 150 C560 156, 620 126, 670 132" fill="none" stroke="#06b6d4" strokeWidth="2.5" strokeLinecap="round"/>
        </svg>
      </div>
      <div className="mt-4 rounded-xl border border-blue-500/20 bg-blue-500/10 p-3 text-[11px] font-mono leading-5 text-blue-300">
        FundersAI shows &quot;Not available&quot; for missing fields, flags partial data, and maintains 100% deterministic transparency.
      </div>
    </div>
  );
}

function FineGrid() {
  const reduceMotion = useReducedMotion();

  return (
    <motion.div
      aria-hidden="true"
      className="absolute inset-0 z-0 bg-[linear-gradient(to_right,rgba(102,163,255,0.08)_1px,transparent_1px),linear-gradient(to_bottom,rgba(102,163,255,0.07)_1px,transparent_1px)] bg-[size:88px_88px] [mask-image:radial-gradient(ellipse_at_top,black_22%,transparent_74%)]"
      animate={reduceMotion ? undefined : { backgroundPosition: ["0px 0px", "88px 88px"], opacity: [0.42, 0.62, 0.42] }}
      transition={reduceMotion ? undefined : { backgroundPosition: { duration: 34, repeat: Infinity, ease: "linear" }, opacity: { duration: 8, repeat: Infinity, ease: "easeInOut" } }}
    />
  );
}

export default function DashboardLayout() {
  const { activeView, selectedIds, auxiliaryData, isCanvasOpen } = useCanvasStore();
  const [activeTab, setActiveTab] = useState<'overview' | 'research'>('research');
  const [currentTier, setCurrentTier] = useState<UserTier>('free');
  const [isResizingCanvas, setIsResizingCanvas] = useState(false);
  const [canvasWidth, setCanvasWidth] = useState(INITIAL_CANVAS_WIDTH);
  const [compareFund1, setCompareFund1] = useState<SearchResultItem | null>(null);
  const [compareFund2, setCompareFund2] = useState<SearchResultItem | null>(null);

  const setPendingQuery = useChatStore((state) => state.setPendingQuery);
  const { data: dataHealth, lastSuccessfulCheck } = useDataHealthContext();
  const healthSummary = dataHealthSummary(dataHealth.metrics);

  const getCanvasBounds = () => {
    const shellPadding = MAIN_PADDING * 2;
    const splitChrome = (PANEL_GAP * 2) + RESIZE_HANDLE_WIDTH;
    const availableWidth = window.innerWidth - shellPadding;
    const max = Math.max(availableWidth - CHAT_MIN_WIDTH - splitChrome, CANVAS_MIN_WIDTH);
    return { min: CANVAS_MIN_WIDTH, max };
  };

  useEffect(() => {
    fetch('/api/keepalive').catch(() => {});
  }, []);

  useEffect(() => {
    let ignore = false;
    const loadBilling = async () => {
      const { data } = await supabaseBrowser.auth.getSession();
      const token = data.session?.access_token;
      if (!token) return;
      const res = await fetch('/api/billing/subscriptions', {
        headers: { Authorization: `Bearer ${token}` },
        cache: 'no-store',
      });
      if (!res.ok) return;
      const payload = await res.json().catch(() => ({}));
      const tier = payload?.profile?.tier;
      if (!ignore && (tier === 'pro' || tier === 'ultra' || tier === 'free')) {
        setCurrentTier(tier);
      }
    };
    void loadBilling();
    return () => { ignore = true; };
  }, []);

  useEffect(() => {
    const onResize = () => {
      setCanvasWidth((prev) => {
        const { min, max } = getCanvasBounds();
        return Math.min(Math.max(prev, min), max);
      });
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  useEffect(() => {
    if (!isResizingCanvas) return;
    const onMouseMove = (event: MouseEvent) => {
      const { min, max } = getCanvasBounds();
      const next = window.innerWidth - MAIN_PADDING - event.clientX;
      setCanvasWidth(Math.min(Math.max(next, min), max));
    };
    const onMouseUp = () => setIsResizingCanvas(false);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    return () => {
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
    };
  }, [isResizingCanvas]);

  const handleOverviewQuery = (query: string) => {
    setPendingQuery(query);
    setActiveTab('research');
  };

  const handleQuickCompare = () => {
    if (compareFund1 && compareFund2) {
      const { openCanvas } = useCanvasStore.getState();
      openCanvas({
        view: 'COMPARISON',
        ids: [compareFund1.id, compareFund2.id]
      });
      setActiveTab('research');
      setPendingQuery(`Compare ${compareFund1.displayName} and ${compareFund2.displayName}`);
    }
  };

  const formatPercent = (value: unknown) => {
    if (value === null || value === undefined || value === '' || value === 'N/A') return 'Not available';
    const num = Number(value);
    return Number.isFinite(num) ? `${num.toFixed(2)}%` : 'Not available';
  };

  const formatAum = (value: unknown) => {
    if (value === null || value === undefined || value === '' || value === 'N/A') return 'Not available';
    const num = Number(value);
    return Number.isFinite(num) ? `INR ${Math.round(num).toLocaleString('en-IN')}` : 'Not available';
  };

  const formatRiskLabel = (value: unknown) => {
    const label = typeof value === 'string' ? value.trim() : '';
    return label || 'Coverage pending';
  };

  const compactFundName = (value: unknown) => String(value || 'Not available')
    .replace(/\s*-\s*Direct Plan\s*-\s*Growth/gi, '')
    .replace(/\s*Direct\s*Growth/gi, '')
    .trim();

  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [categoryFunds, setCategoryFunds] = useState<CategoryFundRow[]>([]);
  const [categoryLoading, setCategoryLoading] = useState(false);
  const [categoryError, setCategoryError] = useState<string | null>(null);
  const [selectedCategoryCodes, setSelectedCategoryCodes] = useState<string[]>([]);
  const [categoryCompare, setCategoryCompare] = useState<CategoryComparePayload | null>(null);
  const [categoryCompareLoading, setCategoryCompareLoading] = useState(false);
  const [categoryCompareError, setCategoryCompareError] = useState<string | null>(null);

  const loadCategoryFunds = async (categoryKey: string) => {
    setActiveCategory(categoryKey);
    setCategoryLoading(true);
    setCategoryError(null);
    setCategoryCompare(null);
    setCategoryCompareError(null);
    setSelectedCategoryCodes([]);
    try {
      const res = await fetch(`/api/funds/category?category=${encodeURIComponent(categoryKey)}`, { cache: 'no-store' });
      if (!res.ok) throw new Error('Unable to load category funds.');
      const payload = await res.json();
      setCategoryFunds(Array.isArray(payload?.rows) ? payload.rows : []);
    } catch (error) {
      setCategoryFunds([]);
      setCategoryError((error as Error).message || 'Unable to load category funds.');
    } finally {
      setCategoryLoading(false);
    }
  };

  const toggleCategorySelection = (fund: CategoryFundRow) => {
    if (!fund.is_supported) return;
    const code = String(fund.scheme_code || '').trim();
    if (!code) return;
    setSelectedCategoryCodes((current) => {
      if (current.includes(code)) return current.filter((item) => item !== code);
      if (current.length >= 3) return current;
      return [...current, code];
    });
  };

  const compareSelectedCategoryFunds = async () => {
    if (!activeCategory || selectedCategoryCodes.length < 2 || selectedCategoryCodes.length > 3) return;
    setCategoryCompareLoading(true);
    setCategoryCompareError(null);
    try {
      const res = await fetch('/api/funds/category/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category: activeCategory, scheme_codes: selectedCategoryCodes }),
      });
      const payload = await res.json();
      if (!res.ok) throw new Error(payload?.detail || payload?.error || 'Unable to compare selected funds.');
      setCategoryCompare(payload);
    } catch (error) {
      setCategoryCompare(null);
      setCategoryCompareError((error as Error).message || 'Unable to compare selected funds.');
    } finally {
      setCategoryCompareLoading(false);
    }
  };

  const useCategoryCompareInChat = () => {
    if (!categoryCompare?.selected_funds?.length) return;
    const { openCanvas } = useCanvasStore.getState();
    openCanvas({
      view: 'COMPARISON',
      ids: selectedCategoryCodes
    });
    setActiveTab('research');

    const names = categoryCompare.selected_funds.map((fund) => compactFundName(fund.scheme_name));
    const last = names.pop();
    const joined = names.length ? `${names.join(', ')} and ${last}` : last;
    setPendingQuery(`Compare ${joined} from the ${categoryCompare.category} bucket.`);
  };

  const renderOverview = () => {
    return (
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h2 className="font-serif text-3xl font-semibold text-white tracking-tight">What can I safely do here?</h2>
            <p className="font-body-sm text-[14px] text-slate-400 mt-1 max-w-2xl">
              Compare verified funds, ask source-backed research questions, and review portfolio structure without advisory output.
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <Panel
            onClick={() => handleOverviewQuery('Compare Axis Flexi Cap and HDFC Flexi Cap')}
            className="p-6 hover:border-[#00FF9D]/40 transition-colors cursor-pointer group shadow-lg"
          >
            <div className="w-10 h-10 rounded-lg bg-[#00FF9D]/10 flex items-center justify-center mb-4 group-hover:bg-[#00FF9D]/20 transition-colors">
              <ArrowLeftRight className="text-[#00FF9D] h-5 w-5" />
            </div>
            <h3 className="font-serif text-lg font-medium text-white mb-2">Compare Funds</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Compare returns, risk, expense ratio, AUM, fund category, and consistency side-by-side.
            </p>
            <p className="mt-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#8ea7cd]">Comparison only, not advice</p>
          </Panel>

          <Panel
            onClick={() => setActiveTab('research')}
            className="border-[#00FF9D]/20 p-6 hover:border-[#00FF9D]/60 transition-colors cursor-pointer group relative overflow-hidden shadow-lg"
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-[#00FF9D]/5 rounded-full blur-3xl pointer-events-none"></div>
            <div className="w-10 h-10 rounded-lg bg-[#00FF9D]/20 flex items-center justify-center mb-4 group-hover:bg-[#00FF9D]/30 transition-colors relative z-10">
              <Brain className="text-[#00FF9D] h-5 w-5" />
            </div>
            <h3 className="font-serif text-lg font-medium text-white mb-2 relative z-10">Ask Research Question</h3>
            <p className="text-sm text-slate-400 leading-relaxed relative z-10">
              Ask FundersAI to explain funds, compare strategies, or simplify complex fund data.
            </p>
            <p className="mt-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#8ea7cd] relative z-10">Source-backed explanation, not a recommendation</p>
          </Panel>

          <Panel
            onClick={() => handleOverviewQuery('Review my portfolio diversification')}
            className="p-6 hover:border-[#00FF9D]/40 transition-colors cursor-pointer group shadow-lg"
          >
            <div className="w-10 h-10 rounded-lg bg-[#00FF9D]/10 flex items-center justify-center mb-4 group-hover:bg-[#00FF9D]/20 transition-colors">
              <Wallet className="text-[#00FF9D] h-5 w-5" />
            </div>
            <h3 className="font-serif text-lg font-medium text-white mb-2">Portfolio Review</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Review holdings structure, concentration, and diversification signals.
            </p>
            <p className="mt-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#8ea7cd]">Diversification read, not portfolio advice</p>
          </Panel>
        </div>

        <div className="rounded-xl border border-[#00FF9D]/20 bg-[#00FF9D]/[0.055] p-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-[#00FF9D]" />
                <h3 className="text-sm font-semibold text-white">How FundersAI keeps answers grounded</h3>
              </div>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-300">
                The app reads normalized stored data for search, compare, charts, and detail views. AI explains what is available; it does not fill missing values or make recommendations.
              </p>
            </div>
            <span className="inline-flex w-fit rounded-full border border-amber-300/25 bg-amber-300/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-amber-100">
              Research-only
            </span>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {[
              { icon: CheckCircle2, label: 'Real records', note: 'Collected data is stored before it appears in the UI.' },
              { icon: Database, label: 'Structured fields', note: 'Messy inputs become normalized records for app reads.' },
              { icon: Clock3, label: 'Freshness visible', note: 'Stale, partial, or missing data is shown near the result.' },
              { icon: AlertCircle, label: 'Limits shown', note: 'Unsupported claims stay out of the answer.' },
            ].map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.label} className="rounded-lg border border-white/10 bg-white/[0.04] p-3">
                  <div className="flex items-center gap-2 text-xs font-semibold text-white">
                    <Icon className="h-3.5 w-3.5 text-[#00FF9D]" />
                    {item.label}
                  </div>
                  <p className="mt-2 text-[11px] leading-5 text-slate-400">{item.note}</p>
                </div>
              );
            })}
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 space-y-6">
            <Panel className="relative z-30 p-6 shadow-lg">
              <div className="flex items-center gap-2 mb-4">
                <ArrowLeftRight className="text-[#00FF9D] h-5 w-5" />
                <h3 className="font-serif text-xl font-medium text-white">Quick Compare</h3>
              </div>
              <div className="flex flex-col sm:flex-row gap-3 items-center">
                <div className="flex-1 w-full relative">
                  <FundSearchSelect
                    placeholder="Search Fund 1..."
                    onSelect={setCompareFund1}
                  />
                </div>
                <div className="flex-shrink-0 text-white/50 text-sm font-medium">VS</div>
                <div className="flex-1 w-full relative">
                  <FundSearchSelect
                    placeholder="Search Fund 2..."
                    onSelect={setCompareFund2}
                  />
                </div>
                <button
                  onClick={handleQuickCompare}
                  disabled={!compareFund1 || !compareFund2}
                  className="w-full sm:w-auto mt-2 sm:mt-0 whitespace-nowrap bg-[#00FF9D] text-black font-semibold px-6 py-2.5 rounded-lg hover:bg-[#00FF9D]/90 disabled:opacity-50 disabled:cursor-not-allowed transition"
                >
                  Compare
                </button>
              </div>
            </Panel>

            <div className="relative z-0">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <h3 className="font-serif text-xl font-medium text-white">Explore by Category</h3>
                  <p className="mt-1 text-xs text-slate-400">List funds by bucket, select 2-3 supported funds, then compare metrics and portfolios.</p>
                </div>
                {selectedCategoryCodes.length > 0 && (
                  <span className="rounded-full border border-[#00FF9D]/25 bg-[#00FF9D]/10 px-3 py-1 text-xs text-[#b3ffdb]">
                    {selectedCategoryCodes.length}/3 selected
                  </span>
                )}
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {FUND_CATEGORIES.map((cat) => {
                  const CatIcon = cat.icon;
                  return (
                    <Panel
                      key={cat.key}
                      onClick={() => loadCategoryFunds(cat.key)}
                      className={`text-left p-4 transition-all cursor-pointer group shadow-sm ${
                        activeCategory === cat.key
                          ? 'border-[#00FF9D]/60 bg-[#00FF9D]/10 shadow-[0_4px_16px_rgba(102,163,255,0.15)]'
                          : 'border-white/10 hover:border-[#00FF9D]/30 hover:bg-[#1a2333]'
                      }`}
                    >
                      <CatIcon className="text-[#00FF9D] h-4 w-4 mb-2 opacity-80 group-hover:opacity-100 transition-opacity" />
                      <div className="text-sm font-medium text-white mb-0.5">{cat.title}</div>
                      <div className="text-[11px] text-slate-400">{cat.desc}</div>
                    </Panel>
                  );
                })}
              </div>

              {activeCategory && (
                <div className="mt-4 rounded-xl border border-white/10 bg-[#101827]/70 p-4">
                  <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <h4 className="text-sm font-semibold text-white">
                        {FUND_CATEGORIES.find((item) => item.key === activeCategory)?.title || 'Category'} funds
                      </h4>
                      <p className="mt-1 text-xs text-slate-400">Unsupported AMCs are visible but disabled until their pipeline is ready.</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={compareSelectedCategoryFunds}
                        disabled={selectedCategoryCodes.length < 2 || selectedCategoryCodes.length > 3 || categoryCompareLoading}
                        className="rounded-lg bg-[#00FF9D] px-3 py-1.5 text-xs font-semibold text-slate-950 transition hover:bg-[#00FF9D]/85 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {categoryCompareLoading ? 'Comparing...' : 'Compare Selected'}
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedCategoryCodes([]);
                          setCategoryCompare(null);
                        }}
                        disabled={selectedCategoryCodes.length === 0}
                        className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:border-[#00FF9D]/40 disabled:cursor-not-allowed disabled:opacity-40"
                      >
                        Clear
                      </button>
                    </div>
                  </div>

                  {categoryLoading && <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4 text-sm text-slate-300">Loading funds...</div>}
                  {categoryError && <div className="rounded-lg border border-rose-400/20 bg-rose-400/10 p-4 text-sm text-rose-100">{categoryError}</div>}
                  {!categoryLoading && !categoryError && categoryFunds.length === 0 && (
                    <div className="rounded-lg border border-white/10 bg-white/[0.03] p-4 text-sm text-slate-300">No funds found for this bucket.</div>
                  )}
                  {!categoryLoading && !categoryError && categoryFunds.length > 0 && (
                    <div className="max-h-96 overflow-y-auto rounded-lg border border-white/10">
                      <table className="min-w-full text-left text-xs">
                        <thead className="sticky top-0 bg-[#172033] text-[#8ea7cd]">
                          <tr>
                            <th className="px-3 py-2 font-semibold">Select</th>
                            <th className="px-3 py-2 font-semibold">Fund</th>
                            <th className="px-3 py-2 font-semibold">AMC</th>
                            <th className="px-3 py-2 font-semibold">3Y</th>
                            <th className="px-3 py-2 font-semibold">AUM</th>
                            <th className="px-3 py-2 font-semibold">Expense</th>
                            <th className="px-3 py-2 font-semibold">Risk</th>
                            <th className="px-3 py-2 font-semibold">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/10">
                          {categoryFunds.map((fund) => {
                            const code = String(fund.scheme_code || '');
                            const selected = selectedCategoryCodes.includes(code);
                            const disabled = !fund.is_supported;
                            return (
                              <tr key={code || fund.scheme_name} className={disabled ? 'bg-white/[0.015] text-slate-500 opacity-60' : 'text-[#d7e4fb] hover:bg-white/[0.03]'}>
                                <td className="px-3 py-3">
                                  <button
                                    type="button"
                                    onClick={() => toggleCategorySelection(fund)}
                                    disabled={disabled || (!selected && selectedCategoryCodes.length >= 3)}
                                    className={`grid h-6 w-6 place-items-center rounded-md border transition ${
                                      selected
                                        ? 'border-[#00FF9D] bg-[#00FF9D] text-slate-950'
                                        : 'border-white/15 bg-white/[0.03] text-slate-300 disabled:cursor-not-allowed'
                                    }`}
                                    aria-label={`Select ${fund.scheme_name}`}
                                  >
                                    {selected && <Check className="h-3.5 w-3.5" />}
                                  </button>
                                </td>
                                <td className="max-w-64 px-3 py-3 font-medium text-white">
                                  <div className="line-clamp-2">{compactFundName(fund.scheme_name)}</div>
                                  <div className="mt-1 text-[10px] text-slate-500">{fund.category || 'Category unavailable'}</div>
                                </td>
                                <td className="px-3 py-3">{fund.amc_name || 'Not available'}</td>
                                <td className="px-3 py-3 font-mono">{formatPercent(fund.return_3y)}</td>
                                <td className="px-3 py-3 font-mono">{formatAum(fund.aum)}</td>
                                <td className="px-3 py-3 font-mono">{formatPercent(fund.expense_ratio)}</td>
                                <td className="px-3 py-3">
                                  <div className="max-w-32 text-[11px] text-slate-300">{formatRiskLabel(fund.risk_level)}</div>
                                  {fund.risk_level && <div className="mt-0.5 text-[10px] text-slate-500">Official AMC factsheet</div>}
                                </td>
                                <td className="px-3 py-3">
                                  {disabled ? (
                                    <span className="rounded-full border border-amber-400/20 bg-amber-400/10 px-2 py-1 text-[10px] font-semibold text-amber-200">Coverage pending</span>
                                  ) : (
                                    <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-2 py-1 text-[10px] font-semibold text-emerald-200">Ready</span>
                                  )}
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {categoryCompareError && <div className="mt-3 rounded-lg border border-rose-400/20 bg-rose-400/10 p-3 text-sm text-rose-100">{categoryCompareError}</div>}
                  {categoryCompare && (
                    <div className="mt-4 rounded-xl border border-[#00FF9D]/20 bg-[#00FF9D]/[0.06] p-4">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <h4 className="text-sm font-semibold text-white">{categoryCompare.category} comparison ready</h4>
                          <p className="mt-1 text-xs text-slate-300">{categoryCompare.insights?.headline || categoryCompare.research_note}</p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            onClick={useCategoryCompareInChat}
                            className="rounded-lg bg-[#00FF9D] px-3 py-1.5 text-xs font-semibold text-slate-950 transition hover:bg-[#00FF9D]/85"
                          >
                            Open Canvas Comparison
                          </button>
                        </div>
                      </div>
                      <div className="mt-3 grid gap-2 sm:grid-cols-3">
                        {categoryCompare.selected_funds.map((fund) => (
                          <div key={String(fund.scheme_code)} className="rounded-lg border border-white/10 bg-white/[0.04] p-3">
                            <div className="line-clamp-2 text-xs font-semibold text-white">{compactFundName(fund.scheme_name)}</div>
                            <div className="mt-2 text-[11px] text-slate-400">3Y {formatPercent(fund.return_3y)} · TER {formatPercent(fund.expense_ratio)}</div>
                            <div className="mt-1 text-[11px] text-slate-400">{formatRiskLabel(fund.risk_level)}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="space-y-6">
            <Panel className="p-6 shadow-lg">
              <h3 className="font-serif text-lg font-medium text-white mb-4">Investor Tools</h3>
              <div className="space-y-2">
                <Link href="/dashboard/research-evidence" className="w-full text-left p-3 rounded-lg border border-[#00FF9D]/20 bg-[#00FF9D]/[0.06] hover:bg-[#00FF9D]/10 hover:border-[#00FF9D]/30 transition-all cursor-pointer flex items-center justify-between group">
                  <div>
                    <div className="text-[13px] font-medium text-white">Official Evidence Lab</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">Inspect retrieval, citations, traces, and evals</div>
                  </div>
                  <ArrowRight className="h-4 w-4 text-[#00FF9D] transition-colors" />
                </Link>
                <div onClick={() => handleOverviewQuery('Is this a good time to invest in mid cap funds?')} className="w-full text-left p-3 rounded-lg border border-white/10 bg-white/[0.02] hover:bg-white/[0.04] transition-all cursor-pointer flex items-center justify-between group">
                  <div>
                    <div className="text-[13px] font-medium text-white">Market Outlook</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">Macro trends and equity valuations</div>
                  </div>
                  <ArrowRight className="h-4 w-4 text-white/30 group-hover:text-white/70 transition-colors" />
                </div>
                <div onClick={() => handleOverviewQuery('Explain the difference between growth and value investing')} className="w-full text-left p-3 rounded-lg border border-white/10 bg-white/[0.02] hover:bg-white/[0.04] transition-all cursor-pointer flex items-center justify-between group">
                  <div>
                    <div className="text-[13px] font-medium text-white">Learn Concepts</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">Investing principles simplified</div>
                  </div>
                  <ArrowRight className="h-4 w-4 text-white/30 group-hover:text-white/70 transition-colors" />
                </div>
              </div>
            </Panel>

            <Panel className="p-6 shadow-lg">
              <h3 className="font-serif text-lg font-medium text-white mb-4">Recent Activity</h3>
              <div className="space-y-3">
                <div onClick={() => handleOverviewQuery('Analyze Parag Parikh Flexi Cap Fund')} className="flex items-center gap-3 cursor-pointer group">
                  <div className="w-8 h-8 rounded bg-[#111] border border-[#222] flex items-center justify-center shrink-0">
                    <History className="h-3.5 w-3.5 text-slate-400" />
                  </div>
                  <div>
                    <div className="text-[12px] font-medium text-white group-hover:text-[#00FF9D] transition-colors">Parag Parikh Flexi Cap</div>
                    <div className="text-[10px] text-slate-500">Fund Analysis • 2h ago</div>
                  </div>
                </div>
                <div onClick={() => handleOverviewQuery('Compare Axis Flexi Cap and HDFC Flexi Cap')} className="flex items-center gap-3 cursor-pointer group">
                  <div className="w-8 h-8 rounded bg-[#111] border border-[#222] flex items-center justify-center shrink-0">
                    <History className="h-3.5 w-3.5 text-slate-400" />
                  </div>
                  <div>
                    <div className="text-[12px] font-medium text-white group-hover:text-[#00FF9D] transition-colors">Axis Flexi vs HDFC Flexi</div>
                    <div className="text-[10px] text-slate-500">Comparison • 1d ago</div>
                  </div>
                </div>
              </div>
            </Panel>
          </div>
        </div>

        <div className="pt-6 border-t border-white/10 text-center">
           <p className="text-[11px] text-slate-500 leading-relaxed max-w-4xl mx-auto">
             <span className="font-semibold text-slate-400">Disclaimer:</span> FundersAI provides educational insights and data-driven research. Mutual fund investments are subject to market risks, read all scheme related documents carefully. The information provided here is not financial advice. Past performance is not indicative of future returns.
           </p>
        </div>
      </div>
    );
  };

  const renderCanvasContent = () => {
    switch (activeView) {
      case 'STOCK_DETAIL':
        return <StockDetailView stockId={selectedIds[0]} />;
      case 'MF_DETAIL':
        return <MFDetailView schemeCode={selectedIds[0]} />;
      case 'COMPARISON':
        return (
          <ComparisonView
            key={`comparison:${selectedIds.join('|')}`}
            ids={selectedIds}
            type={selectedIds[0]?.match(/^[0-9]+$/) ? 'MUTUAL_FUND' : 'STOCK'}
            auxiliaryData={auxiliaryData}
          />
        );
      case 'COMPARISON_GRAPH_ONLY':
        return (
          <ComparisonView
            key={`comparison-graph:${selectedIds.join('|')}`}
            ids={selectedIds}
            type={selectedIds[0]?.match(/^[0-9]+$/) ? 'MUTUAL_FUND' : 'STOCK'}
            auxiliaryData={auxiliaryData}
            variant="graph_only"
          />
        );
      case 'PORTFOLIO_REVIEW':
        return <PortfolioReviewView auxiliaryData={auxiliaryData} />;
      case 'CATEGORY_COMPARE':
        return <CategoryCompareView auxiliaryData={auxiliaryData} />;
      default:
        return <CanvasPlaceholder />;
    }
  };

  return (
    <SidebarProvider>
      <AppSidebar 
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        currentTier={currentTier}
      />
      <div className="relative h-screen w-full overflow-hidden bg-[#050505] text-[#e8f0ff] flex flex-col selection:bg-[#00FF9D]/30 selection:text-white flex-1">
        <FineGrid />
        <div className="pointer-events-none absolute inset-0 z-0 bg-[radial-gradient(circle_at_50%_0%,rgba(102,163,255,0.06),transparent_65%)]" />

        <div className="relative z-10 flex flex-col flex-1 h-full w-full overflow-hidden bg-transparent">
          <EcosystemHeader
            currentApp="research"
            dataTrustHref="/dashboard/data-trust"
            containerClassName="w-full px-4 sm:px-6"
            leading={<SidebarTrigger className="text-slate-200 hover:text-white transition shrink-0" />}
            centerSlot={
              <div className="hidden relative max-w-xs w-full sm:block">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 h-3.5 w-3.5" />
                <input
                  type="text"
                  placeholder="Search tickers, funds, research..."
                  className="w-full bg-black/20 border border-white/10 rounded-lg py-1.5 pl-8 pr-3 text-xs text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-all"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      const target = e.target as HTMLInputElement;
                      const query = target.value.trim();
                      if (query) {
                        setPendingQuery(query);
                        setActiveTab('research');
                        target.value = '';
                      }
                    }
                  }}
                />
              </div>
            }
            trailing={
              <div className="flex items-center gap-3 shrink-0">
                {currentTier === 'free' && (
                  <Link
                    href="/billing"
                    className="inline-flex min-h-9 items-center gap-2 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 px-4 text-xs font-semibold text-white transition hover:from-emerald-500 hover:to-teal-500 shadow-lg shadow-emerald-950/40"
                  >
                    <Sparkles className="h-3.5 w-3.5 text-emerald-100" />
                    <span className="hidden sm:inline tracking-wide">Upgrade</span>
                  </Link>
                )}
                <Link
                  href="/dashboard/data-trust"
                  className="inline-flex min-h-9 items-center gap-2 rounded-lg border border-white/15 bg-white/[0.04] px-3 text-xs font-semibold text-slate-200 transition hover:border-amber-400/45 hover:text-white"
                  title={`Data & Trust: ${healthSummary.label}. Last checked ${lastSuccessfulCheck || 'pending'}.`}
                >
                  <span className={`h-2 w-2 rounded-full ${statusDotClass(healthSummary.status)}`} aria-hidden="true" />
                  <span className="hidden md:inline">Data &amp; Trust</span>
                  <span className="hidden max-w-40 truncate font-normal text-slate-400 lg:inline">{healthSummary.label}</span>
                </Link>
                <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/15 bg-white/[0.04] hover:bg-white/10 transition-colors">
                  <LandingThemeToggle />
                </div>
              </div>
            }
          />

          <div className="flex overflow-hidden relative z-10 w-full" style={{ height: `calc(100vh - ${HEADER_HEIGHT}px)` }}>
            <div className="flex-1 min-w-0 h-full p-6 overflow-hidden">
              {activeTab === 'overview' ? (
                <div className="h-full w-full overflow-y-auto custom-scrollbar pr-1">
                  {renderOverview()}
                </div>
              ) : isCanvasOpen ? (
                <div className="flex h-full gap-4 relative">
                  <aside className="flex-1 h-full min-h-0" style={{ minWidth: CHAT_MIN_WIDTH }}>
                    <ChatWindow />
                  </aside>
                  
                  <div
                    onMouseDown={() => setIsResizingCanvas(true)}
                    className="cursor-col-resize self-stretch transition-all duration-150 relative z-20 flex-shrink-0 flex items-center justify-center group"
                    style={{ width: RESIZE_HANDLE_WIDTH }}
                    title="Drag to resize canvas"
                  >
                    <div className={`w-[2px] h-full transition-all duration-150 ${
                      isResizingCanvas ? 'bg-[#00FF9D]' : 'bg-[#222] group-hover:bg-[#00FF9D]/50'
                    }`} />

                    <div className={`absolute w-5 h-12 rounded-full border bg-[#111] flex flex-col gap-1 items-center justify-center shadow-lg transition-all duration-200 pointer-events-none ${
                      isResizingCanvas
                        ? 'border-[#00FF9D]/80 scale-105 opacity-100 shadow-[0_0_12px_rgba(102,163,255,0.3)]'
                        : 'border-[#222] opacity-40 group-hover:opacity-100 group-hover:border-[#00FF9D]/40'
                    }`}>
                      <div className="flex flex-col gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-400/80 group-hover:bg-[#00FF9D]" />
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-400/80 group-hover:bg-[#00FF9D]" />
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-400/80 group-hover:bg-[#00FF9D]" />
                      </div>
                    </div>
                  </div>

                  <main 
                    style={{ width: `${canvasWidth}px` }}
                    className="min-h-0 min-w-0 h-full overflow-y-auto rounded-[1.2rem] border border-[#222] bg-[#0a0a0a] p-6 flex-shrink-0 relative"
                  >
                    <button
                      onClick={() => { useCanvasStore.getState().closeCanvas(); }}
                      className="absolute top-4 right-4 p-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors z-50"
                    >
                      <X className="w-5 h-5" />
                    </button>
                    {renderCanvasContent()}
                  </main>
                </div>
              ) : (
                <div className="flex h-full w-full">
                    <ChatWindow />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </SidebarProvider>
  );
}
