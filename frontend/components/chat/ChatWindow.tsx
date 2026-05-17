'use client';

import { useCallback, useEffect, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Send, Sparkles } from 'lucide-react';
import { useCanvasStore } from '@/store/useCanvasStore';
import { AssetType, ComparisonViewMode, Message, ResearchDepth, useChatStore } from '@/store/useChatStore';

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
  const addMessage = useChatStore((state) => state.addMessage);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const initialQuerySentRef = useRef(false);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isProcessing]);

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 150)}px`;
  };

  const applySuggestion = (text: string) => {
    setInput(text);
  };

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
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
      addMessage({ id: Date.now().toString(), role: 'system', content: 'Error: Unable to reach Mooliq core. Make sure the server is running.' });
    } finally {
      setIsProcessing(false);
    }
  }, [addMessage, assetType, closeCanvas, comparisonViewMode, openCanvas, researchDepth, setIds, setInput, setIsProcessing, setView]);

  useEffect(() => {
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
  }, [comparisonViewMode, searchParams, sendQuery, setAssetType, setResearchDepth]);

  const handleSend = async () => {
    await sendQuery(input, assetType, researchDepth, comparisonViewMode);
  };

  return (
    <section className="flex h-full min-h-0 flex-col rounded-[1.8rem] border border-white/10 bg-[linear-gradient(160deg,rgba(13,26,45,0.9),rgba(9,19,34,0.88))] p-4 shadow-[0_18px_40px_rgba(0,0,0,0.38)] sm:p-5">
      <header className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/[0.03] px-3 py-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-[#58e0c1]" />
          <h2 className="text-2xl font-semibold tracking-tight text-[#e7f1ff]">MooliqAI</h2>
        </div>
        <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-2.5 py-1 text-xs font-semibold text-emerald-200">
          Research only
        </span>
      </header>

      <div ref={scrollRef} className="custom-scroll mt-3 flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto pr-1">
        {messages.map((msg) => (
          <div key={msg.id} className={msg.role === 'user' ? 'ml-5 rounded-2xl border border-sky-300/20 bg-sky-300/10 p-3 text-sm text-[#d8e9ff]' : 'mr-5 rounded-2xl border border-white/10 bg-white/[0.04] p-3 text-sm text-[#d4e5ff]'}>
            {msg.role === 'system' ? (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
            ) : (
              msg.content
            )}
            {msg.id === '1' && (
              <div className="mt-3 flex flex-wrap gap-2">
                <button className="rounded-full border border-white/10 bg-[#13233d] px-2.5 py-1 text-xs text-[#bed0ee] transition hover:border-[#3f6da8] hover:text-white" onClick={() => applySuggestion('Compare Parag Parikh Flexi Cap and ICICI Multi Asset Fund for long-term consistency.')}>Fund consistency</button>
                <button className="rounded-full border border-white/10 bg-[#13233d] px-2.5 py-1 text-xs text-[#bed0ee] transition hover:border-[#3f6da8] hover:text-white" onClick={() => applySuggestion('Which of these two funds has lower expense ratio and better Sharpe?')}>Sharpe + cost</button>
                <button className="rounded-full border border-white/10 bg-[#13233d] px-2.5 py-1 text-xs text-[#bed0ee] transition hover:border-[#3f6da8] hover:text-white" onClick={() => applySuggestion('Show NAV trend differences between Parag Parikh Flexi Cap and ICICI Multi Asset Fund.')}>NAV trend</button>
              </div>
            )}
          </div>
        ))}

        <div className="rounded-2xl border border-amber-300/25 bg-amber-100/10 px-3 py-2.5 text-sm text-amber-100">
          This is not investment advice. Verify data independently.
        </div>
      </div>

      <div className="mt-3 space-y-2">
        {isProcessing && (
          <div className="rounded-xl border border-sky-300/20 bg-sky-300/10 px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.12em] text-sky-200">
            Pipeline thinking...
          </div>
        )}

        <div className="flex flex-wrap gap-1.5">
          {[
            { label: 'Auto', value: 'auto' },
            { label: 'Stocks', value: 'stock' },
            { label: 'Mutual Funds', value: 'mutual_fund' },
          ].map((option) => (
            <button
              key={option.value}
              type="button"
              className={`rounded-full border px-2.5 py-1 text-xs font-semibold transition ${
                assetType === option.value
                  ? 'border-[#4f8ff7] bg-[#4f8ff7]/25 text-[#e2eeff]'
                  : 'border-white/10 bg-white/[0.03] text-[#9eb7df] hover:text-white'
              }`}
              onClick={() => setAssetType(option.value as AssetType)}
              disabled={isProcessing}
            >
              {option.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1.5">
          {[
            { label: 'Canvas', value: 'canvas' },
            { label: 'Chat', value: 'chat' },
          ].map((option) => (
            <button
              key={option.value}
              type="button"
              className={`rounded-full border px-2.5 py-1 text-xs font-semibold transition ${
                comparisonViewMode === option.value
                  ? 'border-emerald-300/40 bg-emerald-300/15 text-emerald-100'
                  : 'border-white/10 bg-white/[0.03] text-[#9eb7df] hover:text-white'
              }`}
              onClick={() => setComparisonViewMode(option.value as ComparisonViewMode)}
              disabled={isProcessing}
            >
              {option.label}
            </button>
          ))}
        </div>

        <div className="flex items-end gap-2 rounded-2xl border border-white/10 bg-[#0e1a2f]/90 p-2">
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
            placeholder={assetType === 'mutual_fund' ? 'Compare these funds for long-term consistency...' : assetType === 'stock' ? 'Stock research is in progress. Try fund comparison prompts.' : 'Ask for a fund comparison, risk, cost, or NAV view...'}
            rows={1}
            className="max-h-28 min-h-[2.5rem] flex-1 resize-none bg-transparent px-2 py-2 text-sm text-[#e7f0ff] placeholder:text-[#7f98c2] focus:outline-none"
          />
          <button className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-[#4f8ff7] bg-[#2f5fae] text-white transition hover:bg-[#3b70c7] disabled:cursor-not-allowed disabled:opacity-50" onClick={handleSend} aria-label="Send Message" disabled={isProcessing}>
            <Send size={18} />
          </button>
        </div>
      </div>
    </section>
  );
}
