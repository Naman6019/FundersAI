import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { hasSupabaseBrowserEnv, supabaseBrowser } from '@/lib/supabaseBrowser';

export type AssetType = 'auto' | 'stock' | 'mutual_fund';
export type ResearchDepth = 'standard' | 'deep';
export type ExplanationMode = 'beginner' | 'advanced';
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

export type ChatSession = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
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
  explanationMode: ExplanationMode;
  comparisonViewMode: ComparisonViewMode;
  conversationContext: ConversationContext;
  pendingQuery: string | null;
  setPendingQuery: (query: string | null) => void;
  setInput: (input: string) => void;
  setIsProcessing: (isProcessing: boolean) => void;
  setAssetType: (assetType: AssetType) => void;
  setResearchDepth: (researchDepth: ResearchDepth) => void;
  setExplanationMode: (explanationMode: ExplanationMode) => void;
  setComparisonViewMode: (comparisonViewMode: ComparisonViewMode) => void;
  setConversationContext: (conversationContext: ConversationContext) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  resetMessages: () => void;
  currentSessionId: string | null;
  sessions: ChatSession[];
  setCurrentSessionId: (id: string | null) => void;
  setSessions: (sessions: ChatSession[]) => void;
  fetchSessions: () => Promise<void>;
  createNewSession: (title?: string) => Promise<string | null>;
  loadSessionMessages: (sessionId: string) => Promise<void>;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      messages: initialMessages,
      input: '',
      isProcessing: false,
      assetType: 'auto',
      researchDepth: 'standard',
      explanationMode: 'beginner',
      comparisonViewMode: 'canvas',
      conversationContext: {},
      pendingQuery: null,
      setPendingQuery: (pendingQuery) => set({ pendingQuery }),
      setInput: (input) => set({ input }),
      setIsProcessing: (isProcessing) => set({ isProcessing }),
      setAssetType: (assetType) => set({ assetType }),
      setResearchDepth: (researchDepth) => set({ researchDepth }),
      setExplanationMode: (explanationMode) => set({
        explanationMode,
        researchDepth: explanationMode === 'advanced' ? 'deep' : 'standard',
      }),
      setComparisonViewMode: (comparisonViewMode) => set({ comparisonViewMode }),
      setConversationContext: (conversationContext) => set({ conversationContext }),
      setMessages: (messages) => set({ messages }),
      addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),
      resetMessages: () => set({ messages: initialMessages, conversationContext: {}, currentSessionId: null }),
      currentSessionId: null,
      sessions: [],
      setCurrentSessionId: (id) => set({ currentSessionId: id }),
      setSessions: (sessions) => set({ sessions }),
      fetchSessions: async () => {
        try {
          if (!hasSupabaseBrowserEnv) return;
          const { data: authData } = await supabaseBrowser.auth.getSession();
          const token = authData?.session?.access_token;

          const headers: Record<string, string> = {};
          if (token) headers.Authorization = `Bearer ${token}`;

          const res = await fetch('/api/chat/sessions', { headers });
          if (res.ok) {
            const data = await res.json();
            set({ sessions: data.sessions || [] });
          }
        } catch (e) {
          console.error(e);
        }
      },
      createNewSession: async (title = 'New Chat') => {
        try {
          let token = null;
          if (hasSupabaseBrowserEnv) {
            const { data: authData } = await supabaseBrowser.auth.getSession();
            token = authData?.session?.access_token;
          }

          const headers: Record<string, string> = { 'Content-Type': 'application/json' };
          if (token) headers.Authorization = `Bearer ${token}`;

          const res = await fetch('/api/chat/sessions', {
            method: 'POST',
            body: JSON.stringify({ title }),
            headers,
          });
          if (res.ok) {
            const data = await res.json();
            const session = data.session;
            set((state) => ({
              sessions: [session, ...state.sessions],
              currentSessionId: session.id,
            }));
            return session.id;
          }
        } catch (e) {
          console.error(e);
        }
        return null;
      },
      loadSessionMessages: async (sessionId: string) => {
        try {
          let token = null;
          if (hasSupabaseBrowserEnv) {
            const { data: authData } = await supabaseBrowser.auth.getSession();
            token = authData?.session?.access_token;
          }

          const headers: Record<string, string> = {};
          if (token) headers.Authorization = `Bearer ${token}`;

          const res = await fetch(`/api/chat/sessions/${sessionId}`, { headers });
          if (res.ok) {
            const data = await res.json();
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const msgs = data.messages?.map((m: any) => ({
              id: m.id,
              role: m.role,
              content: m.content,
              metadata: m.metadata
            })) || [];

            set({
              currentSessionId: sessionId,
              messages: msgs.length > 0 ? msgs : initialMessages
            });
          }
        } catch (e) {
          console.error(e);
        }
      },
    }),
    {
      name: 'fundersai-chat-preferences',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        assetType: state.assetType,
        researchDepth: state.researchDepth,
        explanationMode: state.explanationMode,
        comparisonViewMode: state.comparisonViewMode,
      }),
    },
  ),
);
