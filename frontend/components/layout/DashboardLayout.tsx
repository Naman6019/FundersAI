'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
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
} from 'lucide-react';
import { useCanvasStore } from '@/store/useCanvasStore';
import SignOutButton from '@/components/auth/SignOutButton';
import ChatWindow from '@/components/chat/ChatWindow';
import StockDetailView from '@/components/canvas/StockDetailView';
import MFDetailView from '@/components/canvas/MFDetailView';
import ComparisonView from '@/components/canvas/ComparisonView';

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
        <span className="mt-4 inline-flex rounded-full border border-emerald-300/30 bg-emerald-300/10 px-3 py-1 text-xs text-emerald-200">
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

      <div className="mt-5 flex-1 rounded-[1.2rem] border border-white/10 bg-[linear-gradient(180deg,rgba(16,185,129,0.1),rgba(15,23,42,0.25))] p-4">
        <svg viewBox="0 0 700 260" className="h-full w-full" aria-hidden>
          <path d="M30 210 C110 180, 150 192, 220 160 C270 138, 300 150, 360 122 C410 98, 450 112, 510 86 C560 66, 620 82, 670 72" fill="none" stroke="#57E4C3" strokeWidth="4" strokeLinecap="round"/>
          <path d="M30 224 C105 202, 150 198, 220 188 C280 178, 310 166, 360 172 C412 178, 455 144, 510 150 C560 156, 620 126, 670 132" fill="none" stroke="#68BCFF" strokeWidth="3" strokeLinecap="round"/>
        </svg>
      </div>
    </div>
  );
}

function SidebarContent({ dataHealth, healthCheckedAt }: { dataHealth: DataHealthItem[]; healthCheckedAt: string | null }) {
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

      <div className="mt-6 rounded-xl border border-white/10 bg-white/[0.03] p-3">
        <p className="text-[11px] uppercase tracking-[0.16em] text-slate-400">Pipelines</p>
        <div className="mt-3 space-y-2">
          <div className="flex items-center gap-2 text-sm text-slate-200">
            <ChartSpline className="h-4 w-4 text-sky-300" />
            Quant + comparison
          </div>
          <div className="flex items-center gap-2 text-sm text-slate-200">
            <Database className="h-4 w-4 text-emerald-300" />
            Supabase-first data
          </div>
          <div className="flex items-center gap-2 text-sm text-slate-200">
            <ShieldCheck className="h-4 w-4 text-slate-300" />
            Research-only guardrails
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.03] p-3">
        <p className="text-[11px] uppercase tracking-[0.16em] text-slate-400">Data health</p>
        <div className="mt-3 space-y-2">
          {dataHealth.map(({ label, status, note }) => (
            <div key={label} className="rounded-lg border border-white/10 bg-[#0f172a]/70 px-3 py-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-slate-300" title={note || ''}>{label}</span>
                <span className={`font-semibold ${statusColorClass(status)}`} title={note || ''}>{status}</span>
              </div>
              {note ? <p className="mt-1 text-[10px] leading-tight text-slate-400">{note}</p> : null}
            </div>
          ))}
        </div>
        <p className="mt-2 text-[10px] text-slate-400">
          {healthCheckedAt
            ? `Checked ${new Date(healthCheckedAt).toLocaleString('en-IN', { hour12: false })}`
            : 'Waiting for health snapshot'}
        </p>
      </div>

      <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.03] p-3">
        <div className="flex items-center gap-2 text-slate-100">
          <Bolt className="h-4 w-4 text-sky-300" />
          <p className="text-sm font-semibold">Next module</p>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-slate-300">
          Stock research follows after mutual fund coverage is broadened.
        </p>
        <Link
          href="/admin"
          className="mt-3 inline-flex rounded-md border border-white/15 bg-white/[0.04] px-2.5 py-1.5 text-xs font-medium text-slate-200 hover:border-sky-300/40 hover:text-white"
        >
          Open admin ops dashboard
        </Link>
      </div>

      <div className="mt-auto pt-4">
        <p className="mb-3 text-[11px] text-slate-400">Not investment advice. Validate independently.</p>
        <SignOutButton />
      </div>
    </div>
  );
}

