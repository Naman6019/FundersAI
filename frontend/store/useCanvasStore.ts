import { create } from 'zustand';
import type { CanvasPayload } from '@/types/funds';

type ViewMode = 'NONE' | 'STOCK_DETAIL' | 'MF_DETAIL' | 'COMPARISON' | 'PORTFOLIO_REVIEW' | 'CATEGORY_COMPARE';
type ComparisonMode = 'simple' | 'llm';

interface CanvasState {
  activeView: ViewMode;
  selectedIds: string[];
  isCanvasOpen: boolean;
  comparisonMode: ComparisonMode;
  auxiliaryData: CanvasPayload | null; // Data passed from chat to canvas
  setView: (view: ViewMode, data?: CanvasPayload | null) => void;
  setIds: (ids: string[]) => void;
  setComparisonMode: (mode: ComparisonMode) => void;
  toggleCanvas: () => void;
  openCanvas: (data?: CanvasPayload | null) => void;
  closeCanvas: () => void;
}

export const useCanvasStore = create<CanvasState>((set) => ({
  activeView: 'NONE',
  selectedIds: [],
  isCanvasOpen: false,
  comparisonMode: 'simple',
  auxiliaryData: null,
  setView: (view, data = null) => set({ activeView: view, auxiliaryData: data }),
  setIds: (ids) => set({ selectedIds: ids }),
  setComparisonMode: (mode) => set({ comparisonMode: mode }),
  toggleCanvas: () => set((state) => ({ isCanvasOpen: !state.isCanvasOpen })),
  openCanvas: (data = null) => set({ isCanvasOpen: true, auxiliaryData: data }),
  closeCanvas: () => set({ isCanvasOpen: false, auxiliaryData: null }),
}));
