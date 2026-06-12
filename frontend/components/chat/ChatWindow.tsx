'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, Sparkles, Trash2 } from 'lucide-react';
import { useCanvasStore } from '@/store/useCanvasStore';
import { AssetType, ComparisonViewMode, ConversationContext, ExplanationMode, initialMessages, Message, ResearchDepth, useChatStore } from '@/store/useChatStore';
import { hasSupabaseBrowserEnv, supabaseBrowser } from '@/lib/supabaseBrowser';
import Magnetic from '@/components/ui/Magnetic';

const markdownComponents = {
  h1: (props: React.ComponentProps<'h1'>) => <h1 className="mb-3 mt-1 text-lg font-bold text-white" {...props} />,
  h2: (props: React.ComponentProps<'h2'>) => <h2 className="mb-2 mt-4 text-base font-semibold text-slate-100" {...props} />,
  h3: (props: React.ComponentProps<'h3'>) => <h3 className="mb-2 mt-3 text-sm font-semibold text-slate-200" {...props} />,
  p: (props: React.ComponentProps<'p'>) => <p className="mb-2 leading-7 text-slate-100" {...props} />,
  ul: (props: React.ComponentProps<'ul'>) => <ul className="mb-3 list-disc space-y-1 pl-5" {...props} />,
  ol: (props: React.ComponentProps<'ol'>) => <ol className="mb-3 list-decimal space-y-1 pl-5" {...props} />,
  li: (props: React.ComponentProps<'li'>) => <li className="leading-7 text-slate-100" {...props} />,
  blockquote: (props: React.ComponentProps<'blockquote'>) => <blockquote className="mb-3 border-l-2 border-[#66a3ff]/60 pl-3 text-slate-200" {...props} />,
  a: (props: React.ComponentProps<'a'>) => (
    <a
      className="text-[#66a3ff] underline underline-offset-2 hover:text-[#cce0ff]"
      target="_blank"
      rel="noreferrer"
      {...props}
    />
  ),
  table: (props: React.ComponentProps<'table'>) => (
    <div className="mb-3 overflow-x-auto rounded-lg border border-white/10">
      <table className="min-w-full border-collapse text-xs sm:text-sm" {...props} />
    </div>
  ),
  thead: (props: React.ComponentProps<'thead'>) => <thead className="bg-white/[0.06] text-slate-100" {...props} />,
  tbody: (props: React.ComponentProps<'tbody'>) => <tbody className="bg-[#0b1325]/65" {...props} />,
  tr: (props: React.ComponentProps<'tr'>) => <tr className="border-t border-white/10" {...props} />,
  th: (props: React.ComponentProps<'th'>) => <th className="px-3 py-2 text-left font-semibold" {...props} />,
  td: (props: React.ComponentProps<'td'>) => <td className="px-3 py-2 align-top text-slate-100" {...props} />,
  code: (props: React.ComponentProps<'code'>) => <code className="rounded bg-white/[0.08] px-1.5 py-0.5 text-[#cce0ff]" {...props} />,
  hr: (props: React.ComponentProps<'hr'>) => <hr className="my-3 border-white/10" {...props} />,
};

function contextFromMessageMetadata(messages: Message[]): ConversationContext {
  for (const message of [...messages].reverse()) {
    const context = message.metadata?.conversation_context;
    if (context && typeof context === 'object' && ('last_compare' in context || 'last_portfolio' in context)) {
      return context as ConversationContext;
    }
  }
  return {};
}

type SuggestionTemplate = {
  id: string;
  label: string;
  prompt: string;
  assetType?: AssetType;
  explanationMode?: ExplanationMode;
};

const defaultTemplates: SuggestionTemplate[] = [
  {
    id: 'mf-deep-dive',
    label: 'Mutual Fund Deep Dive',
    prompt: 'Create a mutual fund deep dive for Parag Parikh Flexi Cap and ICICI Multi Asset Fund with returns, risk, cost, freshness, and missing data.',
    assetType: 'mutual_fund',
    explanationMode: 'advanced',
  },
  {
    id: 'risk-analysis',
    label: 'Risk Analysis',
    prompt: 'Show the key risks, stale data, missing fields, and confidence limits for this comparison.',
    explanationMode: 'beginner',
  },
  {
    id: 'sip-fit',
    label: 'SIP Research Fit',
    prompt: 'Compare these funds for long-term SIP research fit using return consistency, volatility, drawdown, expense ratio, and source freshness.',
    assetType: 'mutual_fund',
    explanationMode: 'beginner',
  },
];

