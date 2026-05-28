'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, Sparkles, Trash2 } from 'lucide-react';
import { useCanvasStore } from '@/store/useCanvasStore';
import { AssetType, ComparisonViewMode, initialMessages, Message, ResearchDepth, useChatStore } from '@/store/useChatStore';
import { hasSupabaseBrowserEnv, supabaseBrowser } from '@/lib/supabaseBrowser';

const markdownComponents = {
  h1: (props: React.ComponentProps<'h1'>) => <h1 className="mb-3 mt-1 text-lg font-bold text-white" {...props} />,
  h2: (props: React.ComponentProps<'h2'>) => <h2 className="mb-2 mt-4 text-base font-semibold text-slate-100" {...props} />,
  h3: (props: React.ComponentProps<'h3'>) => <h3 className="mb-2 mt-3 text-sm font-semibold text-slate-200" {...props} />,
  p: (props: React.ComponentProps<'p'>) => <p className="mb-2 leading-7 text-slate-100" {...props} />,
  ul: (props: React.ComponentProps<'ul'>) => <ul className="mb-3 list-disc space-y-1 pl-5" {...props} />,
  ol: (props: React.ComponentProps<'ol'>) => <ol className="mb-3 list-decimal space-y-1 pl-5" {...props} />,
  li: (props: React.ComponentProps<'li'>) => <li className="leading-7 text-slate-100" {...props} />,
  blockquote: (props: React.ComponentProps<'blockquote'>) => <blockquote className="mb-3 border-l-2 border-sky-300/60 pl-3 text-slate-200" {...props} />,
  a: (props: React.ComponentProps<'a'>) => (
    <a
      className="text-sky-300 underline underline-offset-2 hover:text-sky-200"
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
  code: (props: React.ComponentProps<'code'>) => <code className="rounded bg-white/[0.08] px-1.5 py-0.5 text-sky-200" {...props} />,
  hr: (props: React.ComponentProps<'hr'>) => <hr className="my-3 border-white/10" {...props} />,
};

export default function ChatWindow() {
  const searchParams = useSearchParams();
  const { setView, setIds, openCanvas, closeCanvas } = useCanvasStore();
  const messages = useChatStore((state) => state.messages);
  const input = useChatStore((state) => state.input);
  const isProcessing = useChatStore((state) => state.isProcessing);
  const assetType = useChatStore((state) => state.assetType);
  const researchDepth = useChatStore((state) => state.researchDepth);
  const comparisonViewMode = useChatStore((state) => state.comparisonViewMode);
  const setInput = useChatStore((state) => state.setInput);
  const setIsProcessing = useChatStore((state) => state.setIsProcessing);
  const setAssetType = useChatStore((state) => state.setAssetType);
  const setResearchDepth = useChatStore((state) => state.setResearchDepth);
  const setComparisonViewMode = useChatStore((state) => state.setComparisonViewMode);
  const setMessages = useChatStore((state) => state.setMessages);
  const addMessage = useChatStore((state) => state.addMessage);
  const resetMessages = useChatStore((state) => state.resetMessages);
  const [isHistoryReady, setIsHistoryReady] = useState(!hasSupabaseBrowserEnv);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const initialQuerySentRef = useRef(false);

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

  const applySuggestion = (text: string) => {
    setInput(text);
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
              }))
          : [];

        if (!ignore && savedMessages.length > 0) {
          setMessages([...initialMessages, ...savedMessages]);
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
  }, [getAccessToken, setMessages]);

  const sendQuery = useCallback(async (
    queryText: string,
    selectedAssetType: AssetType = assetType,
    selectedResearchDepth: ResearchDepth = researchDepth,
    selectedComparisonViewMode: ComparisonViewMode = comparisonViewMode,
  ) => {
    const text = queryText.trim();
    if (!text) return;

    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: text };
    addMessage(userMsg);
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }

    setIsProcessing(true);

    try {
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
          comparison_view_mode: selectedComparisonViewMode,
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

      addMessage({ id: Date.now().toString(), role: 'system', content: data.answer });
    } catch {
      addMessage({ id: Date.now().toString(), role: 'system', content: 'Error: Unable to reach FundersAI core. Make sure the server is running.' });
    } finally {
      setIsProcessing(false);
    }
  }, [addMessage, assetType, closeCanvas, comparisonViewMode, getAccessToken, openCanvas, researchDepth, setIds, setInput, setIsProcessing, setView]);

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

    setAssetType(nextAssetType);
    setResearchDepth(nextResearchDepth);
    void sendQuery(query, nextAssetType, nextResearchDepth, comparisonViewMode);
  }, [comparisonViewMode, isHistoryReady, searchParams, sendQuery, setAssetType, setResearchDepth]);

  const handleSend = async () => {
    await sendQuery(input, assetType, researchDepth, comparisonViewMode);
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
    <section className="flex h-full min-h-0 w-full flex-col rounded-[1.3rem] border border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.92),rgba(2,8,24,0.95))] shadow-[0_18px_40px_rgba(0,0,0,0.38)] backdrop-blur-xl">
      <header className="flex items-center justify-between border-b border-white/10 px-4 py-3 sm:px-5">
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
            <span className="rounded-full border border-sky-300/30 bg-sky-300/10 px-2.5 py-1 text-[11px] font-semibold text-sky-200">
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
          <span className="rounded-full border border-emerald-300/30 bg-emerald-300/12 px-2.5 py-1 text-[11px] font-semibold text-emerald-200">
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
                  ? 'ml-auto w-fit max-w-[85%] rounded-2xl border border-sky-300/40 bg-[linear-gradient(140deg,#1d4f91,#2563eb)] px-4 py-3 text-sm text-[#f3f8ff]'
                  : 'mr-auto max-w-[92%] rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm leading-relaxed text-slate-100'
              }
            >
              {msg.role === 'system' ? (
                <div className="chat-markdown text-sm">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                    {msg.content}
                  </ReactMarkdown>
                </div>
              ) : (
                msg.content
              )}
              {msg.id === '1' && (
                <div className="mt-3 flex flex-wrap gap-2">
                  <button className="rounded-full border border-white/15 bg-white/[0.05] px-2.5 py-1 text-xs text-slate-200 transition hover:border-sky-300/45 hover:text-white" onClick={() => applySuggestion('Compare Parag Parikh Flexi Cap and ICICI Multi Asset Fund for long-term consistency.')}>Fund consistency</button>
                  <button className="rounded-full border border-white/15 bg-white/[0.05] px-2.5 py-1 text-xs text-slate-200 transition hover:border-sky-300/45 hover:text-white" onClick={() => applySuggestion('Which of these two funds has lower expense ratio and better Sharpe?')}>Sharpe + cost</button>
                  <button className="rounded-full border border-white/15 bg-white/[0.05] px-2.5 py-1 text-xs text-slate-200 transition hover:border-sky-300/45 hover:text-white" onClick={() => applySuggestion('Show NAV trend differences between Parag Parikh Flexi Cap and ICICI Multi Asset Fund.')}>NAV trend</button>
                </div>
              )}
            </div>
          ))}

          <div className="rounded-xl border border-amber-300/25 bg-amber-400/10 px-3 py-2 text-xs text-amber-100/90">
            This is not investment advice. Verify data independently.
          </div>
        </div>
      </div>

      <div className="border-t border-white/10 bg-[#070b19] p-3 sm:p-4">
        {isProcessing && (
          <div className="mb-3 rounded-lg border border-sky-300/20 bg-sky-500/5 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.12em] text-sky-300 animate-pulse">
            Thinking…
          </div>
        )}

        <div className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/[0.02] p-2 transition-all duration-300 focus-within:border-sky-500/40 focus-within:bg-white/[0.04] focus-within:ring-4 focus-within:ring-sky-500/10">
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
                        ? 'bg-sky-500/20 border border-sky-400/30 text-sky-200'
                        : 'text-slate-400 hover:text-white border border-transparent'
                    }`}
                    onClick={() => setAssetType(option.value as AssetType)}
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
                        ? 'bg-emerald-500/20 border border-emerald-400/30 text-emerald-200'
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

            <button
              onClick={handleSend}
              aria-label="Send Message"
              disabled={isProcessing || !input.trim()}
              className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-sky-500 text-slate-950 transition-all hover:bg-sky-400 hover:scale-105 active:scale-95 disabled:scale-100 disabled:cursor-not-allowed disabled:bg-white/5 disabled:text-slate-600"
            >
              <Send size={15} />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
