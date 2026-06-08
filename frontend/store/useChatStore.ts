import { create } from 'zustand';

export type AssetType = 'auto' | 'stock' | 'mutual_fund';
export type ResearchDepth = 'standard' | 'deep';
export type ComparisonViewMode = 'canvas' | 'chat';

export type Message = {
  id: string;
  role: 'user' | 'system';
  content: string;
};

export const initialMessages: Message[] = [
  {
    id: '1',
    role: 'system',
    content: 'Welcome to FundersAI. Compare Indian mutual funds across returns, cost, Sharpe, risk, and NAV freshness with explainable research context.',
  },
];

interface ChatState {
  messages: Message[];
  input: string;
  isProcessing: boolean;
  assetType: AssetType;
  researchDepth: ResearchDepth;
  comparisonViewMode: ComparisonViewMode;
  pendingQuery: string | null;
  setPendingQuery: (query: string | null) => void;
  setInput: (input: string) => void;
  setIsProcessing: (isProcessing: boolean) => void;
  setAssetType: (assetType: AssetType) => void;
  setResearchDepth: (researchDepth: ResearchDepth) => void;
  setComparisonViewMode: (comparisonViewMode: ComparisonViewMode) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  resetMessages: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: initialMessages,
  input: '',
  isProcessing: false,
  assetType: 'auto',
  researchDepth: 'standard',
  comparisonViewMode: 'canvas',
  pendingQuery: null,
  setPendingQuery: (pendingQuery) => set({ pendingQuery }),
  setInput: (input) => set({ input }),
  setIsProcessing: (isProcessing) => set({ isProcessing }),
  setAssetType: (assetType) => set({ assetType }),
  setResearchDepth: (researchDepth) => set({ researchDepth }),
  setComparisonViewMode: (comparisonViewMode) => set({ comparisonViewMode }),
  setMessages: (messages) => set({ messages }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  resetMessages: () => set({ messages: initialMessages }),
}));
