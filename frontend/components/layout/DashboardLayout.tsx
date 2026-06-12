'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { motion, useReducedMotion } from 'framer-motion';
import {
  Bolt,
  ChartSpline,
  Clock3,
  Database,
  PanelLeftClose,
  PanelLeftOpen,
  PanelRightClose,
  PanelRightOpen,
  ShieldCheck,
  Sparkles,
  LayoutDashboard,
  Landmark,
  LineChart,
  Brain,
  Bell,
  Settings,
  Bot,
  Eye,
  Bookmark,
  AlertCircle,
  CheckCircle2,
  ArrowLeftRight,
  ArrowRight,
  Search,
  Send,
  PieChart,
  Wallet,
  TrendingUp,
  History,
  Check,
  X,
} from 'lucide-react';
import { useCanvasStore } from '@/store/useCanvasStore';
import { useChatStore, AssetType } from '@/store/useChatStore';
import UserProfileDropdown from '@/components/auth/UserProfileDropdown';
import ChatWindow from '@/components/chat/ChatWindow';
import StockDetailView from '@/components/canvas/StockDetailView';
import MFDetailView from '@/components/canvas/MFDetailView';
import ComparisonView from '@/components/canvas/ComparisonView';
import PortfolioReviewView from '@/components/canvas/PortfolioReviewView';
import CategoryCompareView from '@/components/canvas/CategoryCompareView';
import FundSearchSelect from '@/components/ui/FundSearchSelect';
import Magnetic from '@/components/ui/Magnetic';
import { supabaseBrowser } from '@/lib/supabaseBrowser';
import type { CategoryComparePayload, CategoryFundRow, SearchResultItem } from '@/types/funds';
import type { UserTier } from '@/lib/billing/tiers';

type DataHealthItem = {
  label: string;
  status: string;
  note?: string | null;
  last_updated?: string | null;
};

const DEFAULT_DATA_HEALTH: DataHealthItem[] = [
  { label: 'MF NAV', status: 'Checking' },
  { label: 'AUM / TER', status: 'Checking' },
  { label: 'Risk metrics', status: 'Checking' },
  { label: 'Factsheets', status: 'Checking' },
];

const HEADER_HEIGHT = 64;
const SIDEBAR_WIDTH = 276;
const MAIN_PADDING = 24;
const PANEL_GAP = 16;
const RESIZE_HANDLE_WIDTH = 12;
const CHAT_MIN_WIDTH = 320;
const CANVAS_MIN_WIDTH = 420;

const CATEGORY_CARDS = [
  { key: 'large_cap', title: 'Large Cap', desc: 'Top 100 companies', icon: Landmark },
  { key: 'mid_cap', title: 'Mid Cap', desc: 'High growth potential', icon: TrendingUp },
  { key: 'small_cap', title: 'Small Cap', desc: 'Aggressive growth', icon: ChartSpline },
  { key: 'flexi_cap', title: 'Flexi Cap', desc: 'Dynamic allocation', icon: PieChart },
  { key: 'index', title: 'Index Funds', desc: 'Low cost tracking', icon: Database },
  { key: 'elss', title: 'ELSS', desc: 'Tax saving funds', icon: ShieldCheck },
];

function statusColorClass(status: string): string {
  const normalized = (status || '').toLowerCase();
  if (['fresh', 'synced', 'ready', 'indexed'].includes(normalized)) return 'text-emerald-300';
  if (['lagging', 'partial', 'processing', 'checking'].includes(normalized)) return 'text-amber-300';
  if (['stale', 'missing', 'error'].includes(normalized)) return 'text-rose-300';
  return 'text-slate-300';
}

