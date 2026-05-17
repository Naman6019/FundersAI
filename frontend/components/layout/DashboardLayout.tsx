'use client';

import { useEffect, useState } from 'react';
import { Circle, Clock3 } from 'lucide-react';
import { useCanvasStore } from '@/store/useCanvasStore';
import SignOutButton from '@/components/auth/SignOutButton';
import ChatWindow from '@/components/chat/ChatWindow';
import StockDetailView from '@/components/canvas/StockDetailView';
import MFDetailView from '@/components/canvas/MFDetailView';
import ComparisonView from '@/components/canvas/ComparisonView';

function CanvasPlaceholder() {
  return (
    <div className="flex h-full flex-col rounded-[1.8rem] border border-white/10 bg-[linear-gradient(160deg,rgba(13,27,46,0.9),rgba(8,18,34,0.88))] p-5 shadow-[0_20px_46px_rgba(0,0,0,0.34)]">
      <div>
        <h2 className="text-4xl font-semibold tracking-tight text-[#e8f0ff]">Fund comparison canvas</h2>
        <p className="mt-1 text-base text-[#9fb4d8]">Parag Parikh Flexi Cap vs ICICI Multi Asset Fund</p>
        <span className="mt-4 inline-flex rounded-full border border-white/15 bg-white/[0.03] px-3 py-1 text-sm text-[#c6d7f3]">
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
          <div key={item.label} className="rounded-2xl border border-white/10 bg-[#0b1730]/90 p-4">
            <p className="text-sm text-[#89a4ce]">{item.label}</p>
            <p className="mt-2 text-3xl font-semibold tracking-tight text-[#e8f0ff]">{item.value}</p>
            <p className="mt-1 text-sm text-[#7f99c1]">{item.note}</p>
          </div>
        ))}
      </div>

      <div className="mt-5 flex-1 rounded-[1.6rem] border border-emerald-200/20 bg-[linear-gradient(180deg,rgba(19,65,71,0.34),rgba(10,27,49,0.4))] p-4">
        <svg viewBox="0 0 700 260" className="h-full w-full" aria-hidden>
          <path d="M30 210 C110 180, 150 192, 220 160 C270 138, 300 150, 360 122 C410 98, 450 112, 510 86 C560 66, 620 82, 670 72" fill="none" stroke="#57E4C3" strokeWidth="4" strokeLinecap="round"/>
          <path d="M30 224 C105 202, 150 198, 220 188 C280 178, 310 166, 360 172 C412 178, 455 144, 510 150 C560 156, 620 126, 670 132" fill="none" stroke="#68BCFF" strokeWidth="3" strokeLinecap="round"/>
        </svg>
      </div>
    </div>
  );
}

function DataHealthPanel() {
  return (
    <aside className="flex h-full flex-col rounded-[1.8rem] border border-white/10 bg-[linear-gradient(160deg,rgba(13,26,45,0.9),rgba(8,18,34,0.88))] p-5 shadow-[0_20px_46px_rgba(0,0,0,0.34)]">
      <h3 className="text-2xl font-semibold tracking-tight text-[#e8f0ff]">Data health</h3>

      <div className="mt-4 space-y-3">
        {[
          { label: 'MF NAV', status: 'Fresh' },
          { label: 'AUM / TER', status: 'Synced' },
          { label: 'Risk metrics', status: 'Ready' },
          { label: 'Factsheets', status: 'Indexed' },
        ].map((item) => (
          <div key={item.label} className="flex items-center justify-between rounded-2xl border border-white/10 bg-[#0c1932]/90 px-4 py-3">
            <span className="text-lg text-[#9ab2d9]">{item.label}</span>
            <span className="text-lg font-medium text-[#56e9c5]">{item.status}</span>
          </div>
        ))}
      </div>

      <div className="mt-5 rounded-[1.5rem] border border-white/10 bg-white/[0.04] p-4">
        <p className="text-sm uppercase tracking-[0.18em] text-[#8faad5]">Next module</p>
        <p className="mt-2 text-3xl font-semibold text-[#e8f0ff]">Stock research</p>
        <p className="mt-2 text-base leading-relaxed text-[#8ea6cd]">
          Stock coverage is on the way. Mutual fund comparison stays the current MVP.
        </p>
      </div>

      <div className="mt-auto pt-4">
        <SignOutButton />
      </div>
    </aside>
  );
}

export default function DashboardLayout() {
  const { activeView, selectedIds, auxiliaryData } = useCanvasStore();
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    fetch('/api/keepalive').catch(() => {});
  }, []);

  useEffect(() => {
    const query = window.matchMedia('(max-width: 1100px)');
    const update = () => setIsMobile(query.matches);
    update();
    query.addEventListener('change', update);
    return () => query.removeEventListener('change', update);
  }, []);

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
    <div className="relative min-h-screen overflow-hidden bg-[#040a14] text-[#e8f0ff]">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_10%_6%,rgba(76,124,210,0.23),transparent_35%),radial-gradient(circle_at_90%_10%,rgba(89,236,195,0.15),transparent_30%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_bottom,rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(to_right,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[length:42px_42px]" />

      <div className="relative mx-auto max-w-[1520px] px-4 py-4 sm:px-6">
        <div className="min-h-[calc(100vh-2rem)] overflow-hidden rounded-[2.2rem] border border-white/10 bg-[linear-gradient(160deg,rgba(7,18,36,0.9),rgba(5,13,26,0.92))] shadow-[0_28px_80px_rgba(0,0,0,0.45)]">
          <header className="flex items-center justify-between border-b border-white/10 px-6 py-5">
            <div className="flex items-center gap-2.5">
              <Circle className="h-4 w-4 fill-[#f87171] text-[#f87171]" />
              <Circle className="h-4 w-4 fill-[#facc15] text-[#facc15]" />
              <Circle className="h-4 w-4 fill-[#34d399] text-[#34d399]" />
            </div>

            <div className="rounded-full border border-white/10 bg-[#0c1a32] px-5 py-2 text-base text-[#9ab3d8]">
              mooliq.com/fund-comparison
            </div>

            <div className="flex items-center gap-2 text-sm font-medium text-[#61eac8]">
              <Clock3 className="h-4 w-4" />
              <span>NAV updated today</span>
            </div>
          </header>

          <div className={`grid gap-4 p-4 sm:p-5 ${isMobile ? 'grid-cols-1' : 'grid-cols-[340px_minmax(0,1fr)_320px]'}`}>
            <div className="min-h-[620px]">
              <ChatWindow />
            </div>

            <div className="min-h-[620px] min-w-0">
              {renderCanvasContent()}
            </div>

            <div className="min-h-[620px]">
              <DataHealthPanel />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