const stockTemplates: SuggestionTemplate[] = [
  {
    id: 'stock-deep-dive',
    label: 'Stock Deep Dive',
    prompt: 'Create a stock deep dive with valuation, growth, profitability, debt risk, price trend, data freshness, and missing fields.',
    assetType: 'stock',
    explanationMode: 'advanced',
  },
  {
    id: 'news-impact',
    label: 'News Impact',
    prompt: 'Check recent news impact and clearly separate verified data from missing or stale data.',
    assetType: 'stock',
    explanationMode: 'beginner',
  },
  {
    id: 'expensive-now',
    label: 'Expensive Now?',
    prompt: 'Is this stock expensive based on available valuation metrics, growth, debt, and data confidence? Keep it research-only.',
    assetType: 'stock',
    explanationMode: 'beginner',
  },
];

function buildSuggestionTemplates(assetType: AssetType, context: ConversationContext): SuggestionTemplate[] {
  const lastCompare = context.last_compare;
  if (lastCompare?.entities?.length) {
    const entities = lastCompare.entities.join(' vs ');
    return [
      {
        id: 'context-risk',
        label: 'Key Risks',
        prompt: `Show the key risks for ${entities}, including stale data, missing fields, confidence, and what should be verified next.`,
        assetType: lastCompare.asset_type,
        explanationMode: 'beginner',
      },
      {
        id: 'context-benchmark',
        label: 'Benchmark Compare',
        prompt: `Compare ${entities} against the relevant benchmark context using available returns, risk, cost, and data freshness.`,
        assetType: lastCompare.asset_type,
        explanationMode: 'advanced',
      },
      {
        id: 'context-long-term',
        label: 'Long-Term View',
        prompt: `Build a long-term investor research view for ${entities} without recommendation language.`,
        assetType: lastCompare.asset_type,
        explanationMode: 'beginner',
      },
    ];
  }
  return assetType === 'stock' ? stockTemplates : defaultTemplates;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' ? value as Record<string, unknown> : null;
}

function MessageMetadataBadges({ metadata, content }: { metadata?: Record<string, unknown> | null; content: string }) {
  const sourceFreshness = asRecord(metadata?.source_freshness);
  const confidence = asRecord(metadata?.confidence);
  const riskAnalysis = asRecord(metadata?.risk_analysis);
  const dataQuality = asRecord(metadata?.data_quality);
  const sourceRows = sourceFreshness ? Object.entries(sourceFreshness).slice(0, 2) : [];
  const riskItems = Array.isArray(riskAnalysis?.items) ? riskAnalysis.items : [];
  const missingCount = dataQuality
    ? Object.values(dataQuality).reduce((count: number, value) => {
        const row = asRecord(value);
        const missing = row?.missing_fields;
        return count + (Array.isArray(missing) ? missing.length : 0);
      }, 0)
    : 0;

  if (content.toLowerCase().includes('coverage pending')) {
    return (
      <span className="rounded-full border border-amber-400/20 bg-amber-400/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-amber-200">
        Coverage pending
      </span>
    );
  }

  if (!metadata || (!sourceRows.length && !confidence?.label && !riskItems.length && !missingCount)) {
    return (
      <span className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-300">
        Source metadata pending
      </span>
    );
  }

  return (
    <>
      {confidence?.label ? (
        <span className="rounded-full border border-[#66a3ff]/20 bg-[#66a3ff]/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-[#cce0ff]">
          Confidence {String(confidence.label)}
        </span>
      ) : null}
      {sourceRows.map(([entity, raw]) => {
        const row = asRecord(raw) || {};
        const stale = Boolean(row.stale);
        const lastUpdated = row.snapshot_last_updated || row.price_date || row.nav_date;
        return (
          <span
            key={entity}
            className={`rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] ${
              stale
                ? 'border-amber-400/20 bg-amber-400/10 text-amber-200'
                : 'border-emerald-400/20 bg-emerald-400/10 text-emerald-200'
            }`}
          >
            {stale ? 'Stale' : 'Fresh'} {lastUpdated ? String(lastUpdated) : entity}
          </span>
        );
      })}
      {riskItems.length ? (
        <span className="rounded-full border border-rose-300/20 bg-rose-300/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-rose-100">
          {riskItems.length} risk flags
        </span>
      ) : null}
      {missingCount ? (
        <span className="rounded-full border border-amber-400/20 bg-amber-400/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-amber-200">
          {missingCount} missing fields
        </span>
      ) : null}
    </>
  );
}