function CanvasPlaceholder() {
  return (
    <div className="flex h-full flex-col rounded-[1.35rem] border border-white/10 bg-[linear-gradient(160deg,rgba(15,23,42,0.95),rgba(2,8,24,0.98))] p-6 shadow-[0_20px_44px_rgba(0,0,0,0.35)]">
      <div>
        <h2 className="text-3xl font-semibold tracking-tight text-white">Comparison canvas</h2>
        <p className="mt-1 text-sm text-slate-300">Ask FundersAI to compare two funds to open side-by-side metrics here.</p>
        <span className="mt-4 inline-flex rounded-full border border-[#66a3ff]/30 bg-[#66a3ff]/10 px-3 py-1 text-xs text-[#66a3ff]">
          Waiting for comparison
        </span>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-4">
        {[
          { label: 'Returns', value: 'Side-by-side', note: '1Y, 3Y, 5Y' },
          { label: 'Risk', value: 'Side-by-side', note: 'Volatility, drawdown, Sharpe' },
          { label: 'Costs', value: 'Side-by-side', note: 'Expense ratio and AUM' },
          { label: 'Data', value: 'Side-by-side', note: 'NAV date and coverage' },
        ].map((item) => (
          <div key={item.label} className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs text-slate-300">{item.label}</p>
            <p className="mt-2 text-lg font-semibold tracking-tight text-white">{item.value}</p>
            <p className="mt-1 text-xs text-slate-400">{item.note}</p>
          </div>
        ))}
      </div>

      <div className="mt-5 flex-1 rounded-[1.2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(0,80,158,0.15),rgba(15,23,42,0.25))] p-4">
        <svg viewBox="0 0 700 260" className="h-full w-full" aria-hidden>
          <path d="M30 210 C110 180, 150 192, 220 160 C270 138, 300 150, 360 122 C410 98, 450 112, 510 86 C560 66, 620 82, 670 72" fill="none" stroke="#66a3ff" strokeWidth="4" strokeLinecap="round"/>
          <path d="M30 224 C105 202, 150 198, 220 188 C280 178, 310 166, 360 172 C412 178, 455 144, 510 150 C560 156, 620 126, 670 132" fill="none" stroke="#007acc" strokeWidth="3" strokeLinecap="round"/>
        </svg>
      </div>
    </div>
  );
}

