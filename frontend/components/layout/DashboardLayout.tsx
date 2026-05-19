'use client';

import { useEffect, useState } from 'react';
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
  if (['fresh', 'synced', 'ready', 'indexed'].includes(normalized)) return 'text-[#5be2c0]';
  if (['lagging', 'partial', 'processing', 'checking'].includes(normalized)) return 'text-[#f7d37a]';
  if (['stale', 'missing', 'error'].includes(normalized)) return 'text-[#ff9c9c]';
  return 'text-[#b9cceb]';
}

function CanvasPlaceholder() {
  return (
    <div className="flex h-full flex-col rounded-[1.3rem] border border-[#2b3e5e] bg-[linear-gradient(160deg,rgba(12,26,47,0.95),rgba(8,19,36,0.95))] p-5 shadow-[0_18px_36px_rgba(0,0,0,0.3)]">
      <div>
        <h2 className="text-3xl font-semibold tracking-tight text-[#e8f0ff]">Fund comparison canvas</h2>
        <p className="mt-1 text-sm text-[#9fb4d8]">Parag Parikh Flexi Cap vs ICICI Multi Asset Fund</p>
        <span className="mt-4 inline-flex rounded-full border border-[#385178] bg-[#142747] px-3 py-1 text-xs text-[#c6d7f3]">
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
          <div key={item.label} className="rounded-xl border border-[#2d4468] bg-[#0d1b34]/90 p-4">
            <p className="text-xs text-[#89a4ce]">{item.label}</p>
            <p className="mt-2 text-3xl font-semibold tracking-tight text-[#e8f0ff]">{item.value}</p>
            <p className="mt-1 text-xs text-[#7f99c1]">{item.note}</p>
          </div>
        ))}
      </div>

      <div className="mt-5 flex-1 rounded-[1.2rem] border border-emerald-200/20 bg-[linear-gradient(180deg,rgba(19,65,71,0.34),rgba(10,27,49,0.4))] p-4">
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
    <div className="flex h-full flex-col rounded-[1.2rem] border border-[#2b3e5f] bg-[linear-gradient(180deg,#111d31,#0d1728_60%,#0b1423)] p-4 shadow-[0_20px_40px_rgba(0,0,0,0.36)]">
      <div>
        <div className="flex items-center gap-2">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-[linear-gradient(135deg,#73b6ff,#3b73de)] text-white shadow-[0_8px_18px_rgba(59,115,222,0.4)]">
            <Sparkles className="h-4 w-4" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-[#eaf2ff]">MooliqAI</h1>
            <p className="text-[11px] uppercase tracking-[0.14em] text-[#8ea7cb]">Research terminal</p>
          </div>
        </div>
      </div>

      <div className="mt-6 rounded-xl border border-[#314766] bg-[#122038] p-3">
        <p className="text-[11px] uppercase tracking-[0.16em] text-[#90a8ca]">Pipelines</p>
        <div className="mt-3 space-y-2">
          <div className="flex items-center gap-2 text-sm text-[#d6e5ff]">
            <ChartSpline className="h-4 w-4 text-[#74b5ff]" />
            Quant + comparison
          </div>
          <div className="flex items-center gap-2 text-sm text-[#d6e5ff]">
            <Database className="h-4 w-4 text-[#5ad2a5]" />
            Supabase-first data
          </div>
          <div className="flex items-center gap-2 text-sm text-[#d6e5ff]">
            <ShieldCheck className="h-4 w-4 text-[#b6c7df]" />
            Research-only guardrails
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-[#314766] bg-[#122038] p-3">
        <p className="text-[11px] uppercase tracking-[0.16em] text-[#90a8ca]">Data health</p>
        <div className="mt-3 space-y-2">
          {dataHealth.map(({ label, status, note }) => (
            <div key={label} className="rounded-lg border border-[#2e4466] bg-[#0f1b30] px-3 py-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-[#9fb4d6]" title={note || ''}>{label}</span>
                <span className={`font-semibold ${statusColorClass(status)}`} title={note || ''}>{status}</span>
              </div>
              {note ? <p className="mt-1 text-[10px] leading-tight text-[#7f97bc]">{note}</p> : null}
            </div>
          ))}
        </div>
        <p className="mt-2 text-[10px] text-[#7f97bc]">
          {healthCheckedAt
            ? `Checked ${new Date(healthCheckedAt).toLocaleString('en-IN', { hour12: false })}`
            : 'Waiting for health snapshot'}
        </p>
      </div>

      <div className="mt-4 rounded-xl border border-[#314766] bg-[#122038] p-3">
        <div className="flex items-center gap-2 text-[#d8e7ff]">
          <Bolt className="h-4 w-4 text-[#7eb9ff]" />
          <p className="text-sm font-semibold">Next module</p>
        </div>
        <p className="mt-2 text-xs leading-relaxed text-[#91a9cc]">
          Stock research follows after mutual fund coverage is broadened.
        </p>
      </div>

      <div className="mt-auto pt-4">
        <p className="mb-3 text-[11px] text-[#7f97bc]">Not investment advice. Validate independently.</p>
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
    const max = Math.min(Math.max(window.innerWidth - 520, 560), 980);
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
      const rightGap = 22;
      const next = window.innerWidth - event.clientX - rightGap;
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
    <div className="relative h-screen w-screen overflow-hidden bg-[#050a12] text-[#e8f0ff] flex flex-col">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_10%_6%,rgba(76,124,210,0.23),transparent_35%),radial-gradient(circle_at_90%_10%,rgba(89,236,195,0.15),transparent_30%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_bottom,rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(to_right,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[length:42px_42px]" />

      <div className="relative flex flex-col flex-1 h-full w-full overflow-hidden border border-[#2b3e5f] bg-[linear-gradient(160deg,rgba(7,18,36,0.92),rgba(5,13,26,0.95))] shadow-[0_28px_80px_rgba(0,0,0,0.45)]">
        <header className="h-16 shrink-0 flex items-center justify-between border-b border-[#2b3e5f] px-4 sm:px-5">
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-[#355079] bg-[#0f1c32] text-[#c6d8f4] transition hover:border-[#4f8ff7] hover:text-white"
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
              <p className="text-sm font-semibold text-[#e9f2ff]">Mooliq Research</p>
              <p className="text-xs text-[#90a8cb]">Centered chat + optional canvas</p>
            </div>
          </div>

          <div className="hidden rounded-full border border-[#355079] bg-[#0f1c32] px-4 py-1.5 text-xs text-[#9ab3d8] sm:block">
            mooliq.com/fund-comparison
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-xs font-semibold transition ${
                isCanvasOpen
                  ? 'border-emerald-300/35 bg-emerald-300/10 text-emerald-100'
                  : 'border-[#355079] bg-[#0f1c32] text-[#bad0ef] hover:border-[#4f8ff7] hover:text-white'
              }`}
              onClick={toggleCanvas}
            >
              {isCanvasOpen ? <PanelRightClose className="h-3.5 w-3.5" /> : <PanelRightOpen className="h-3.5 w-3.5" />}
              Canvas
            </button>
            <div className="hidden items-center gap-1.5 text-xs font-medium text-[#61eac8] sm:flex">
              <Clock3 className="h-3.5 w-3.5" />
              <span className={statusColorClass(navStatus)}>MF NAV {navStatus}</span>
            </div>
          </div>
        </header>

        <div className="flex h-[calc(100vh-64px)] overflow-hidden relative z-10 w-full">
          {!isMobile && !isSidebarCollapsed && (
            <aside className="w-[276px] shrink-0 border-r border-[#2b3e5f] bg-[#0c1626]/80 p-4 min-h-0 h-full overflow-y-auto">
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
                  <section className="flex-1 min-h-[420px] rounded-[1.2rem] border border-[#2b3e5f] bg-[linear-gradient(180deg,#0f1a2d,#0c1524)] p-4">
                    {renderCanvasContent()}
                  </section>
                )}
              </div>
            ) : isCanvasOpen ? (
              <div className="grid h-full grid-cols-[420px_minmax(0,1fr)] gap-6">
                <aside className="min-h-0 h-full">
                  <ChatWindow />
                </aside>
                <main className="min-h-0 min-w-0 h-full overflow-y-auto rounded-[1.2rem] border border-[#2b3e5f] bg-[linear-gradient(180deg,#0f1a2d,#0c1524)] p-5">
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
        <div className="fixed inset-0 z-50 bg-black/50 lg:hidden" onClick={() => setIsMobileSidebarOpen(false)}>
          <aside
            className="h-full w-[290px] border-r border-[#2b3e5f] bg-[linear-gradient(180deg,#111d31,#0d1728_60%,#0b1423)] p-4"
            onClick={(event) => event.stopPropagation()}
          >
            <SidebarContent dataHealth={dataHealth} healthCheckedAt={healthCheckedAt} />
          </aside>
        </div>
      )}
    </div>
  );
}
