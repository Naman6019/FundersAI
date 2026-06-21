'use client';

import { useCallback, useEffect, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, Sparkles, Trash2 } from 'lucide-react';
import { useCanvasStore } from '@/store/useCanvasStore';
import { AssetType, ComparisonViewMode, ConversationContext, ExplanationMode, Message, ResearchDepth, useChatStore } from '@/store/useChatStore';
import { hasSupabaseBrowserEnv, supabaseBrowser } from '@/lib/supabaseBrowser';
import Magnetic from '@/components/ui/Magnetic';
import { motion } from 'framer-motion';
import ComparisonView from '@/components/canvas/ComparisonView';

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
    prompt: 'Create a mutual fund deep dive for Axis Flexi Cap and HDFC Flexi Cap with returns, risk, cost, freshness, and missing data.',
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
  const reasoningSummary = asRecord(metadata?.reasoning_summary);
  const statusFlag = typeof metadata?.status_flag === 'string' ? metadata.status_flag : null;
  const modelStatus = typeof metadata?.model_status === 'string' ? metadata.model_status : null;
  const coverageStatus = typeof metadata?.coverage_status === 'string' ? metadata.coverage_status : null;
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

  if (!metadata || (!sourceRows.length && !confidence?.label && !riskItems.length && !missingCount && !statusFlag && !modelStatus && !coverageStatus && !reasoningSummary)) {
    return (
      <span className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-300">
        Source metadata pending
      </span>
    );
  }

  return (
    <>
      {statusFlag === 'deterministic_fallback' ? (
        <span className="rounded-full border border-amber-400/20 bg-amber-400/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-amber-200">
          Basic comparison shown
        </span>
      ) : null}
      {coverageStatus && coverageStatus !== 'not_applicable' ? (
        <span className="rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-300">
          Coverage {coverageStatus}
        </span>
      ) : null}
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

function statusClass(status: unknown): string {
  if (status === 'ok') return 'border-emerald-400/25 bg-emerald-400/10 text-emerald-100';
  if (status === 'missing') return 'border-rose-300/25 bg-rose-300/10 text-rose-100';
  return 'border-amber-300/25 bg-amber-300/10 text-amber-100';
}

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string' && item.trim().length > 0) : [];
}

