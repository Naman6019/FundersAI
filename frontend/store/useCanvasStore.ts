import { create } from 'zustand';
import type { CanvasPayload } from '@/types/funds';

export type ViewMode = 'NONE' | 'STOCK_DETAIL' | 'MF_DETAIL' | 'COMPARISON' | 'COMPARISON_GRAPH_ONLY' | 'PORTFOLIO_REVIEW' | 'CATEGORY_COMPARE';

interface CanvasState {
  activeView: ViewMode;
  selectedIds: string[];
  isCanvasOpen: boolean;
  auxiliaryData: CanvasPayload | null; // Data passed from chat to canvas
  setView: (view: ViewMode, data?: CanvasPayload | null) => void;
  setIds: (ids: string[]) => void;
  openCanvas: (payload: { view?: ViewMode; ids?: string[]; data?: CanvasPayload | null }) => void;
  closeCanvas: () => void;
}

export const useCanvasStore = create<CanvasState>((set) => ({
  activeView: 'NONE',
  selectedIds: [],
  isCanvasOpen: false,
  auxiliaryData: null,
  setView: (view, data = null) => set({ activeView: view, auxiliaryData: data }),
  setIds: (ids) => set({ selectedIds: ids }),
  openCanvas: (payload = {}) => set((state) => ({ 
    isCanvasOpen: true, 
    activeView: payload.view !== undefined ? payload.view : state.activeView,
    selectedIds: payload.ids !== undefined ? payload.ids : state.selectedIds,
    auxiliaryData: payload.data !== undefined ? payload.data : state.auxiliaryData 
  })),
  closeCanvas: () => set({ isCanvasOpen: false, auxiliaryData: null }),
}));

// Derived selector to ensure valid combinations
export const useCanvasView = (state: CanvasState) => {
  if (!state.isCanvasOpen) return null;
  if (state.activeView === 'COMPARISON' && state.selectedIds.length !== 2) return null;
  return state.activeView;
};
