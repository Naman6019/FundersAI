import { create } from 'zustand';
import type { CanvasPayload } from '@/types/funds';

type ViewMode = 'NONE' | 'STOCK_DETAIL' | 'MF_DETAIL' | 'COMPARISON';

interface CanvasState {
  activeView: ViewMode;
  selectedIds: string[];
  isCanvasOpen: boolean;
  auxiliaryData: CanvasPayload | null; // Data passed from chat to canvas
  setView: (view: ViewMode, data?: CanvasPayload | null) => void;
  setIds: (ids: string[]) => void;
  toggleCanvas: () => void;
  openCanvas: (data?: CanvasPayload | null) => void;
  closeCanvas: () => void;
}

export const useCanvasStore = create<CanvasState>((set) => ({
  activeView: 'NONE',
  selectedIds: [],
  isCanvasOpen: false,
  auxiliaryData: null,
  setView: (view, data = null) => set({ activeView: view, auxiliaryData: data }),
  setIds: (ids) => set({ selectedIds: ids }),
  toggleCanvas: () => set((state) => ({ isCanvasOpen: !state.isCanvasOpen })),
  openCanvas: (data = null) => set({ isCanvasOpen: true, auxiliaryData: data }),
  closeCanvas: () => set({ isCanvasOpen: false, auxiliaryData: null }),
}));