function ThinkingSummary({ metadata }: { metadata?: Record<string, unknown> | null }) {
  const summary = asRecord(metadata?.reasoning_summary);
  if (!summary) return null;

  const steps = Array.isArray(summary.steps)
    ? summary.steps.map(asRecord).filter((step): step is Record<string, unknown> => Boolean(step)).slice(0, 4)
    : [];
  const dataUsed = stringList(summary.data_used).slice(0, 5);
  const limits = stringList(summary.limits).slice(0, 4);

  if (!steps.length && !dataUsed.length && !limits.length) return null;

  return (
    <details className="mt-3 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-xs text-slate-200">
      <summary className="cursor-pointer select-none text-[11px] font-semibold uppercase tracking-[0.14em] text-[#cce0ff]">
        Thinking
      </summary>
      <div className="mt-2 space-y-2">
        {steps.length ? (
          <div className="space-y-1.5">
            {steps.map((step, index) => (
              <div key={`${String(step.label || 'step')}-${index}`} className="flex gap-2">
                <span className={`mt-0.5 h-fit rounded-full border px-1.5 py-0.5 text-[9px] font-semibold uppercase ${statusClass(step.status)}`}>
                  {String(step.status || 'limited')}
                </span>
                <p className="m-0 leading-5 text-slate-200">
                  <span className="font-semibold text-slate-100">{String(step.label || 'Step')}:</span>{' '}
                  {String(step.detail || '')}
                </p>
              </div>
            ))}
          </div>
        ) : null}
        {dataUsed.length ? (
          <p className="m-0 leading-5 text-slate-300">Data used: {dataUsed.join('; ')}</p>
        ) : null}
        {limits.length ? (
          <p className="m-0 leading-5 text-amber-100/85">Limits: {limits.join('; ')}</p>
        ) : null}
      </div>
    </details>
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
  const addMessage = useChatStore((state) => state.addMessage);
  const resetMessages = useChatStore((state) => state.resetMessages);
  const currentSessionId = useChatStore((state) => state.currentSessionId);
  const createNewSession = useChatStore((state) => state.createNewSession);
  const pendingQuery = useChatStore((state) => state.pendingQuery);
  const setPendingQuery = useChatStore((state) => state.setPendingQuery);
  const isHistoryReady = true;
  const isHistoryLoading = false;
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

      let activeSessionId = currentSessionId;
      if (!activeSessionId) {
        activeSessionId = await createNewSession(text.substring(0, 30) + '...');
      }

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
          session_id: activeSessionId,
        }),
      });

      if (!res.ok) {
        let errorMessage = res.status === 408 || res.status === 504
          ? 'The research request timed out. Try again in a moment.'
          : 'FundersAI research service returned an error. Try again in a moment.';
        try {
          const errorBody = await res.json();
          if (errorBody?.error === 'token_budget_exceeded') {
            errorMessage = 'Your chat token budget has been reached for this period.';
          } else if (errorBody?.error === 'Upstream Error') {
            errorMessage = 'FundersAI research service could not complete the request in time. Try again in a moment.';
          } else if (typeof errorBody?.error === 'string') {
            errorMessage = errorBody.error;
          }
        } catch {
          // Keep the status-based message when the response body is not JSON.
        }
        throw new Error(errorMessage);
      }
      const data = await res.json();

      if (data.system_action?.type === 'COMPARE') {
        if (selectedComparisonViewMode === 'canvas') {
          setIds(data.system_action.ids);
          setView('COMPARISON', data);
          openCanvas(data);
        } else {
          setIds(data.system_action.ids);
          setView('COMPARISON_GRAPH_ONLY', data);
          openCanvas(data);
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
          trace_id: data.trace_id || null,
          coverage_status: data.coverage_status || null,
          model_status: data.model_status || null,
          status_flag: data.status_flag || null,
          resolution: data.resolution || null,
          explanation_mode: data.explanation_mode || selectedExplanationMode,
          answer_mode: data.answer_mode || null,
          news_context_status: data.news_context_status || null,
          sources: data.sources || null,
          reasoning_summary: data.reasoning_summary || null,
          system_action_type: data.system_action?.type || null,
          system_action_ids: data.system_action?.ids || null,
        },
      });
    } catch (error) {
      const message = error instanceof Error && error.message
        ? error.message
        : 'FundersAI research service is unavailable. Try again in a moment.';
      addMessage({ id: Date.now().toString(), role: 'system', content: message });
    } finally {
      setIsProcessing(false);
    }
  }, [addMessage, assetType, closeCanvas, comparisonViewMode, conversationContext, currentSessionId, createNewSession, explanationMode, getAccessToken, messages, openCanvas, researchDepth, setConversationContext, setIds, setInput, setIsProcessing, setView]);

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

  const isEmpty = messages.length <= 1 && !isProcessing;

  return (
    <div className={`flex flex-col h-full min-h-0 w-full bg-transparent text-white relative overflow-hidden flex-1 ${
      isFullScreen ? '' : ''
    }`}>
      {/* Animated Backgrounds */}
      <div className="absolute inset-0 w-full h-full overflow-hidden pointer-events-none">
          <div className="absolute top-0 left-1/4 w-96 h-96 bg-violet-500/10 rounded-full mix-blend-normal filter blur-[128px] animate-pulse" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-indigo-500/10 rounded-full mix-blend-normal filter blur-[128px] animate-pulse delay-700" />
          <div className="absolute top-1/4 right-1/3 w-64 h-64 bg-fuchsia-500/10 rounded-full mix-blend-normal filter blur-[96px] animate-pulse delay-1000" />
      </div>

      {/* Header */}
      {!isEmpty && (
        <header className="relative z-10 flex items-center justify-between border-b border-white/5 px-4 py-3 sm:px-5 shrink-0 bg-[#050505]/60 backdrop-blur-md">
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
          </div>
        </header>
      )}

      {/* Content Area */}
      <div className={`relative z-10 flex flex-col flex-1 w-full max-w-4xl mx-auto overflow-hidden ${isEmpty ? 'items-center justify-center px-6' : 'px-0'}`}>

        {/* Empty State Centered Hero */}
        {isEmpty && (
          <motion.div
            className="w-full max-w-2xl text-center space-y-3 mb-8"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          >
              <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2, duration: 0.5 }}
                  className="inline-block"
              >
                  <h1 className="text-3xl font-medium tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white/90 to-white/40 pb-1">
                      How can I help today?
                  </h1>
                  <motion.div
                      className="h-px bg-gradient-to-r from-transparent via-white/20 to-transparent"
                      initial={{ width: 0, opacity: 0 }}
                      animate={{ width: "100%", opacity: 1 }}
                      transition={{ delay: 0.5, duration: 0.8 }}
                  />
              </motion.div>
              <motion.p
                  className="text-sm text-white/40"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.3 }}
              >
                  Type a query to compare mutual funds or review your portfolio
              </motion.p>
          </motion.div>
        )}

        {/* Chat Feed */}
        {!isEmpty && (
          <div ref={scrollRef} className="custom-scroll flex min-h-0 flex-1 flex-col overflow-y-auto px-4 pt-4 sm:px-6 w-full">
            <div ref={contentRef} className="flex flex-col gap-5 pb-8 w-full max-w-3xl mx-auto">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={
                    msg.role === 'user'
                      ? 'ml-auto w-fit max-w-[85%] rounded-2xl border border-[#66a3ff]/20 bg-[#66a3ff]/10 px-5 py-3.5 text-sm text-[#f3f8ff] shadow-sm'
                      : 'mr-auto max-w-[92%] rounded-2xl border border-white/5 bg-white/[0.02] backdrop-blur-md px-5 py-3.5 text-sm leading-relaxed text-slate-100 shadow-sm'
                  }
                >
                  {msg.role === 'system' ? (
                    <div className="chat-markdown text-sm">
                      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                        {msg.content}
                      </ReactMarkdown>
                      {msg.id !== '1' && <ThinkingSummary metadata={msg.metadata} />}
                      {msg.metadata?.system_action_type === 'COMPARE' && comparisonViewMode === 'chat' && Array.isArray(msg.metadata?.system_action_ids) && (
                        <div className="mt-4 -mx-2 sm:-mx-4 h-[600px] border border-white/10 rounded-2xl overflow-hidden bg-[#050505]/50">
                          <ComparisonView
                            key={(msg.metadata.system_action_ids as string[]).join('|')}
                            ids={msg.metadata.system_action_ids as string[]}
                            type={(msg.metadata.system_action_ids[0] as string)?.match(/^[0-9]+$/) ? 'MUTUAL_FUND' : 'STOCK'}
                            variant="metrics_only"
                          />
                        </div>
                      )}
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

              {isProcessing && (
                <motion.div
                    className="mr-auto w-fit backdrop-blur-md bg-white/[0.02] rounded-full px-4 py-2 shadow-sm border border-white/[0.05]"
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                >
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-7 rounded-full bg-[linear-gradient(135deg,#67b2ff,#3b82f6)] flex items-center justify-center text-center shadow-[0_4px_8px_rgba(59,130,246,0.2)]">
                            <Sparkles className="h-3 w-3 text-white" />
                        </div>
                        <div className="flex items-center gap-2 text-sm text-white/70">
                            <span>Thinking</span>
                            <TypingDots />
                        </div>
                    </div>
                </motion.div>
              )}

              <div className="mt-2 mx-auto rounded-xl border border-amber-300/10 bg-amber-400/5 px-4 py-2.5 text-xs text-amber-100/70 max-w-md text-center">
                FundersAI provides educational insights. Verify data independently.
              </div>
            </div>
          </div>
        )}

        {/* Input Area */}
        <motion.div
          layout
          className={`shrink-0 w-full ${isEmpty ? 'max-w-2xl' : 'max-w-3xl mx-auto px-4 sm:px-6 pb-6 pt-2'}`}
          initial={isEmpty ? { scale: 0.98 } : false}
          animate={isEmpty ? { scale: 1 } : false}
          transition={{ delay: 0.1 }}
        >
          <div className="relative backdrop-blur-2xl bg-white/[0.02] rounded-2xl border border-white/[0.05] shadow-2xl focus-within:border-[#66a3ff]/30 focus-within:bg-white/[0.03] transition-all duration-300">
            <div className="p-3 sm:p-4">
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
                    ? 'Compare Axis Flexi and HDFC Flexi...'
                    : assetType === 'stock'
                    ? 'Stock research is in progress. Try fund comparison prompts.'
                    : 'Ask about mutual funds or stocks...'
                }
                rows={1}
                name="chat_message"
                autoComplete="off"
                aria-label="Type your message"
                className="w-full resize-none bg-transparent px-2 py-1 text-[15px] text-white/90 placeholder:text-white/30 focus:outline-none min-h-[44px] custom-scrollbar leading-relaxed"
                style={{ overflow: "hidden" }}
              />
            </div>

            <div className="p-2 sm:px-4 sm:pb-3 sm:pt-0 border-t border-white/[0.05] flex items-center justify-between gap-4 mt-1">
              <div className="flex items-center gap-1.5 flex-wrap">
                {/* Asset Type selector */}
                <div className="inline-flex rounded-lg bg-white/[0.02] p-0.5 border border-white/5">
                  {[
                    { label: 'Auto', value: 'auto' },
                    { label: 'Stocks', value: 'stock' },
                    { label: 'Funds', value: 'mutual_fund' },
                  ].map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition-all ${
                        assetType === option.value
                          ? 'bg-[#66a3ff]/15 text-[#66a3ff]'
                          : 'text-white/40 hover:text-white/80'
                      }`}
                      onClick={() => setAssetType(option.value as AssetType)}
                      disabled={isProcessing}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
                <div className="inline-flex rounded-lg bg-white/[0.02] p-0.5 border border-white/5">
                  {[
                    { label: 'Beginner', value: 'beginner' },
                    { label: 'Advanced', value: 'advanced' },
                  ].map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition-all ${
                        explanationMode === option.value
                          ? 'bg-emerald-400/15 text-emerald-200'
                          : 'text-white/40 hover:text-white/80'
                      }`}
                      onClick={() => {
                        const nextMode = option.value as ExplanationMode;
                        setExplanationMode(nextMode);
                        setResearchDepth(nextMode === 'advanced' ? 'deep' : 'standard');
                      }}
                      disabled={isProcessing}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
                <div className="inline-flex rounded-lg bg-white/[0.02] p-0.5 border border-white/5">
                  {[
                    { label: 'Canvas', value: 'canvas' },
                    { label: 'Chat', value: 'chat' },
                  ].map((option) => (
                    <button
                      key={option.value}
                      type="button"
                      className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition-all ${
                        comparisonViewMode === option.value
                          ? 'bg-[#66a3ff]/15 text-[#66a3ff]'
                          : 'text-white/40 hover:text-white/80'
                      }`}
                      onClick={() => setComparisonViewMode(option.value as ComparisonViewMode)}
                      disabled={isProcessing}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleSend}
                  disabled={isProcessing || !input.trim()}
                  className={`px-4 py-2 rounded-xl text-sm font-medium transition-all flex items-center gap-2 ${
                    input.trim()
                      ? 'bg-white text-[#0A0A0B] shadow-[0_4px_12px_rgba(255,255,255,0.15)] hover:scale-[1.02] active:scale-[0.98]'
                      : 'bg-white/[0.05] text-white/30 cursor-not-allowed'
                  }`}
                >
                  <Send className="w-4 h-4" />
                  <span className="hidden sm:inline">{isProcessing ? 'Wait' : 'Send'}</span>
                </button>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}

function TypingDots() {
    return (
        <div className="flex items-center ml-1">
            {[1, 2, 3].map((dot) => (
                <motion.div
                    key={dot}
                    className="w-1.5 h-1.5 bg-white/90 rounded-full mx-0.5"
                    initial={{ opacity: 0.3 }}
                    animate={{
                        opacity: [0.3, 0.9, 0.3],
                        scale: [0.85, 1.1, 0.85]
                    }}
                    transition={{
                        duration: 1.2,
                        repeat: Infinity,
                        delay: dot * 0.15,
                        ease: "easeInOut",
                    }}
                    style={{
                        boxShadow: "0 0 4px rgba(255, 255, 255, 0.3)"
                    }}
                />
            ))}
        </div>
    );
}
