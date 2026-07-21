'use client';

import { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { MessageSquareText, Zap, ChevronUp, ChevronDown } from 'lucide-react';
import type { User } from '@supabase/supabase-js';
import SignOutButton from './SignOutButton';
import type { UserTier } from '@/lib/billing/tiers';
import { hasSupabaseBrowserEnv, supabaseBrowser } from '@/lib/supabaseBrowser';

type UserProfileDropdownProps = {
  currentTier: UserTier;
};

function userDisplayName(user: User | null): string {
  const metadata = user?.user_metadata || {};
  const metadataName = [metadata.full_name, metadata.name, metadata.user_name, metadata.preferred_username]
    .find((value) => typeof value === 'string' && value.trim());
  if (typeof metadataName === 'string') return metadataName.trim();

  const emailName = user?.email?.split('@')[0]?.trim();
  if (!emailName) return 'User';
  return emailName
    .replace(/[._-]+/g, ' ')
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function userAvatarUrl(user: User | null): string | null {
  const metadata = user?.user_metadata || {};
  const value = metadata.avatar_url || metadata.picture;
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

export default function UserProfileDropdown({ currentTier }: UserProfileDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [user, setUser] = useState<User | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const displayName = userDisplayName(user);
  const avatarUrl = userAvatarUrl(user);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (!hasSupabaseBrowserEnv) return;

    let isActive = true;
    void supabaseBrowser.auth.getUser().then(({ data }) => {
      if (isActive) setUser(data.user);
    });
    const { data: listener } = supabaseBrowser.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
    });

    return () => {
      isActive = false;
      listener.subscription.unsubscribe();
    };
  }, []);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex w-full items-center justify-between rounded-xl px-2 py-2 transition-colors hover:bg-white/5"
      >
        <div className="flex items-center gap-2.5">
          {avatarUrl ? (
            // OAuth providers can return avatar URLs from arbitrary hosts.
            // eslint-disable-next-line @next/next/no-img-element
            <img
              alt={`${displayName} profile`}
              className="h-8 w-8 rounded-full border border-white/20 object-cover"
              src={avatarUrl}
            />
          ) : (
            <span className="flex h-8 w-8 items-center justify-center rounded-full border border-white/20 bg-white/10 text-sm font-semibold text-white">
              {displayName.charAt(0).toUpperCase()}
            </span>
          )}
          <span className="truncate text-sm font-medium text-slate-200">{displayName}</span>
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
            <p className="truncate text-sm font-semibold text-white">{displayName}</p>
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

          <Link
            href="/feedback"
            className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-sm text-slate-300 transition-colors hover:bg-white/5 hover:text-white"
            onClick={() => setIsOpen(false)}
          >
            <MessageSquareText className="h-4 w-4 text-[#00FF9D]" />
            <span>Send Feedback</span>
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