export default function ChatWindow({ isFullScreen = false }: { isFullScreen?: boolean }) {
  const searchParams = useSearchParams();
  const { setView, setIds, openCanvas, closeCanvas } = useCanvasStore();
  const messages = useChatStore((state) => state.messages);
  const input = useChatStore((state) => state.input);
  const isProcessing = useChatStore((state) => state.isProcessing);
  const assetType = useChatStore((state) => state.assetType);
  const researchDepth = useChatStore((state) => state.researchDepth);
  const explanationMode = useChatStore((state) => state.explanationMode);
  const comparisonViewMode = useChatStore((state) => state.comparisonViewMode);
  const conversationContext = useChatStore((state) => state.conversationContext);
  const setInput = useChatStore((state) => state.setInput);
  const setIsProcessing = useChatStore((state) => state.setIsProcessing);
  const setAssetType = useChatStore((state) => state.setAssetType);
  const setResearchDepth = useChatStore((state) => state.setResearchDepth);
  const setExplanationMode = useChatStore((state) => state.setExplanationMode);
  const setComparisonViewMode = useChatStore((state) => state.setComparisonViewMode);
  const setConversationContext = useChatStore((state) => state.setConversationContext);
  const setMessages = useChatStore((state) => state.setMessages);
  const addMessage = useChatStore((state) => state.addMessage);
  const resetMessages = useChatStore((state) => state.resetMessages);
  const pendingQuery = useChatStore((state) => state.pendingQuery);
  const setPendingQuery = useChatStore((state) => state.setPendingQuery);
  const [isHistoryReady, setIsHistoryReady] = useState(!hasSupabaseBrowserEnv);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const initialQuerySentRef = useRef(false);
  const suggestionTemplates = buildSuggestionTemplates(assetType, conversationContext);

  const getAccessToken = useCallback(async () => {
    if (!hasSupabaseBrowserEnv) return null;
    const { data } = await supabaseBrowser.auth.getSession();
    return data.session?.access_token ?? null;
  }, []);

  useEffect(() => {
    const scrollEl = scrollRef.current;
    const contentEl = contentRef.current;
    if (!scrollEl || !contentEl) return;

    const scrollToBottom = () => {
      scrollEl.scrollTop = scrollEl.scrollHeight;
    };

    // Scroll to bottom immediately
    scrollToBottom();

    // Create ResizeObserver to observe size changes of content and container
    const observer = new ResizeObserver(() => {
      scrollToBottom();
    });

    observer.observe(contentEl);
    observer.observe(scrollEl);

    return () => observer.disconnect();
  }, [messages, isProcessing]);

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 150)}px`;
  };

  const applySuggestion = (template: SuggestionTemplate) => {
    setInput(template.prompt);
    if (template.assetType) setAssetType(template.assetType);
    if (template.explanationMode) setExplanationMode(template.explanationMode);
  };

  useEffect(() => {
    let ignore = false;

    const loadHistory = async () => {
      const token = await getAccessToken();
      if (!token) {
        if (!ignore) setIsHistoryReady(true);
        return;
      }

      setIsHistoryLoading(true);
      try {
        const res = await fetch('/api/chat/history', {
          headers: { Authorization: `Bearer ${token}` },
          cache: 'no-store',
        });
        if (!res.ok) return;

        const payload = await res.json();
        const savedMessages: Message[] = Array.isArray(payload?.messages)
          ? payload.messages
              .filter((message: Message) => message?.id && (message.role === 'user' || message.role === 'system') && message.content)
              .map((message: Message) => ({
                id: message.id,
                role: message.role,
                content: message.content,
                metadata: message.metadata || null,
              }))
          : [];

        if (!ignore && savedMessages.length > 0) {
          setMessages([...initialMessages, ...savedMessages]);
          setConversationContext(contextFromMessageMetadata(savedMessages));
        }
      } catch (error) {
        console.error('Chat history load failed:', error);
      } finally {
        if (!ignore) {
          setIsHistoryLoading(false);
          setIsHistoryReady(true);
        }
      }
    };

    void loadHistory();

    return () => {
      ignore = true;
    };
  }, [getAccessToken, setConversationContext, setMessages]);

  const sendQuery = useCallback(async (
    queryText: string,
    selectedAssetType: AssetType = assetType,
    selectedResearchDepth: ResearchDepth = researchDepth,
    selectedExplanationMode: ExplanationMode = explanationMode,
    selectedComparisonViewMode: ComparisonViewMode = comparisonViewMode,
  ) => {
    const text = queryText.trim();
    if (!text) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      metadata: { explanation_mode: selectedExplanationMode },
    };
    addMessage(userMsg);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    setIsProcessing(true);

    try {
      const requestHistory = messages
        .filter((message) => message.id !== '1' && (message.role === 'user' || message.role === 'system') && message.content.trim())
        .slice(-12)
        .map((message) => ({
          role: message.role,
          content: message.content.slice(0, 4000),
        }));
      const token = await getAccessToken();
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (token) headers.Authorization = `Bearer ${token}`;

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          query: text,
          asset_type: selectedAssetType,
          research_depth: selectedResearchDepth,
          explanation_mode: selectedExplanationMode,
          comparison_view_mode: selectedComparisonViewMode,
          history: requestHistory,
          conversation_context: conversationContext,
        }),
      });

      if (!res.ok) throw new Error('API Error');
      const data = await res.json();

      if (data.system_action?.type === 'COMPARE') {
        if (selectedComparisonViewMode === 'canvas') {
          setIds(data.system_action.ids);
          setView('COMPARISON', data);
          openCanvas(data);
        } else {
          closeCanvas();
        }
      }
      if (data.system_action?.type === 'PORTFOLIO_REVIEW') {
        setIds([]);
        setView('PORTFOLIO_REVIEW', data);
        openCanvas(data);
      }

      const nextConversationContext = data.conversation_context
        ? { ...conversationContext, ...data.conversation_context }
        : conversationContext;
      if (data.conversation_context) {
        setConversationContext(nextConversationContext);
      }

      addMessage({
        id: Date.now().toString(),
        role: 'system',
        content: data.answer,
        metadata: {
          conversation_context: nextConversationContext,
          source_freshness: data.source_freshness || null,
          data_quality: data.data_quality || null,
          risk_analysis: data.risk_analysis || null,
          confidence: data.confidence || null,
          explanation_mode: data.explanation_mode || selectedExplanationMode,
        },
      });
    } catch {
      addMessage({ id: Date.now().toString(), role: 'system', content: 'Coverage pending: FundersAI core is not reachable. Try again when the research service is running.' });
    } finally {
      setIsProcessing(false);
    }
  }, [addMessage, assetType, closeCanvas, comparisonViewMode, conversationContext, explanationMode, getAccessToken, messages, openCanvas, researchDepth, setConversationContext, setIds, setInput, setIsProcessing, setView]);

  useEffect(() => {
    if (!isHistoryReady) return;
    if (initialQuerySentRef.current) return;
    const query = searchParams.get('query')?.trim();
    if (!query) return;

    initialQuerySentRef.current = true;
    const selectedAssetType = searchParams.get('asset_type');
    const nextAssetType: AssetType =
      selectedAssetType === 'stock' || selectedAssetType === 'mutual_fund' ? selectedAssetType : 'auto';
    const selectedResearchDepth = searchParams.get('research_depth');
    const nextResearchDepth: ResearchDepth = selectedResearchDepth === 'deep' ? 'deep' : 'standard';
    const selectedExplanationMode = searchParams.get('explanation_mode');
    const nextExplanationMode: ExplanationMode =
      selectedExplanationMode === 'advanced' || nextResearchDepth === 'deep' ? 'advanced' : 'beginner';

    setAssetType(nextAssetType);
    setExplanationMode(nextExplanationMode);
    setResearchDepth(nextExplanationMode === 'advanced' ? 'deep' : nextResearchDepth);
    void sendQuery(query, nextAssetType, nextExplanationMode === 'advanced' ? 'deep' : nextResearchDepth, nextExplanationMode, comparisonViewMode);
  }, [comparisonViewMode, isHistoryReady, searchParams, sendQuery, setAssetType, setExplanationMode, setResearchDepth]);

  useEffect(() => {
    if (pendingQuery) {
      void sendQuery(pendingQuery);
      setPendingQuery(null);
    }
  }, [pendingQuery, sendQuery, setPendingQuery]);

  const handleSend = async () => {
    await sendQuery(input, assetType, researchDepth, explanationMode, comparisonViewMode);
  };

  const handleClearHistory = async () => {
    resetMessages();
    const token = await getAccessToken();
    if (!token) return;
    await fetch('/api/chat/history', {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    }).catch((error) => console.error('Chat history clear failed:', error));
  };

  return (
    <section className={`flex h-full min-h-0 w-full flex-col ${
      isFullScreen
        ? 'bg-transparent border-none'
        : 'rounded-[1.3rem] border border-white/10 bg-[#07111f] shadow-[0_18px_40px_rgba(0,0,0,0.38)]'
    }`}>
      <header className={`flex items-center justify-between border-white/10 px-4 py-3 sm:px-5 ${isFullScreen ? 'border-b-0' : 'border-b'}`}>
        <div className="flex items-center gap-2.5">
          <div className="grid h-7 w-7 place-items-center rounded-md bg-[linear-gradient(135deg,#67b2ff,#3b82f6)] text-white shadow-[0_8px_16px_rgba(59,130,246,0.35)]">
            <Sparkles className="h-3.5 w-3.5" />
          </div>
          <div>
            <h2 className="text-sm font-semibold tracking-tight text-white">FundersAI</h2>
            <p className="text-[11px] text-slate-400">Ask, compare, and inspect source-backed metrics</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isHistoryLoading ? (
            <span className="rounded-full border border-[#66a3ff]/30 bg-[#66a3ff]/10 px-2.5 py-1 text-[11px] font-semibold text-[#66a3ff]">
              Loading
            </span>
          ) : null}
          <button
            type="button"
            className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-white/10 bg-white/[0.04] text-slate-300 transition hover:border-rose-300/45 hover:text-rose-200 disabled:cursor-not-allowed disabled:opacity-50"
            onClick={handleClearHistory}
            disabled={isProcessing}
            aria-label="Clear chat history"
            title="Clear chat history"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
          <span className="rounded-full border border-[#007acc]/30 bg-[#007acc]/12 px-2.5 py-1 text-[11px] font-semibold text-[#66a3ff]">
            Research only
          </span>
        </div>
      </header>

      <div ref={scrollRef} className="custom-scroll flex min-h-0 flex-1 flex-col overflow-y-auto px-3 pt-4 sm:px-5">
        <div ref={contentRef} className="flex flex-col gap-3 pb-8">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={
                msg.role === 'user'
                  ? 'ml-auto w-fit max-w-[85%] rounded-2xl border border-[#66a3ff]/30 bg-[#66a3ff]/10 px-4 py-3 text-sm text-[#f3f8ff]'
                  : 'mr-auto max-w-[92%] rounded-2xl border border-white/10 bg-[#0f172a] px-4 py-3 text-sm leading-relaxed text-slate-100'
              }
            >
              {msg.role === 'system' ? (
                <div className="chat-markdown text-sm">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                    {msg.content}
                  </ReactMarkdown>
                  {msg.id !== '1' && (
                    <div className="mt-3 flex flex-wrap gap-2 border-t border-white/5 pt-3">
                      <MessageMetadataBadges metadata={msg.metadata} content={msg.content} />
                    </div>
                  )}
                </div>
              ) : (
                msg.content
              )}
              {msg.id === '1' && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {suggestionTemplates.map((template) => (
                    <Magnetic key={template.id}>
                      <button
                        className="rounded-full border border-white/15 bg-white/[0.05] px-2.5 py-1 text-xs text-slate-200 transition hover:border-[#66a3ff]/45 hover:text-white"
                        onClick={() => applySuggestion(template)}
                      >
                        {template.label}
                      </button>
                    </Magnetic>
                  ))}
                </div>
              )}
            </div>
          ))}

          <div className="rounded-xl border border-amber-300/25 bg-amber-400/10 px-3 py-2 text-xs text-amber-100/90">
            This is not investment advice. Verify data independently.
          </div>
        </div>
      </div>
      <div className={`${isFullScreen ? 'bg-transparent' : 'border-t border-white/10 bg-[#07111f]'} p-3 sm:p-4 pb-8`}>
        {isProcessing && (
          <div className="mb-3 rounded-lg border border-[#66a3ff]/20 bg-[#66a3ff]/5 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-[#66a3ff] animate-pulse">
            Thinking…
          </div>
        )}

        <div className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-[#0f172a] p-2 transition-all duration-300 focus-within:border-[#66a3ff]/40 focus-within:bg-[#0f172a]/80 focus-within:ring-4 focus-within:ring-[#66a3ff]/10">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder={
              assetType === 'mutual_fund'
                ? 'Compare PPFAS and ICICI funds for long-term consistency…'
                : assetType === 'stock'
                ? 'Stock research is in progress. Try fund comparison prompts.'
                : 'Ask for PPFAS vs ICICI comparison, risk, cost, or NAV view…'
            }
            rows={1}
            name="chat_message"
            autoComplete="off"
            aria-label="Type your message"
            className="max-h-28 min-h-[2.5rem] w-full resize-none bg-transparent px-3 py-2 text-sm text-slate-100 placeholder:text-slate-400 focus:outline-none"
          />

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-white/5 pt-2 px-1">
            <div className="flex flex-wrap items-center gap-2">
              {/* Asset Type selector */}
              <div className="inline-flex rounded-full bg-white/[0.03] p-1 border border-white/5 gap-1">
                {[
                  { label: 'Auto', value: 'auto' },
                  { label: 'Stocks', value: 'stock' },
                  { label: 'Funds', value: 'mutual_fund' },
                ].map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    className={`rounded-full px-2.5 py-1 text-[10px] font-bold tracking-wide transition-all ${
                      assetType === option.value
                        ? 'bg-[#00509e]/20 border border-[#66a3ff]/30 text-[#66a3ff]'
                        : 'text-slate-400 hover:text-white border border-transparent'
                    }`}
                    onClick={() => setAssetType(option.value as AssetType)}
                    disabled={isProcessing}
                  >
                    {option.label}
                  </button>
                ))}
              </div>

              {/* Explanation mode selector */}
              <div className="inline-flex rounded-full bg-white/[0.03] p-1 border border-white/5 gap-1">
                {[
                  { label: 'Beginner', value: 'beginner' },
                  { label: 'Advanced', value: 'advanced' },
                ].map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    className={`rounded-full px-2.5 py-1 text-[10px] font-bold tracking-wide transition-all ${
                      explanationMode === option.value
                        ? 'bg-emerald-400/15 border border-emerald-300/30 text-emerald-100'
                        : 'text-slate-400 hover:text-white border border-transparent'
                    }`}
                    onClick={() => setExplanationMode(option.value as ExplanationMode)}
                    disabled={isProcessing}
                  >
                    {option.label}
                  </button>
                ))}
              </div>

              {/* View Mode selector */}
              <div className="inline-flex rounded-full bg-white/[0.03] p-1 border border-white/5 gap-1">
                {[
                  { label: 'Canvas', value: 'canvas' },
                  { label: 'Chat', value: 'chat' },
                ].map((option) => (
                  <button
                    key={option.value}
                    type="button"
                    className={`rounded-full px-2.5 py-1 text-[10px] font-bold tracking-wide transition-all ${
                      comparisonViewMode === option.value
                        ? 'bg-[#007acc]/20 border border-[#007acc]/30 text-[#66a3ff]'
                        : 'text-slate-400 hover:text-white border border-transparent'
                    }`}
                    onClick={() => setComparisonViewMode(option.value as ComparisonViewMode)}
                    disabled={isProcessing}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            <Magnetic>
              <button
                onClick={handleSend}
                aria-label="Send Message"
                disabled={isProcessing || !input.trim()}
                className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-[#66a3ff] text-slate-950 transition-all hover:bg-[#66a3ff]/80 hover:scale-105 active:scale-95 disabled:scale-100 disabled:cursor-not-allowed disabled:bg-white/5 disabled:text-slate-600"
              >
                <Send size={15} />
              </button>
            </Magnetic>
          </div>
        </div>
      </div>
    </section>
  );
}
