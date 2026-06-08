'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
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
} from 'lucide-react';
import { useCanvasStore } from '@/store/useCanvasStore';
import { useChatStore, AssetType } from '@/store/useChatStore';
import SignOutButton from '@/components/auth/SignOutButton';
import ChatWindow from '@/components/chat/ChatWindow';
import StockDetailView from '@/components/canvas/StockDetailView';
import MFDetailView from '@/components/canvas/MFDetailView';
import ComparisonView from '@/components/canvas/ComparisonView';
import Magnetic from '@/components/ui/Magnetic';
import { supabaseBrowser } from '@/lib/supabaseBrowser';
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

function statusColorClass(status: string): string {
  const normalized = (status || '').toLowerCase();
  if (['fresh', 'synced', 'ready', 'indexed'].includes(normalized)) return 'text-emerald-300';
  if (['lagging', 'partial', 'processing', 'checking'].includes(normalized)) return 'text-amber-300';
  if (['stale', 'missing', 'error'].includes(normalized)) return 'text-rose-300';
  return 'text-slate-300';
}

function CanvasPlaceholder() {
  return (
    <div className="flex h-full flex-col rounded-[1.35rem] border border-white/10 bg-[linear-gradient(160deg,rgba(15,23,42,0.82),rgba(2,8,24,0.9))] p-5 shadow-[0_20px_44px_rgba(0,0,0,0.35)] backdrop-blur-xl">
      <div>
        <h2 className="text-3xl font-semibold tracking-tight text-white">Fund comparison canvas</h2>
        <p className="mt-1 text-sm text-slate-300">Parag Parikh Flexi Cap vs ICICI Multi Asset Fund</p>
        <span className="mt-4 inline-flex rounded-full border border-[#66a3ff]/30 bg-[#66a3ff]/10 px-3 py-1 text-xs text-[#66a3ff]">
          Side-by-side
        </span>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-4">
        {[
          { label: '3Y Return', value: '+18.6%', note: 'Performance' },
          { label: 'Expense Ratio', value: '0.63%', note: 'Risk-Cost' },
          { label: 'Sharpe', value: '1.12', note: 'Risk-adjusted' },
          { label: 'Coverage', value: 'PPFAS + ICICI', note: 'Current pipeline' },
        ].map((item) => (
          <div key={item.label} className="rounded-xl border border-white/10 bg-white/[0.04] p-4">
            <p className="text-xs text-slate-300">{item.label}</p>
            <p className="mt-2 text-3xl font-semibold tracking-tight text-white">{item.value}</p>
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
  activeTab: 'overview' | 'research';
  setActiveTab: (tab: 'overview' | 'research') => void;
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
      id: 'research',
      label: 'AI Research',
      icon: Brain,
      isActive: activeTab === 'research' && assetType === 'auto',
      onClick: () => {
        setActiveTab('research');
        setAssetType('auto');
      },
    },
  ];

  return (
    <div className="flex h-full flex-col rounded-[1.2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.92),rgba(2,8,24,0.94))] p-4 shadow-[0_20px_42px_rgba(0,0,0,0.4)] backdrop-blur-xl">
      <div>
        <div className="flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-[linear-gradient(135deg,#67b2ff,#3b82f6)] text-white shadow-[0_8px_18px_rgba(59,130,246,0.38)]">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-white">FundersAI</h1>
            <p className="text-[11px] uppercase tracking-[0.14em] text-slate-400">Research terminal</p>
          </div>
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
              <div key={label} className="rounded-lg border border-white/5 bg-[#0f172a]/70 px-2.5 py-1.5 text-[11px]">
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
        <Link
          href="/billing"
          className="flex items-center justify-between rounded-xl border border-[#66a3ff]/25 bg-[#66a3ff]/10 px-3 py-2 text-xs text-[#cce0ff] transition hover:border-[#66a3ff]/50 hover:bg-[#66a3ff]/15"
        >
          <span>Current tier</span>
          <span className="font-semibold uppercase">{currentTier}</span>
        </Link>
        <div className="flex items-center justify-between px-2">
          <div className="flex items-center gap-2.5">
            <img
              alt="User Profile"
              className="w-7 h-7 rounded-full border border-white/20"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuC2yc-OZ72YKCNRfbOXvs1JmLKZ8WsL1I4VdXs7ay-q-nGiubYiIDIn5X-U2JM7CUVh4ez21gIRIi88QOJbY2MGm4mxh4VKFl3jfsj00Xu-2wkZyL8elq700xoxfN8ggkPtWyu1QMLbXeSfy4p5SePZGFHluNczs4uCQdnfoc3hLiJXqSIUeyAVFOLC_g-dgN5Vua1TH3ooT3QW6lOXjtHGvBH_ktSxj7IoGj7WqZ3yR_GOcOkozqObt4umNwUzkBPsvUJlmwlhVp5f"
            />
            <span className="text-xs text-slate-300 font-medium">Reaper</span>
          </div>
          <SignOutButton />
        </div>
      </div>
    </div>
  );
}

export default function DashboardLayout() {
  const searchParams = useSearchParams();
  const { activeView, selectedIds, auxiliaryData, isCanvasOpen, toggleCanvas } = useCanvasStore();
  const [isMobile, setIsMobile] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [canvasWidth, setCanvasWidth] = useState(640);
  const [isResizingCanvas, setIsResizingCanvas] = useState(false);
  const [dataHealth, setDataHealth] = useState<DataHealthItem[]>(DEFAULT_DATA_HEALTH);
  const [healthCheckedAt, setHealthCheckedAt] = useState<string | null>(null);
  
  const initialTab = (searchParams?.get('tab') as 'overview' | 'research') || 'overview';
  const [activeTab, setActiveTab] = useState<'overview' | 'research'>(initialTab);
  const [compareFund1, setCompareFund1] = useState('');
  const [compareFund2, setCompareFund2] = useState('');
  const [assistantInput, setAssistantInput] = useState('');
  const [currentTier, setCurrentTier] = useState<UserTier>('free');
  const setPendingQuery = useChatStore((state) => state.setPendingQuery);
  const navStatus = dataHealth.find((item) => item.label === 'MF NAV')?.status || 'Checking';
  const getCanvasBounds = () => {
    const min = 420;
    const sidebarWidth = !isSidebarCollapsed ? 276 : 0;
    const paddingAndGap = 48; // p-6 on main container
    const availableWidth = window.innerWidth - sidebarWidth - paddingAndGap;
    // Chat window min width is 320px, and gap is 16px. So max canvas width is availableWidth - 336px
    const max = Math.max(availableWidth - 336, min);
    return { min, max };
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
      const rightPadding = 24; // p-6 is 24px padding on the right edge
      const next = window.innerWidth - rightPadding - event.clientX;
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

  const renderOverview = () => {
    return (
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-6">
          <div>
            <h2 className="font-serif text-3xl font-semibold text-white tracking-tight">Welcome to MarketMind</h2>
            <p className="font-body-sm text-[14px] text-slate-400 mt-1 max-w-2xl">
              Understand, compare, and research mutual funds with confidence.
            </p>
          </div>
        </div>

        {/* Main Action Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div
            onClick={() => handleOverviewQuery('Compare PPFAS Flexi Cap and HDFC Flexi Cap')}
            className="backdrop-blur-md bg-[#1f2833]/40 border border-white/10 p-5 rounded-xl hover:border-[#66a3ff]/40 transition-colors cursor-pointer group"
          >
            <div className="w-10 h-10 rounded-lg bg-[#66a3ff]/10 flex items-center justify-center mb-4 group-hover:bg-[#66a3ff]/20 transition-colors">
              <ArrowLeftRight className="text-[#66a3ff] h-5 w-5" />
            </div>
            <h3 className="text-lg font-medium text-white mb-2">Compare Funds</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Compare returns, risk, expense ratio, AUM, fund category, and consistency side-by-side.
            </p>
          </div>

          <div
            onClick={() => setActiveTab('research')}
            className="backdrop-blur-md bg-[#1f2833]/40 border border-[#66a3ff]/20 p-5 rounded-xl hover:border-[#66a3ff]/60 transition-colors cursor-pointer group relative overflow-hidden"
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-[#66a3ff]/10 rounded-full blur-3xl pointer-events-none"></div>
            <div className="w-10 h-10 rounded-lg bg-[#66a3ff]/20 flex items-center justify-center mb-4 group-hover:bg-[#66a3ff]/30 transition-colors relative z-10">
              <Brain className="text-[#66a3ff] h-5 w-5" />
            </div>
            <h3 className="text-lg font-medium text-white mb-2 relative z-10">AI Fund Research</h3>
            <p className="text-sm text-slate-400 leading-relaxed relative z-10">
              Ask FundersAI to explain funds, compare strategies, or simplify complex fund data.
            </p>
          </div>

          <div
            onClick={() => handleOverviewQuery('Review my portfolio health')}
            className="backdrop-blur-md bg-[#1f2833]/40 border border-white/10 p-5 rounded-xl hover:border-[#66a3ff]/40 transition-colors cursor-pointer group"
          >
            <div className="w-10 h-10 rounded-lg bg-[#66a3ff]/10 flex items-center justify-center mb-4 group-hover:bg-[#66a3ff]/20 transition-colors">
              <Wallet className="text-[#66a3ff] h-5 w-5" />
            </div>
            <h3 className="text-lg font-medium text-white mb-2">Portfolio Review</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Upload your portfolio and get a simple health check and diversification review.
            </p>
          </div>
        </div>

        {/* Two Column Layout for the rest */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Left Column (Wider) */}
          <div className="xl:col-span-2 space-y-6">
            
            {/* Quick Compare Widget */}
            <div className="backdrop-blur-md bg-[#1f2833]/40 border border-white/10 rounded-xl p-5">
              <div className="flex items-center gap-2 mb-4">
                <ArrowLeftRight className="text-[#66a3ff] h-5 w-5" />
                <h3 className="font-serif text-xl font-medium text-white">Quick Compare</h3>
              </div>
              <div className="flex flex-col sm:flex-row gap-3 items-center">
                <div className="flex-1 w-full relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 h-4 w-4" />
                  <input
                    type="text"
                    value={compareFund1}
                    onChange={(e) => setCompareFund1(e.target.value)}
                    placeholder="E.g. Parag Parikh Flexi Cap"
                    className="w-full bg-[#080d1a] border border-white/20 rounded-lg py-2.5 pl-10 pr-3 text-sm text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-[#66a3ff] focus:border-[#66a3ff] transition-all"
                  />
                </div>
                <div className="text-slate-500 font-medium font-serif-display px-2 text-sm">VS</div>
                <div className="flex-1 w-full relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 h-4 w-4" />
                  <input
                    type="text"
                    value={compareFund2}
                    onChange={(e) => setCompareFund2(e.target.value)}
                    placeholder="E.g. HDFC Flexi Cap"
                    className="w-full bg-[#080d1a] border border-white/20 rounded-lg py-2.5 pl-10 pr-3 text-sm text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-[#66a3ff] focus:border-[#66a3ff] transition-all"
                  />
                </div>
                <button
                  onClick={() => {
                    if (compareFund1 && compareFund2) {
                      handleOverviewQuery(`Compare ${compareFund1} and ${compareFund2}`);
                    }
                  }}
                  disabled={!compareFund1 || !compareFund2}
                  className="w-full sm:w-auto px-6 py-2.5 bg-[#66a3ff] text-slate-950 rounded-lg font-medium text-sm hover:bg-[#66a3ff]/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Compare Now
                </button>
              </div>
            </div>

            {/* Market / Category Snapshot */}
            <div>
              <h3 className="font-serif text-xl font-medium text-white mb-4">Explore Categories</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                {[
                  { title: 'Large Cap', desc: 'Top 100 companies', icon: Landmark, q: 'Show me top large cap funds' },
                  { title: 'Mid Cap', desc: 'High growth potential', icon: TrendingUp, q: 'Analyze mid cap funds performance' },
                  { title: 'Small Cap', desc: 'Aggressive growth', icon: ChartSpline, q: 'What are the risks of small cap funds?' },
                  { title: 'Flexi Cap', desc: 'Dynamic allocation', icon: PieChart, q: 'Explain flexi cap funds vs multi cap' },
                  { title: 'Index Funds', desc: 'Low cost tracking', icon: Database, q: 'Compare popular Nifty 50 index funds' },
                  { title: 'ELSS', desc: 'Tax saving funds', icon: ShieldCheck, q: 'What are ELSS funds and their benefits?' },
                ].map((cat, i) => {
                  const CatIcon = cat.icon;
                  return (
                    <div
                      key={i}
                      onClick={() => handleOverviewQuery(cat.q)}
                      className="backdrop-blur-md bg-[#1f2833]/40 border border-white/10 rounded-lg p-3 hover:border-[#66a3ff]/30 hover:bg-white/5 transition-all cursor-pointer group"
                    >
                      <CatIcon className="text-[#66a3ff] h-4 w-4 mb-2 opacity-80 group-hover:opacity-100 transition-opacity" />
                      <div className="text-sm font-medium text-white mb-0.5">{cat.title}</div>
                      <div className="text-[11px] text-slate-400">{cat.desc}</div>
                    </div>
                  );
                })}
              </div>
            </div>
            
          </div>

          {/* Right Column (Narrower) */}
          <div className="space-y-6">
            
            {/* Beginner Tools Placeholder */}
            <div className="backdrop-blur-md bg-[#1f2833]/40 border border-white/10 rounded-xl p-5">
              <h3 className="font-serif text-lg font-medium text-white mb-4">Investor Tools</h3>
              <div className="space-y-2">
                <button onClick={() => handleOverviewQuery("Calculate SIP returns for 10000 per month for 10 years")} className="w-full text-left p-3 rounded-lg border border-white/10 bg-[#080d1a]/50 hover:bg-[#66a3ff]/10 hover:border-[#66a3ff]/30 transition-all cursor-pointer flex items-center justify-between group">
                  <div>
                    <div className="text-[13px] font-medium text-white">SIP Calculator</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">Estimate your future wealth</div>
                  </div>
                  <ArrowRight className="h-4 w-4 text-slate-500 group-hover:text-[#66a3ff] transition-colors" />
                </button>
                <button onClick={() => handleOverviewQuery("Help me find my risk profile")} className="w-full text-left p-3 rounded-lg border border-white/10 bg-[#080d1a]/50 hover:bg-[#66a3ff]/10 hover:border-[#66a3ff]/30 transition-all cursor-pointer flex items-center justify-between group">
                  <div>
                    <div className="text-[13px] font-medium text-white">Risk Quiz</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">Find funds that fit you</div>
                  </div>
                  <ArrowRight className="h-4 w-4 text-slate-500 group-hover:text-[#66a3ff] transition-colors" />
                </button>
              </div>
            </div>

            {/* Recent Activity */}
            <div className="backdrop-blur-md bg-[#1f2833]/40 border border-white/10 rounded-xl p-5">
              <h3 className="font-serif text-lg font-medium text-white mb-4">Recent Activity</h3>
              <div className="space-y-3">
                <div onClick={() => handleOverviewQuery('Analyze Parag Parikh Flexi Cap Fund')} className="flex items-center gap-3 cursor-pointer group">
                  <div className="w-8 h-8 rounded bg-[#0f172a] border border-white/10 flex items-center justify-center shrink-0">
                    <History className="h-3.5 w-3.5 text-slate-400" />
                  </div>
                  <div>
                    <div className="text-[12px] font-medium text-white group-hover:text-[#66a3ff] transition-colors">Parag Parikh Flexi Cap</div>
                    <div className="text-[10px] text-slate-500">Viewed 2h ago</div>
                  </div>
                </div>
                <div onClick={() => handleOverviewQuery('Compare Nifty 50 vs Next 50')} className="flex items-center gap-3 cursor-pointer group">
                  <div className="w-8 h-8 rounded bg-[#0f172a] border border-white/10 flex items-center justify-center shrink-0">
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
        <div className="mt-8 pt-6 border-t border-white/10 text-center">
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
      default:
        return <CanvasPlaceholder />;
    }
  };

  return (
    <div className="relative h-screen w-screen overflow-hidden bg-[#050913] text-[#e8f0ff] flex flex-col">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_12%_8%,rgba(0,80,158,0.18),transparent_35%),radial-gradient(circle_at_88%_10%,rgba(0,122,204,0.15),transparent_30%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_bottom,rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(to_right,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[length:56px_56px]" />

      <div className="relative flex flex-col flex-1 h-full w-full overflow-hidden border border-white/10 bg-[linear-gradient(160deg,rgba(10,18,34,0.92),rgba(3,10,22,0.96))] shadow-[0_28px_80px_rgba(0,0,0,0.5)] backdrop-blur-xl">
        <header className="h-16 shrink-0 flex items-center justify-between border-b border-white/10 px-4 sm:px-5">
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
            <div className="hidden sm:block">
              <p className="text-sm font-semibold text-white">FundersAI Research</p>
              <p className="text-xs text-slate-400">Centered chat + optional canvas</p>
            </div>
          </div>

          <div className="hidden relative max-w-xs w-full sm:block">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400 h-3.5 w-3.5" />
            <input
              type="text"
              placeholder="Search tickers, funds, research..."
              className="w-full bg-[#080d1a] border border-white/10 rounded-lg py-1.5 pl-8 pr-3 text-xs text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-[#66a3ff]/50 focus:border-[#66a3ff]/50 transition-all"
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

        <div className="flex h-[calc(100vh-64px)] overflow-hidden relative z-10 w-full">
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
                <aside className="flex-1 min-w-[320px] h-full min-h-0">
                  <ChatWindow />
                </aside>
                
                {/* Drag handle styled like Gemini's canvas handle */}
                <div
                  onMouseDown={() => setIsResizingCanvas(true)}
                  className={`w-3 cursor-col-resize self-stretch transition-all duration-150 relative z-20 flex-shrink-0 flex items-center justify-center group`}
                  title="Drag to resize canvas"
                >
                  {/* Central divider line */}
                  <div className={`w-[2px] h-full transition-all duration-150 ${
                    isResizingCanvas ? 'bg-[#66a3ff]' : 'bg-white/10 group-hover:bg-[#66a3ff]/50'
                  }`} />

                  {/* Glassmorphic Capsule Handle */}
                  <div className={`absolute w-5 h-12 rounded-full border bg-slate-950/80 backdrop-blur-md flex flex-col gap-1 items-center justify-center shadow-lg transition-all duration-200 pointer-events-none ${
                    isResizingCanvas
                      ? 'border-[#66a3ff]/80 scale-105 opacity-100 shadow-[0_0_12px_rgba(102,163,255,0.3)]'
                      : 'border-white/10 opacity-40 group-hover:opacity-100 group-hover:border-[#66a3ff]/40'
                  }`}>
                    {/* Vertical grip dots */}
                    <div className="flex flex-col gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400/80 group-hover:bg-[#66a3ff]" />
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400/80 group-hover:bg-[#66a3ff]" />
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400/80 group-hover:bg-[#66a3ff]" />
                    </div>
                  </div>
                </div>

                <main 
                  style={{ width: `${canvasWidth}px` }}
                  className="min-h-0 min-w-0 h-full overflow-y-auto rounded-[1.2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.85),rgba(2,6,23,0.9))] p-5 backdrop-blur-xl flex-shrink-0"
                >
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