export default function DashboardLayout() {
  const { activeView, selectedIds, auxiliaryData, isCanvasOpen, toggleCanvas } = useCanvasStore();
  const [isMobile, setIsMobile] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [canvasWidth, setCanvasWidth] = useState(640);
  const [isResizingCanvas, setIsResizingCanvas] = useState(false);
  const [dataHealth, setDataHealth] = useState<DataHealthItem[]>(DEFAULT_DATA_HEALTH);
  const [healthCheckedAt, setHealthCheckedAt] = useState<string | null>(null);
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
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_12%_8%,rgba(59,130,246,0.18),transparent_35%),radial-gradient(circle_at_88%_10%,rgba(16,185,129,0.13),transparent_30%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_bottom,rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(to_right,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[length:56px_56px]" />

      <div className="relative flex flex-col flex-1 h-full w-full overflow-hidden border border-white/10 bg-[linear-gradient(160deg,rgba(10,18,34,0.92),rgba(3,10,22,0.96))] shadow-[0_28px_80px_rgba(0,0,0,0.5)] backdrop-blur-xl">
        <header className="h-16 shrink-0 flex items-center justify-between border-b border-white/10 px-4 sm:px-5">
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-white/15 bg-white/[0.04] text-slate-200 transition hover:border-sky-300/50 hover:text-white"
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

          <div className="hidden rounded-full border border-white/15 bg-white/[0.04] px-4 py-1.5 text-xs text-slate-300 sm:block">
            fundersai.com/fund-comparison
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition ${
                isCanvasOpen
                  ? 'border-emerald-300/35 bg-emerald-300/12 text-emerald-100'
                  : 'border-white/15 bg-white/[0.04] text-slate-200 hover:border-sky-300/45 hover:text-white'
              }`}
              onClick={toggleCanvas}
            >
              {isCanvasOpen ? <PanelRightClose className="h-3.5 w-3.5" /> : <PanelRightOpen className="h-3.5 w-3.5" />}
              Canvas
            </button>
            <div className="hidden items-center gap-1.5 text-xs font-medium text-emerald-300 sm:flex">
              <Clock3 className="h-3.5 w-3.5" />
              <span className={statusColorClass(navStatus)}>MF NAV {navStatus}</span>
            </div>
          </div>
        </header>

        <div className="flex h-[calc(100vh-64px)] overflow-hidden relative z-10 w-full">
          {!isMobile && !isSidebarCollapsed && (
            <aside className="w-[276px] shrink-0 border-r border-white/10 bg-[#0b1526]/72 p-4 min-h-0 h-full overflow-y-auto">
              <SidebarContent dataHealth={dataHealth} healthCheckedAt={healthCheckedAt} />
            </aside>
          )}

          <div className="flex-1 min-w-0 h-full p-6 overflow-hidden">
            {isMobile ? (
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
                    isResizingCanvas ? 'bg-sky-400' : 'bg-white/10 group-hover:bg-sky-400/50'
                  }`} />
                  
                  {/* Glassmorphic Capsule Handle */}
                  <div className={`absolute w-5 h-12 rounded-full border bg-slate-950/80 backdrop-blur-md flex flex-col gap-1 items-center justify-center shadow-lg transition-all duration-200 pointer-events-none ${
                    isResizingCanvas 
                      ? 'border-sky-400/80 scale-105 opacity-100 shadow-[0_0_12px_rgba(56,189,248,0.3)]' 
                      : 'border-white/10 opacity-40 group-hover:opacity-100 group-hover:border-sky-400/40'
                  }`}>
                    {/* Vertical grip dots */}
                    <div className="flex flex-col gap-1">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400/80 group-hover:bg-sky-300" />
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400/80 group-hover:bg-sky-300" />
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-400/80 group-hover:bg-sky-300" />
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
            <SidebarContent dataHealth={dataHealth} healthCheckedAt={healthCheckedAt} />
          </aside>
        </div>
      )}
    </div>
  );
}
