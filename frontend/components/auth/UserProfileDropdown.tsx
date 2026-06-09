'use client';

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { LogOut, User, Zap, ChevronUp, ChevronDown } from 'lucide-react';
import SignOutButton from './SignOutButton';
import type { UserTier } from '@/lib/billing/tiers';

type UserProfileDropdownProps = {
  currentTier: UserTier;
};

export default function UserProfileDropdown({ currentTier }: UserProfileDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between rounded-xl px-2 py-2 transition-colors hover:bg-white/5"
      >
        <div className="flex items-center gap-2.5">
          <img
            alt="User Profile"
            className="h-8 w-8 rounded-full border border-white/20 object-cover"
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuC2yc-OZ72YKCNRfbOXvs1JmLKZ8WsL1I4VdXs7ay-q-nGiubYiIDIn5X-U2JM7CUVh4ez21gIRIi88QOJbY2MGm4mxh4VKFl3jfsj00Xu-2wkZyL8elq700xoxfN8ggkPtWyu1QMLbXeSfy4p5SePZGFHluNczs4uCQdnfoc3hLiJXqSIUeyAVFOLC_g-dgN5Vua1TH3ooT3QW6lOXjtHGvBH_ktSxj7IoGj7WqZ3yR_GOcOkozqObt4umNwUzkBPsvUJlmwlhVp5f"
          />
          <span className="text-sm font-medium text-slate-200">Reaper</span>
        </div>
        {isOpen ? (
          <ChevronDown className="h-4 w-4 text-slate-400" />
        ) : (
          <ChevronUp className="h-4 w-4 text-slate-400" />
        )}
      </button>

      {isOpen && (
        <div className="absolute bottom-full left-0 mb-2 w-full min-w-[220px] rounded-xl border border-white/10 bg-[#0f172a] p-1.5 shadow-[0_4px_24px_rgba(0,0,0,0.4)] backdrop-blur-xl">
          <div className="mb-1 border-b border-white/5 px-2.5 py-2">
            <p className="text-xs font-medium text-slate-300">Signed in as</p>
            <p className="truncate text-sm font-semibold text-white">Reaper</p>
          </div>

          <Link
            href="/billing"
            className="flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-sm text-slate-300 transition-colors hover:bg-white/5 hover:text-white"
            onClick={() => setIsOpen(false)}
          >
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-[#66a3ff]" />
              <span>Current Plan</span>
            </div>
            <span className="rounded bg-[#66a3ff]/10 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-[#66a3ff]">
              {currentTier}
            </span>
          </Link>

          <div className="my-1 border-t border-white/5"></div>

          <div className="px-1" onClick={() => setIsOpen(false)}>
            <SignOutButton className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-sm text-rose-400 transition-colors hover:bg-rose-500/10 hover:text-rose-300" showText={true} />
          </div>
        </div>
      )}
    </div>
  );
}