function SidebarContent({
  activeTab,
  setActiveTab,
  dataHealth,
  healthCheckedAt,
  currentTier,
}: {
  activeTab: 'overview' | 'research' | 'ai_research';
  setActiveTab: (tab: 'overview' | 'research' | 'ai_research') => void;
  dataHealth: DataHealthItem[];
  healthCheckedAt: string | null;
  currentTier: UserTier;
}) {
  const assetType = useChatStore((state) => state.assetType);
  const setAssetType = useChatStore((state) => state.setAssetType);

  const navItems = [
    {
      id: 'overview',
      label: 'Overview',
      icon: LayoutDashboard,
      isActive: activeTab === 'overview',
      onClick: () => setActiveTab('overview'),
    },
    {
      id: 'mutual_funds',
      label: 'Mutual Funds',
      icon: Landmark,
      isActive: activeTab === 'research' && assetType === 'mutual_fund',
      onClick: () => {
        setActiveTab('research');
        setAssetType('mutual_fund');
      },
    },
    {
      id: 'stocks',
      label: 'Stocks',
      icon: LineChart,
      isActive: activeTab === 'research' && assetType === 'stock',
      onClick: () => {
        setActiveTab('research');
        setAssetType('stock');
      },
    },
    {
      id: 'ai_research',
      label: 'AI Research',
      icon: Brain,
      isActive: activeTab === 'ai_research',
      onClick: () => {
        setActiveTab('ai_research');
        setAssetType('auto');
      },
    },
  ];

  return (
    <div className="flex h-full flex-col rounded-[1.2rem] border border-white/10 bg-[#07111f] p-5 shadow-[0_20px_42px_rgba(0,0,0,0.4)]">
      <div>
        <div className="flex flex-col gap-1 items-start">
          <img src="/FUNDERSAI-vertical.png" alt="FundersAI Logo" className="h-8 w-auto object-contain origin-left" />
          <p className="text-[11px] uppercase tracking-[0.14em] text-slate-400 pl-1">Research terminal</p>
        </div>
      </div>

      {/* Navigation menu */}
      <div className="mt-6 flex-1 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              onClick={item.onClick}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-[13px] font-medium transition-all ${
                item.isActive
                  ? 'text-white font-bold border-r-2 border-[#66a3ff] bg-white/5'
                  : 'text-slate-400 hover:bg-white/5 hover:text-white'
              }`}
            >
              <Icon className="h-[18px] w-[18px] shrink-0" />
              <span>{item.label}</span>
            </button>
          );
        })}

        {/* Dynamic Pipelines & Data Health Info sections, merged neatly under the navigation */}
        <div className="mt-6 border-t border-white/5 pt-4">
          <p className="text-[11px] uppercase tracking-[0.16em] text-slate-400 font-semibold">Pipelines</p>
          <div className="mt-2.5 space-y-2">
            <div className="flex items-center gap-2 text-xs text-slate-300">
              <ChartSpline className="h-3.5 w-3.5 text-[#66a3ff] shrink-0" />
              <span>Quant + comparison</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-300">
              <Database className="h-3.5 w-3.5 text-[#007acc] shrink-0" />
              <span>Supabase-first data</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-300">
              <ShieldCheck className="h-3.5 w-3.5 text-slate-400 shrink-0" />
              <span>Research guardrails</span>
            </div>
          </div>
        </div>

        <div className="mt-4 border-t border-white/5 pt-4">
          <p className="text-[11px] uppercase tracking-[0.16em] text-slate-400 font-semibold">Data health</p>
          <div className="mt-2.5 space-y-2">
            {dataHealth.slice(0, 3).map(({ label, status, note }) => (
              <div key={label} className="rounded-lg border border-white/5 bg-white/[0.045] backdrop-blur-md shadow-[0_24px_90px_rgba(0,0,0,0.18)]/70 px-2.5 py-1.5 text-[11px]">
                <div className="flex items-center justify-between">
                  <span className="text-slate-400" title={note || ''}>{label}</span>
                  <span className={`font-semibold ${statusColorClass(status)}`} title={note || ''}>{status}</span>
                </div>
              </div>
            ))}
          </div>
          {healthCheckedAt && (
            <p className="mt-2 text-[9px] text-slate-500">
              Checked {new Date(healthCheckedAt).toLocaleString('en-IN', { hour12: false })}
            </p>
          )}
        </div>
      </div>

      <div className="mt-auto pt-4 border-t border-white/10 space-y-3">
        <UserProfileDropdown currentTier={currentTier} />
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
  const searchParams = useSearchParams();
  const { activeView, selectedIds, auxiliaryData, isCanvasOpen, toggleCanvas, comparisonMode } = useCanvasStore();
  const [isMobile, setIsMobile] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [canvasWidth, setCanvasWidth] = useState(640);
  const [isResizingCanvas, setIsResizingCanvas] = useState(false);
  const [dataHealth, setDataHealth] = useState<DataHealthItem[]>(DEFAULT_DATA_HEALTH);
  const [healthCheckedAt, setHealthCheckedAt] = useState<string | null>(null);
  
  const initialTab = (searchParams?.get('tab') as 'overview' | 'research' | 'ai_research') || 'overview';
  const [activeTab, setActiveTab] = useState<'overview' | 'research' | 'ai_research'>(initialTab);
  const [compareFund1, setCompareFund1] = useState<SearchResultItem | null>(null);
  const [compareFund2, setCompareFund2] = useState<SearchResultItem | null>(null);
  const [assistantInput, setAssistantInput] = useState('');
  const [currentTier, setCurrentTier] = useState<UserTier>('free');
  const [activeCategory, setActiveCategory] = useState<string | null>(null);
  const [categoryFunds, setCategoryFunds] = useState<CategoryFundRow[]>([]);
  const [categoryLoading, setCategoryLoading] = useState(false);
  const [categoryError, setCategoryError] = useState<string | null>(null);
  const [selectedCategoryCodes, setSelectedCategoryCodes] = useState<string[]>([]);
  const [categoryCompare, setCategoryCompare] = useState<CategoryComparePayload | null>(null);
  const [categoryCompareLoading, setCategoryCompareLoading] = useState(false);
  const [categoryCompareError, setCategoryCompareError] = useState<string | null>(null);
  const setPendingQuery = useChatStore((state) => state.setPendingQuery);
  const navStatus = dataHealth.find((item) => item.label === 'MF NAV')?.status || 'Checking';
  const getCanvasBounds = () => {
    const sidebarWidth = !isSidebarCollapsed ? SIDEBAR_WIDTH : 0;
    const shellPadding = MAIN_PADDING * 2;
    const splitChrome = (PANEL_GAP * 2) + RESIZE_HANDLE_WIDTH;
    const availableWidth = window.innerWidth - sidebarWidth - shellPadding;
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
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    let ignore = false;

    const loadDataHealth = async () => {
      try {
        const res = await fetch('/api/data-health', { cache: 'no-store' });
        if (!res.ok) {
          if (!ignore) {
            setDataHealth((current) => current.map((item) => ({ ...item, status: 'Error', note: 'Data health request failed.' })));
          }
          return;
        }

        const payload = await res.json();
        const incoming = Array.isArray(payload?.metrics) ? payload.metrics : [];
        const byLabel = new Map(incoming.map((item: DataHealthItem) => [item.label, item]));
        if (!ignore) {
          setDataHealth(
            DEFAULT_DATA_HEALTH.map((item) => {
              const next = byLabel.get(item.label);
              return next ? { ...item, ...next } : item;
            }),
          );
          setHealthCheckedAt(typeof payload?.checked_at === 'string' ? payload.checked_at : new Date().toISOString());
        }
      } catch {
        if (!ignore) {
          setDataHealth((current) => current.map((item) => ({ ...item, status: 'Error', note: 'Data health request failed.' })));
        }
      }
    };

    loadDataHealth();
    const timer = window.setInterval(loadDataHealth, 120000);

    return () => {
      ignore = true;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    const query = window.matchMedia('(max-width: 1100px)');
    const update = () => {
      const nextIsMobile = query.matches;
      setIsMobile(nextIsMobile);
      if (nextIsMobile) {
        setIsMobileSidebarOpen(false);
      }
    };
    update();
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
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

  const formatPercent = (value: unknown) => {
    const num = Number(value);
    return Number.isFinite(num) ? `${num.toFixed(2)}%` : 'N/A';
  };

  const formatAum = (value: unknown) => {
    const num = Number(value);
    return Number.isFinite(num) ? `INR ${Math.round(num).toLocaleString('en-IN')}` : 'N/A';
  };

  const formatRiskLabel = (value: unknown) => {
    const label = typeof value === 'string' ? value.trim() : '';
    return label || 'Coverage pending';
  };

  const compactFundName = (value: unknown) => String(value || 'N/A')
    .replace(/\s*-\s*Direct Plan\s*-\s*Growth/gi, '')
    .replace(/\s*Direct\s*Growth/gi, '')
    .trim();

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
    const { setView, setIds, openCanvas } = useCanvasStore.getState();
    setIds(selectedCategoryCodes);
    setView('COMPARISON');
    openCanvas();
    setActiveTab('research');

    // Still send a background query for context if needed, but it won't block UI
    const names = categoryCompare.selected_funds.map((fund) => compactFundName(fund.scheme_name));
    const last = names.pop();
    const joined = names.length ? `${names.join(', ')} and ${last}` : last;
    setPendingQuery(`Compare ${joined} from the ${categoryCompare.category} bucket.`);
  };

  const renderOverview = () => {
    return (
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h2 className="font-serif text-3xl font-semibold text-white tracking-tight">What can I safely do here?</h2>
            <p className="font-body-sm text-[14px] text-slate-400 mt-1 max-w-2xl">
              Compare verified funds, ask source-backed research questions, and review portfolio structure without advisory output.
            </p>
          </div>
        </div>

        {/* Main Action Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div
            onClick={() => handleOverviewQuery('Compare PPFAS Flexi Cap and HDFC Flexi Cap')}
            className="bg-white/[0.045] backdrop-blur-md shadow-[0_24px_90px_rgba(0,0,0,0.18)] border border-white/10 p-6 rounded-xl hover:border-[#66a3ff]/40 transition-colors cursor-pointer group shadow-lg"
          >
            <div className="w-10 h-10 rounded-lg bg-[#66a3ff]/10 flex items-center justify-center mb-4 group-hover:bg-[#66a3ff]/20 transition-colors">
              <ArrowLeftRight className="text-[#66a3ff] h-5 w-5" />
            </div>
            <h3 className="font-serif text-lg font-medium text-white mb-2">Compare Funds</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Compare returns, risk, expense ratio, AUM, fund category, and consistency side-by-side.
            </p>
            <p className="mt-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#8ea7cd]">Comparison only, not advice</p>
          </div>

          <div
            onClick={() => setActiveTab('research')}
            className="bg-white/[0.045] backdrop-blur-md shadow-[0_24px_90px_rgba(0,0,0,0.18)] border border-[#66a3ff]/20 p-6 rounded-xl hover:border-[#66a3ff]/60 transition-colors cursor-pointer group relative overflow-hidden shadow-lg"
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-[#66a3ff]/5 rounded-full blur-3xl pointer-events-none"></div>
            <div className="w-10 h-10 rounded-lg bg-[#66a3ff]/20 flex items-center justify-center mb-4 group-hover:bg-[#66a3ff]/30 transition-colors relative z-10">
              <Brain className="text-[#66a3ff] h-5 w-5" />
            </div>
            <h3 className="font-serif text-lg font-medium text-white mb-2 relative z-10">Ask Research Question</h3>
            <p className="text-sm text-slate-400 leading-relaxed relative z-10">
              Ask FundersAI to explain funds, compare strategies, or simplify complex fund data.
            </p>
            <p className="mt-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#8ea7cd] relative z-10">Source-backed explanation, not a recommendation</p>
          </div>

          <div
            onClick={() => handleOverviewQuery('Review my portfolio diversification')}
            className="bg-white/[0.045] backdrop-blur-md shadow-[0_24px_90px_rgba(0,0,0,0.18)] border border-white/10 p-6 rounded-xl hover:border-[#66a3ff]/40 transition-colors cursor-pointer group shadow-lg"
          >
            <div className="w-10 h-10 rounded-lg bg-[#66a3ff]/10 flex items-center justify-center mb-4 group-hover:bg-[#66a3ff]/20 transition-colors">
              <Wallet className="text-[#66a3ff] h-5 w-5" />
            </div>
            <h3 className="font-serif text-lg font-medium text-white mb-2">Portfolio Review</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Review holdings structure, concentration, and diversification signals.
            </p>
            <p className="mt-3 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#8ea7cd]">Diversification read, not portfolio advice</p>
          </div>
        </div>

        {/* Two Column Layout for the rest */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Left Column (Wider) */}
          <div className="xl:col-span-2 space-y-6">
            
            {/* Quick Compare Widget */}
            <div className="relative z-30 bg-white/[0.045] backdrop-blur-md shadow-[0_24px_90px_rgba(0,0,0,0.18)] border border-white/10 rounded-xl p-6 shadow-lg">
              <div className="flex items-center gap-2 mb-4">
                <ArrowLeftRight className="text-[#66a3ff] h-5 w-5" />
                <h3 className="font-serif text-xl font-medium text-white">Quick Compare</h3>
              </div>
              <div className="flex flex-col sm:flex-row gap-3 items-center">
                <div className="flex-1 w-full relative">
                  <FundSearchSelect
                    placeholder="Search Fund 1..."
                    onSelect={setCompareFund1}
                  />
                  {compareFund1 && (
                    <div className="absolute top-full mt-1 left-0 right-0 z-10 px-2 py-1 bg-[#1a2333] border border-emerald-500/30 rounded text-xs text-emerald-200">
                      Selected: {compareFund1.displayName}
                    </div>
                  )}
                </div>
                <div className="text-slate-500 font-medium font-serif-display px-2 text-sm">VS</div>
                <div className="flex-1 w-full relative">
                  <FundSearchSelect
                    placeholder="Search Fund 2..."
                    onSelect={setCompareFund2}
                  />
                  {compareFund2 && (
                    <div className="absolute top-full mt-1 left-0 right-0 z-10 px-2 py-1 bg-[#1a2333] border border-emerald-500/30 rounded text-xs text-emerald-200">
                      Selected: {compareFund2.displayName}
                    </div>
                  )}
                </div>
                <button
                  onClick={() => {
                    if (compareFund1 && compareFund2) {
                      const { setView, setIds, openCanvas } = useCanvasStore.getState();
                      setIds([compareFund1.id, compareFund2.id]);
                      setView('COMPARISON');
                      openCanvas();
                      setActiveTab('research');
                      setPendingQuery(`Compare ${compareFund1.displayName} and ${compareFund2.displayName}`);
                    }
                  }}
                  disabled={!compareFund1 || !compareFund2}
                  className="w-full sm:w-auto px-6 py-2.5 bg-[#66a3ff] text-slate-950 rounded-lg font-medium text-sm hover:bg-[#66a3ff]/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-4 sm:mt-0"
                >
                  Compare Now
                </button>
              </div>
            </div>

            {/* Market / Category Snapshot */}
            <div className="relative z-0">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <h3 className="font-serif text-xl font-medium text-white">Explore Categories</h3>
                  <p className="mt-1 text-xs text-slate-400">List funds by bucket, select 2-3 supported funds, then compare metrics and portfolios.</p>
                </div>
                {selectedCategoryCodes.length > 0 && (
                  <span className="rounded-full border border-[#66a3ff]/25 bg-[#66a3ff]/10 px-3 py-1 text-xs text-[#cce0ff]">
                    {selectedCategoryCodes.length}/3 selected
                  </span>
                )}
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {CATEGORY_CARDS.map((cat) => {
                  const CatIcon = cat.icon;
                  return (
                    <button
                      type="button"
                      key={cat.key}
                      onClick={() => loadCategoryFunds(cat.key)}
                      className={`text-left bg-white/[0.045] backdrop-blur-md shadow-[0_24px_90px_rgba(0,0,0,0.18)] border rounded-lg p-4 transition-all cursor-pointer group shadow-sm ${
                        activeCategory === cat.key
                          ? 'border-[#66a3ff]/60 bg-[#66a3ff]/10 shadow-[0_4px_16px_rgba(102,163,255,0.15)]'
                          : 'border-white/10 hover:border-[#66a3ff]/30 hover:bg-[#1a2333]'
                      }`}
                    >
                      <CatIcon className="text-[#66a3ff] h-4 w-4 mb-2 opacity-80 group-hover:opacity-100 transition-opacity" />
                      <div className="text-sm font-medium text-white mb-0.5">{cat.title}</div>
                      <div className="text-[11px] text-slate-400">{cat.desc}</div>
                    </button>
                  );
                })}
              </div>

              {activeCategory && (
                <div className="mt-4 rounded-xl border border-white/10 bg-[#101827]/70 p-4">
                  <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <h4 className="text-sm font-semibold text-white">
                        {CATEGORY_CARDS.find((item) => item.key === activeCategory)?.title || 'Category'} funds
                      </h4>
                      <p className="mt-1 text-xs text-slate-400">Unsupported AMCs are visible but disabled until their pipeline is ready.</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        onClick={compareSelectedCategoryFunds}
                        disabled={selectedCategoryCodes.length < 2 || selectedCategoryCodes.length > 3 || categoryCompareLoading}
                        className="rounded-lg bg-[#66a3ff] px-3 py-1.5 text-xs font-semibold text-slate-950 transition hover:bg-[#66a3ff]/85 disabled:cursor-not-allowed disabled:opacity-50"
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
                        className="rounded-lg border border-white/10 bg-white/[0.04] px-3 py-1.5 text-xs font-semibold text-slate-200 transition hover:border-[#66a3ff]/40 disabled:cursor-not-allowed disabled:opacity-40"
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
                                        ? 'border-[#66a3ff] bg-[#66a3ff] text-slate-950'
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
                                <td className="px-3 py-3">{fund.amc_name || 'N/A'}</td>
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
                    <div className="mt-4 rounded-xl border border-[#66a3ff]/20 bg-[#66a3ff]/[0.06] p-4">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div>
                          <h4 className="text-sm font-semibold text-white">{categoryCompare.category} comparison ready</h4>
                          <p className="mt-1 text-xs text-slate-300">{categoryCompare.insights?.headline || categoryCompare.research_note}</p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            onClick={useCategoryCompareInChat}
                            className="rounded-lg bg-[#66a3ff] px-3 py-1.5 text-xs font-semibold text-slate-950 transition hover:bg-[#66a3ff]/85"
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

          {/* Right Column (Narrower) */}
          <div className="space-y-6">
            
            {/* Beginner Tools Placeholder */}
            <div className="bg-white/[0.045] backdrop-blur-md shadow-[0_24px_90px_rgba(0,0,0,0.18)] border border-white/10 rounded-xl p-6 shadow-lg">
              <h3 className="font-serif text-lg font-medium text-white mb-4">Investor Tools</h3>
              <div className="space-y-2">
                <Link href="/dashboard/sip-calculator" className="w-full text-left p-3 rounded-lg border border-white/10 bg-black/20 hover:bg-[#66a3ff]/10 hover:border-[#66a3ff]/30 transition-all cursor-pointer flex items-center justify-between group">
                  <div>
                    <div className="text-[13px] font-medium text-white">SIP Calculator</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">Estimate SIP outcomes</div>
                  </div>
                  <ArrowRight className="h-4 w-4 text-slate-500 group-hover:text-[#66a3ff] transition-colors" />
                </Link>
                <Link href="/dashboard/risk-quiz" className="w-full text-left p-3 rounded-lg border border-white/10 bg-black/20 hover:bg-[#66a3ff]/10 hover:border-[#66a3ff]/30 transition-all cursor-pointer flex items-center justify-between group">
                  <div>
                    <div className="text-[13px] font-medium text-white">Risk Quiz</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">Understand risk profile</div>
                  </div>
                  <ArrowRight className="h-4 w-4 text-slate-500 group-hover:text-[#66a3ff] transition-colors" />
                </Link>
              </div>
            </div>

            {/* Recent Activity */}
            <div className="bg-white/[0.045] backdrop-blur-md shadow-[0_24px_90px_rgba(0,0,0,0.18)] border border-white/10 rounded-xl p-6 shadow-lg">
              <h3 className="font-serif text-lg font-medium text-white mb-4">Recent Activity</h3>
              <div className="space-y-3">
                <div onClick={() => handleOverviewQuery('Analyze Parag Parikh Flexi Cap Fund')} className="flex items-center gap-3 cursor-pointer group">
                  <div className="w-8 h-8 rounded bg-[#111] border border-[#222] flex items-center justify-center shrink-0">
                    <History className="h-3.5 w-3.5 text-slate-400" />
                  </div>
                  <div>
                    <div className="text-[12px] font-medium text-white group-hover:text-[#66a3ff] transition-colors">Parag Parikh Flexi Cap</div>
                    <div className="text-[10px] text-slate-500">Viewed 2h ago</div>
                  </div>
                </div>
                <div onClick={() => handleOverviewQuery('Compare Nifty 50 vs Next 50')} className="flex items-center gap-3 cursor-pointer group">
                  <div className="w-8 h-8 rounded bg-[#111] border border-[#222] flex items-center justify-center shrink-0">
                    <History className="h-3.5 w-3.5 text-slate-400" />
                  </div>
                  <div>
                    <div className="text-[12px] font-medium text-white group-hover:text-[#66a3ff] transition-colors">Nifty 50 vs Next 50</div>
                    <div className="text-[10px] text-slate-500">Compared yesterday</div>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>

        {/* Disclaimer Footer */}
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
            ids={selectedIds}
            type={selectedIds[0]?.match(/^[0-9]+$/) ? 'MUTUAL_FUND' : 'STOCK'}
            auxiliaryData={auxiliaryData}
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
    <div className="relative h-screen w-screen overflow-hidden bg-[#050A15] text-[#e8f0ff] flex flex-col selection:bg-[#66a3ff]/30 selection:text-white">
      <FineGrid />
      <div className="pointer-events-none absolute inset-0 z-0 bg-[radial-gradient(circle_at_50%_0%,rgba(102,163,255,0.06),transparent_65%)]" />

      <div className="relative z-10 flex flex-col flex-1 h-full w-full overflow-hidden border border-white/10 bg-transparent shadow-[0_28px_80px_rgba(0,0,0,0.5)]">
        <header className="h-16 shrink-0 flex items-center justify-between border-b border-white/10 px-4 sm:px-6">
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-white/15 bg-white/[0.04] text-slate-200 transition hover:border-[#66a3ff]/50 hover:text-white"
              onClick={() => {
                if (isMobile) {
                  setIsMobileSidebarOpen((value) => !value);
                  return;
                }
                setIsSidebarCollapsed((value) => !value);
              }}
              aria-label={isMobile ? 'Toggle sidebar menu' : 'Collapse sidebar'}
            >
              {isMobile || isSidebarCollapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
            </button>
            <div className="hidden sm:flex items-center gap-3">
              <Image src="/FUNDERSAI-nobackground.png" alt="FundersAI Logo" width={28} height={28} className="object-contain" />
              <div>
                <p className="text-sm font-semibold text-white">FundersAI Research</p>
                <p className="text-xs text-slate-400">Centered chat + optional canvas</p>
              </div>
            </div>
          </div>

          <div className="hidden relative max-w-xs w-full sm:block">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 h-3.5 w-3.5" />
            <input
              type="text"
              placeholder="Search tickers, funds, research..."
              className="w-full bg-black/20 border border-white/10 rounded-lg py-1.5 pl-8 pr-3 text-xs text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-[#66a3ff]/50 focus:border-[#66a3ff]/50 transition-all"
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

          <div className="flex items-center gap-2">
            {activeTab === 'research' && (
              <button
                type="button"
                className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition ${
                  isCanvasOpen
                    ? 'border-[#66a3ff]/35 bg-[#66a3ff]/12 text-[#cce0ff]'
                    : 'border-white/15 bg-white/[0.04] text-slate-200 hover:border-[#66a3ff]/45 hover:text-white'
                }`}
                onClick={toggleCanvas}
              >
                {isCanvasOpen ? <PanelRightClose className="h-3.5 w-3.5" /> : <PanelRightOpen className="h-3.5 w-3.5" />}
                Canvas
              </button>
            )}
            <div className="hidden items-center gap-1.5 text-xs font-medium text-emerald-300 sm:flex">
              <Clock3 className="h-3.5 w-3.5" />
              <span className={statusColorClass(navStatus)}>MF NAV {navStatus}</span>
            </div>
          </div>
        </header>

        <div className="flex overflow-hidden relative z-10 w-full" style={{ height: `calc(100vh - ${HEADER_HEIGHT}px)` }}>
          {!isMobile && !isSidebarCollapsed && (
            <aside className="w-[276px] shrink-0 border-r border-white/10 bg-[#0b1526]/72 p-4 min-h-0 h-full overflow-y-auto">
              <SidebarContent
                activeTab={activeTab}
                setActiveTab={setActiveTab}
                dataHealth={dataHealth}
                healthCheckedAt={healthCheckedAt}
                currentTier={currentTier}
              />
            </aside>
          )}

          <div className="flex-1 min-w-0 h-full p-6 overflow-hidden">
            {activeTab === 'overview' ? (
              <div className="h-full w-full overflow-y-auto custom-scrollbar pr-1">
                {renderOverview()}
              </div>
            ) : activeTab === 'ai_research' ? (
              <div className="flex h-full items-center justify-center w-full relative">
                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(102,163,255,0.05),transparent_50%)] pointer-events-none" />
                <div className="h-full w-full max-w-[800px] min-h-0 pt-4 pb-0 relative z-10">
                  <ChatWindow isFullScreen={true} />
                </div>
              </div>
            ) : isMobile ? (
              <div className="flex h-full flex-col gap-4 overflow-y-auto">
                <div className="h-[450px] shrink-0 min-h-0">
                  <ChatWindow />
                </div>
                {isCanvasOpen && (
                  <section className="flex-1 min-h-[420px] rounded-[1.2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.85),rgba(2,6,23,0.9))] p-4">
                    {renderCanvasContent()}
                  </section>
                )}
              </div>
            ) : isCanvasOpen ? (
              <div className="flex h-full gap-4 relative">
                {comparisonMode === 'llm' && (
                  <aside className="flex-1 h-full min-h-0" style={{ minWidth: CHAT_MIN_WIDTH }}>
                    <ChatWindow />
                  </aside>
                )}
                
                {/* Drag handle styled like Gemini's canvas handle */}
                {comparisonMode === 'llm' && (
                  <div
                    onMouseDown={() => setIsResizingCanvas(true)}
                    className="cursor-col-resize self-stretch transition-all duration-150 relative z-20 flex-shrink-0 flex items-center justify-center group"
                    style={{ width: RESIZE_HANDLE_WIDTH }}
                    title="Drag to resize canvas"
                  >
                    {/* Central divider line */}
                    <div className={`w-[2px] h-full transition-all duration-150 ${
                      isResizingCanvas ? 'bg-[#66a3ff]' : 'bg-[#222] group-hover:bg-[#66a3ff]/50'
                    }`} />

                    {/* Glassmorphic Capsule Handle - removed blur */}
                    <div className={`absolute w-5 h-12 rounded-full border bg-[#111] flex flex-col gap-1 items-center justify-center shadow-lg transition-all duration-200 pointer-events-none ${
                      isResizingCanvas
                        ? 'border-[#66a3ff]/80 scale-105 opacity-100 shadow-[0_0_12px_rgba(102,163,255,0.3)]'
                        : 'border-[#222] opacity-40 group-hover:opacity-100 group-hover:border-[#66a3ff]/40'
                    }`}>
                      {/* Vertical grip dots */}
                      <div className="flex flex-col gap-1">
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-400/80 group-hover:bg-[#66a3ff]" />
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-400/80 group-hover:bg-[#66a3ff]" />
                        <span className="w-1.5 h-1.5 rounded-full bg-slate-400/80 group-hover:bg-[#66a3ff]" />
                      </div>
                    </div>
                  </div>
                )}

                <main 
                  style={{ width: comparisonMode === 'llm' ? `${canvasWidth}px` : '100%' }}
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
              <div className="flex h-full items-center justify-center">
                <div className="h-full w-full max-w-[680px] min-h-0">
                  <ChatWindow />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {isMobile && isMobileSidebarOpen && (
        <div
          role="button"
          tabIndex={-1}
          aria-label="Close sidebar menu"
          className="fixed inset-0 z-50 bg-black/50 lg:hidden cursor-default"
          onClick={() => setIsMobileSidebarOpen(false)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' || event.key === ' ') {
              setIsMobileSidebarOpen(false);
            }
          }}
        >
          <aside
            className="h-full w-[290px] border-r border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.95),rgba(2,8,24,0.96))] p-4"
            onClick={(event) => event.stopPropagation()}
          >
            <SidebarContent
              activeTab={activeTab}
              setActiveTab={setActiveTab}
              dataHealth={dataHealth}
              healthCheckedAt={healthCheckedAt}
              currentTier={currentTier}
            />
          </aside>
        </div>
      )}
    </div>
  );
}
