'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import type { FormEvent, KeyboardEvent } from 'react';
import { Send } from 'lucide-react';

const quickPrompts = [
  'Compare Axis Flexi and HDFC Flexi',
  'Explain beta and volatility',
  'Show source freshness',
];

export default function LandingPromptBox({ className = '' }: { className?: string }) {
  const router = useRouter();
  const [query, setQuery] = useState('');

  const openApp = () => {
    const text = query.trim();
    if (!text) {
      router.push('/dashboard');
      return;
    }

    router.push(`/dashboard?query=${encodeURIComponent(text)}`);
  };

  const submitPrompt = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    openApp();
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  };

  return (
    <form className={`w-full min-w-0 ${className}`} onSubmit={submitPrompt}>
      <div className="min-w-0 rounded-2xl border border-white/10 bg-white/[0.03] p-4 text-left backdrop-blur-md">
        <div className="flex items-center gap-2 border-b border-white/10 px-2 pb-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-[#00FF9D]">
          <span className="relative flex h-2 w-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#00FF9D] opacity-75"></span>
            <span className="relative inline-flex h-2 w-2 rounded-full bg-[#00FF9D]"></span>
          </span>
          Ask a research question
        </div>

        <div className="relative mt-4">
          <textarea
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Compare Axis Large Cap and HDFC Mid Cap for risk, cost, and source freshness"
            rows={4}
            name="landing_query"
            autoComplete="off"
            aria-label="Ask FundersAI about a stock, mutual fund, index, or market trend"
            className="block h-28 w-full resize-none whitespace-pre-wrap break-words rounded-xl border border-white/10 bg-black/40 px-5 py-4 pr-16 font-sans text-sm leading-relaxed text-white outline-none transition placeholder:text-white/30 focus:border-white/30 focus:bg-white/[0.02] sm:h-36 sm:text-base"
          />
          <button
            type="submit"
            aria-label="Open FundersAI with this question"
            className="absolute bottom-3 right-3 inline-flex h-11 w-11 items-center justify-center rounded-lg bg-white text-black transition hover:bg-white/80"
          >
            <Send className="h-[18px] w-[18px]" />
          </button>
        </div>

        <div className="flex min-w-0 flex-wrap gap-2 pt-4">
          {quickPrompts.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => setQuery(prompt)}
              className="max-w-full whitespace-normal break-words rounded-full border border-white/10 bg-transparent px-4 py-2 text-left text-xs font-medium text-white/50 transition hover:border-white/30 hover:bg-white/5 hover:text-white"
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>
    </form>
  );
}
