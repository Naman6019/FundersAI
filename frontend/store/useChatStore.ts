import { create } from 'zustand';

export type AssetType = 'auto' | 'stock' | 'mutual_fund';
export type ResearchDepth = 'standard' | 'deep';
export type ComparisonViewMode = 'canvas' | 'chat';

export type Message = {
  id: string;
  role: 'user' | 'system';
  content: string;
  metadata?: Record<string, unknown> | null;
};

export type LastCompareContext = {
  asset_type: 'stock' | 'mutual_fund';
  entities: string[];
  ids: string[];
  query?: string | null;
  last_focus?: string | null;
  available_topics?: string[];
};

export type LastPortfolioContext = {
  query?: string | null;
  score?: number | null;
  label?: string | null;
  holdings?: Array<Record<string, unknown>>;
  buckets?: Record<string, number>;
  overlap?: Record<string, unknown>;
  available_topics?: string[];
};

export type ConversationContext = {
  last_compare?: LastCompareContext | null;
  last_portfolio?: LastPortfolioContext | null;
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
  conversationContext: ConversationContext;
  pendingQuery: string | null;
  setPendingQuery: (query: string | null) => void;
  setInput: (input: string) => void;
  setIsProcessing: (isProcessing: boolean) => void;
  setAssetType: (assetType: AssetType) => void;
  setResearchDepth: (researchDepth: ResearchDepth) => void;
  setComparisonViewMode: (comparisonViewMode: ComparisonViewMode) => void;
  setConversationContext: (conversationContext: ConversationContext) => void;
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
  conversationContext: {},
  pendingQuery: null,
  setPendingQuery: (pendingQuery) => set({ pendingQuery }),
  setInput: (input) => set({ input }),
  setIsProcessing: (isProcessing) => set({ isProcessing }),
  setAssetType: (assetType) => set({ assetType }),
  setResearchDepth: (researchDepth) => set({ researchDepth }),
  setComparisonViewMode: (comparisonViewMode) => set({ comparisonViewMode }),
  setConversationContext: (conversationContext) => set({ conversationContext }),
  setMessages: (messages) => set({ messages }),
  addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
  resetMessages: () => set({ messages: initialMessages, conversationContext: {} }),
}));
