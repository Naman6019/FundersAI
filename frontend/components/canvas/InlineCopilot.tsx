'use client';

import { useState, useRef, useEffect } from 'react';
import { Bot, Send, X, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { MagicCard } from '@/components/ui/magic-card';

interface InlineCopilotProps {
  assetId: string;
  assetType: 'MUTUAL_FUND' | 'STOCK';
  assetName: string;
}

export default function InlineCopilot({ assetId, assetType, assetName }: InlineCopilotProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant'; content: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || loading) return;

    const userMessage = query.trim();
    setQuery('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: `User is viewing ${assetType === 'MUTUAL_FUND' ? 'mutual fund' : 'stock'} "${assetName}" (ID: ${assetId}). ${userMessage}`,
          asset_type: assetType === 'MUTUAL_FUND' ? 'mutual_fund' : 'stock',
          research_depth: 'standard',
          explanation_mode: 'beginner',
          comparison_view_mode: 'canvas',
          history: messages.map((message) => ({
            role: message.role === 'assistant' ? 'system' : 'user',
            content: message.content,
          })),
          conversation_context: {},
        }),
      });

      if (!res.ok) throw new Error('Copilot response failed');
      const data = await res.json();

      setMessages(prev => [...prev, { role: 'assistant', content: data.answer || "I couldn't generate a response." }]);
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: "Sorry, I ran into an error connecting to the copilot." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="absolute bottom-6 right-6 z-50">
      <AnimatePresence>
        {!isOpen && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            onClick={() => setIsOpen(true)}
            className="flex items-center gap-2 bg-[#00FF9D]/20 hover:bg-[#00FF9D]/30 border border-[#00FF9D]/50 text-[#00FF9D] px-4 py-3 rounded-full shadow-[0_0_20px_rgba(0,255,157,0.2)] backdrop-blur-md transition-all font-semibold"
          >
            <Bot className="w-5 h-5" />
            <span>Ask Copilot</span>
          </motion.button>
        )}

        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            className="w-80 sm:w-96 rounded-2xl overflow-hidden shadow-[0_10px_40px_rgba(0,0,0,0.5)] border border-[#00FF9D]/30 bg-black"
          >
            <MagicCard className="p-0 flex flex-col h-[400px]" gradientColor="rgba(0,255,157,0.1)">
              {/* Header */}
              <div className="flex items-center justify-between p-3 border-b border-white/10 bg-[#050505]/80 backdrop-blur-sm z-10">
                <div className="flex items-center gap-2">
                  <Bot className="w-4 h-4 text-[#00FF9D]" />
                  <span className="text-sm font-semibold text-white">Copilot Context: {assetName}</span>
                </div>
                <button onClick={() => setIsOpen(false)} className="text-slate-400 hover:text-white transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar relative z-0">
                {messages.length === 0 ? (
                  <div className="text-center text-slate-400 text-xs mt-10">
                    Ask a quick question about <strong className="text-[#00FF9D]">{assetName}</strong>.
                  </div>
                ) : (
                  messages.map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`text-sm px-3 py-2 rounded-xl max-w-[85%] ${msg.role === 'user' ? 'bg-[#00FF9D]/20 text-[#00FF9D] border border-[#00FF9D]/30 rounded-br-sm' : 'bg-white/10 text-slate-200 border border-white/5 rounded-bl-sm leading-relaxed prose prose-invert prose-p:my-0 prose-sm'}`}>
                        {msg.content}
                      </div>
                    </div>
                  ))
                )}
                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-white/5 border border-white/5 px-3 py-2 rounded-xl rounded-bl-sm">
                      <Loader2 className="w-4 h-4 animate-spin text-[#00FF9D]" />
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <form onSubmit={handleSubmit} className="p-3 border-t border-white/10 bg-[#050505]/80 backdrop-blur-sm flex items-center gap-2 z-10">
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Ask a question..."
                  className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-[#00FF9D]/50 transition-colors"
                />
                <button
                  type="submit"
                  disabled={!query.trim() || loading}
                  className="p-2 bg-[#00FF9D] text-black rounded-lg disabled:opacity-50 disabled:cursor-not-allowed hover:bg-[#00FF9D]/80 transition-colors"
                >
                  <Send className="w-4 h-4" />
                </button>
              </form>
            </MagicCard>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
