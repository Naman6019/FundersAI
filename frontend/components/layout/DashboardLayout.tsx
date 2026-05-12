'use client';

import { useState, useEffect } from 'react';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import { useCanvasStore } from '@/store/useCanvasStore';
import { ChevronRight, ChevronLeft, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import SignOutButton from '@/components/auth/SignOutButton';
import ChatWindow from '@/components/chat/ChatWindow';
import StockDetailView from '@/components/canvas/StockDetailView';
import MFDetailView from '@/components/canvas/MFDetailView';
import ComparisonView from '@/components/canvas/ComparisonView';

export default function DashboardLayout() {
  const { isCanvasOpen, activeView, selectedIds, auxiliaryData, toggleCanvas } = useCanvasStore();
  const [isSidebarVisible, setIsSidebarVisible] = useState(true);
  const [isMobile, setIsMobile] = useState(false);

  // Wake up the backend on load
  useEffect(() => {
    fetch('/api/keepalive').catch(() => {});
  }, []);

  useEffect(() => {
    const query = window.matchMedia('(max-width: 768px)');
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
        return <ComparisonView ids={selectedIds} type={selectedIds[0].match(/^[0-9]+$/) ? 'MUTUAL_FUND' : 'STOCK'} auxiliaryData={auxiliaryData} />;
      default:
        return <div className="p-6 text-gray-400">Select an item to view details.</div>;
    }
  };

  return (
    <div className={`app-container finance-shell ${isSidebarVisible ? '' : 'sidebar-collapsed'}`}>
      <aside className={`sidebar ${isSidebarVisible ? '' : 'sidebar-hidden'} z-20 h-full flex flex-col`}>
        <div className="flex justify-between items-start mb-6">
          <div className="brand">
            <div className="logo"></div>
            <div>
              <h1>MarketMind</h1>
              <p className="tagline">Research Terminal</p>
            </div>
          </div>
          <button 
            onClick={() => setIsSidebarVisible(false)}
            className="sidebar-toggle-btn"
            title="Hide Sidebar"
          >
            <PanelLeftClose size={18} />
          </button>
        </div>

        <div className="info-panel">
          <h3>Analysis Pipeline</h3>
          <ul className="pipeline-list">
            <li><span className="dot q-dot"></span> Quant Models</li>
            <li><span className="dot n-dot"></span> Market Signals</li>
            <li><span className="dot s-dot"></span> Synthesis Engine</li>
          </ul>
        </div>

        <div className="disclaimer-sidebar">
          <p>Research platform only. Not investment advice. Validate decisions with a SEBI-registered advisor.</p>
        </div>

        <SignOutButton />
      </aside>

      <main className="flex-1 h-full relative flex overflow-hidden gap-4">
        {isMobile ? (
          <div className="mobile-workspace">
            <div className={`chat-area relative h-full w-full ${isCanvasOpen ? 'hidden' : 'flex'}`} aria-hidden={isCanvasOpen}>
              <ChatWindow />
            </div>
            {isCanvasOpen && (
              <div className="absolute inset-0 z-40 flex min-h-0 min-w-0 canvas-stage">
                <button
                  onClick={toggleCanvas}
                  className="canvas-close-btn"
                  aria-label="Close comparison"
                >
                  <ChevronRight size={20} />
                </button>
                {renderCanvasContent()}
              </div>
            )}
          </div>
        ) : (
        <PanelGroup direction="horizontal">
          <Panel defaultSize={isCanvasOpen ? 40 : 100} minSize={30} className="relative transition-all duration-300 ease-in-out chat-area">
            {!isSidebarVisible && (
              <button 
                onClick={() => setIsSidebarVisible(true)}
                className="sidebar-open-btn"
                title="Show Sidebar"
              >
                <PanelLeftOpen size={20} />
              </button>
            )}
            <ChatWindow />
            
            <button 
              onClick={toggleCanvas}
              className="canvas-toggle-btn"
            >
              {isCanvasOpen ? <ChevronRight size={20} /> : <ChevronLeft size={20} />}
            </button>
          </Panel>

          {isCanvasOpen && (
            <>
              <PanelResizeHandle className="w-4 flex items-center justify-center cursor-col-resize user-select-none">
                <div className="resize-handle-pill"></div>
              </PanelResizeHandle>
              <Panel defaultSize={60} minSize={40} className="animate-in slide-in-from-right-4 duration-300 ease-in-out canvas-panel">
                {renderCanvasContent()}
              </Panel>
            </>
          )}
        </PanelGroup>
        )}
      </main>
    </div>
  );
}
