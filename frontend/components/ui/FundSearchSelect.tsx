'use client';

import { useState, useEffect, useRef } from 'react';
import { Search, Loader2 } from 'lucide-react';
import type { SearchResultItem } from '@/types/funds';

interface Props {
  placeholder?: string;
  onSelect: (item: SearchResultItem) => void;
  className?: string;
}

export default function FundSearchSelect({ placeholder = "Search for a fund or stock...", onSelect, className = "" }: Props) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResultItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (!query || query.length < 2) {
      setResults([]);
      setIsOpen(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        if (res.ok) {
          const data = await res.json();
          setResults(data.results || []);
          setIsOpen(true);
        }
      } catch (err) {
        console.error("Search failed:", err);
      } finally {
        setIsLoading(false);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  const handleSelect = (item: SearchResultItem) => {
    setQuery('');
    setIsOpen(false);
    onSelect(item);
  };

  return (
    <div ref={wrapperRef} className={`relative ${className}`}>
      <div className="relative w-full">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 h-4 w-4" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => { if (results.length > 0) setIsOpen(true); }}
          placeholder={placeholder}
          className="w-full bg-[#080d1a] border border-white/20 rounded-lg py-2.5 pl-10 pr-10 text-sm text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-[#66a3ff] focus:border-[#66a3ff] transition-all"
        />
        {isLoading && (
          <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin text-slate-400" />
        )}
      </div>

      {isOpen && results.length > 0 && (
        <div className="absolute z-50 mt-1 w-full rounded-lg border border-white/10 bg-[#0f172a] shadow-xl max-h-60 overflow-y-auto">
          {results.map((item) => (
            <button
              key={`${item.type}-${item.id}`}
              onClick={() => handleSelect(item)}
              className="w-full text-left px-4 py-2.5 hover:bg-white/5 transition-colors border-b border-white/5 last:border-0 flex flex-col gap-0.5"
            >
              <div className="text-sm font-medium text-white line-clamp-1">{item.displayName}</div>
              <div className="text-[10px] text-slate-400 uppercase tracking-wider">{item.subLabel} &bull; {item.type === 'STOCK' ? 'Stock' : 'Mutual Fund'}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
