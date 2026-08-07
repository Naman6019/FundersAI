'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, BookOpen, Loader2 } from 'lucide-react';
import { MagicCard } from '@/components/ui/magic-card';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
};

export default function FundResearchChat({ schemeName }: { schemeName: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userQuery = input.trim();
    setInput('');
    const newMessageId = Date.now().toString();
    setMessages((prev) => [...prev, { id: newMessageId, role: 'user', content: userQuery }]);
    setIsLoading(true);

    try {
      const res = await fetch('/api/funds/research/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: `[${schemeName}] ${userQuery}`,
          limit: 5,
        }),
      });

      if (!res.ok) throw new Error('Failed to fetch response');
      const data = await res.json();
      
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.answer || 'I am unable to answer this question right now.',
          sources: data.sources || [],
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'Sorry, I encountered an error while trying to retrieve the answer.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <MagicCard 
      className="w-full flex-col shadow-2xl p-0 overflow-hidden border border-white/5"
      gradientColor="rgba(0, 255, 157, 0.08)"
    >
      <div className="flex items-center gap-2 p-4 border-b border-white/5 bg-white/[0.02]">
        <Sparkles className="w-5 h-5 text-[#00FF9D]" />
        <h3 className="text-sm font-semibold tracking-wide text-white uppercase">Chat with {schemeName}</h3>
      </div>

      <div className="flex flex-col h-[350px] bg-[#050505]/50">
        <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-slate-400 space-y-3">
              <BookOpen className="w-8 h-8 opacity-50 text-[#00FF9D]" />
              <p className="text-sm text-center max-w-sm">
                Ask a question about this fund. We&apos;ll search its official factsheets and portfolio disclosures to find the answer.
              </p>
              <div className="flex flex-wrap justify-center gap-2 mt-4">
                {['Why did the AUM drop?', 'What are the top 3 holdings?', 'What is the expense ratio?'].map((q) => (
                  <button
                    key={q}
                    onClick={() => setInput(q)}
                    className="text-xs bg-white/5 hover:bg-white/10 px-3 py-1.5 rounded-full transition-colors border border-white/10"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <div key={msg.id} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                <div 
                  className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                    msg.role === 'user' 
                      ? 'bg-[#00FF9D]/10 text-[#00FF9D] border border-[#00FF9D]/20 rounded-tr-sm' 
                      : 'bg-white/5 text-slate-200 border border-white/10 rounded-tl-sm'
                  }`}
                >
                  <div className="text-sm prose prose-invert max-w-none prose-p:leading-relaxed prose-a:text-[#00FF9D]">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                </div>
                {msg.role === 'assistant' && msg.sources && msg.sources.length > 0 && (
                  <div className="mt-2 pl-2 max-w-[85%]">
                    <p className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-1.5">Sources Cited:</p>
                    <div className="flex flex-col gap-1.5">
                      {msg.sources.map((source, idx) => (
                        <div key={idx} className="flex items-start gap-1.5 text-xs text-slate-400 bg-white/[0.03] px-2.5 py-1.5 rounded border border-white/5">
                          <BookOpen className="w-3.5 h-3.5 mt-0.5 shrink-0 opacity-70" />
                          <span className="leading-tight">{source}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))
          )}
          {isLoading && (
            <div className="flex items-start">
              <div className="bg-white/5 border border-white/10 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-2">
                <Loader2 className="w-4 h-4 text-[#00FF9D] animate-spin" />
                <span className="text-sm text-slate-400">Searching official documents...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <div className="p-3 border-t border-white/5 bg-white/[0.02]">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about this fund's performance, holdings, or strategy..."
              className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder:text-slate-500 focus:outline-none focus:border-[#00FF9D]/50 focus:ring-1 focus:ring-[#00FF9D]/50 transition-all"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="bg-[#00FF9D] hover:bg-[#00e68d] disabled:opacity-50 disabled:hover:bg-[#00FF9D] text-black w-10 flex items-center justify-center rounded-xl transition-colors"
            >
              <Send className="w-4 h-4" />
            </button>
          </form>
        </div>
      </div>
    </MagicCard>
  );
}
