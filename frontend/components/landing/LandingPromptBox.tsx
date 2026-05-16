'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { Send } from 'lucide-react';

export default function LandingPromptBox() {
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

  return (
    <div className="landing-query-card">
      <textarea
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            openApp();
          }
        }}
        placeholder="Ask Mooliq about a stock, mutual fund, index, or market trend..."
        rows={3}
      />
      <button type="button" onClick={openApp}>
        Try out Mooliq
        <Send size={20} />
      </button>
    </div>
  );
}
