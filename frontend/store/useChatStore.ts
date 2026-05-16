import { create } from 'zustand';

export type AssetType = 'auto' | 'stock' | 'mutual_fund';
export type ResearchDepth = 'standard' | 'deep';
export type ComparisonViewMode = 'canvas' | 'chat';

export type Message = {
  id: string;
  role: 'user' | 'system';
  content: string;
};

const initialMessages: Message[] = [
  {
    id: '1',
    role: 'system',
    content: 'Welcome to MarketMind. I monitor NSE/BSE quant data and latest financial news. How can I assist your market research today?',
  },
];

interface ChatState {
  messages: Message[];
  input: string;
  isProcessing: boolean;
  assetType: AssetType;
  researchDepth: ResearchDepth;
  comparisonViewMode: ComparisonViewMode;
  setInput: (input: string) => void;
  setIsProcessing: (isProcessing: boolean) => void;
  setAssetType: (assetType: AssetType) => void;
  setResearchDepth: (researchDepth: ResearchDepth) => void;
  setComparisonViewMode: (comparisonViewMode: ComparisonViewMode) => void;
  addMessage: (message: Message) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: initialMessages,
  input: '',
  isProcessing: false,
  assetType: 'auto',
  researchDepth: 'standard',
  comparisonViewMode: 'canvas',
  setInput: (input) => set({ input }),
  setIsProcessing: (isProcessing) => set({ isProcessing }),
  setAssetType: (assetType) => set({ assetType }),
  setResearchDepth: (researchDepth) => set({ researchDepth }),
  setComparisonViewMode: (comparisonViewMode) => set({ comparisonViewMode }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
}));
