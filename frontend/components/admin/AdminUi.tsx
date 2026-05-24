'use client';

import type { ReactNode } from 'react';

export function statusBadgeClass(status: string): string {
  const value = (status || '').toLowerCase();
  if (['fresh', 'active', 'success', 'ok'].includes(value)) return 'border-emerald-400/40 bg-emerald-400/10 text-emerald-200';
  if (['stale', 'warning', 'lagging'].includes(value)) return 'border-amber-400/40 bg-amber-400/10 text-amber-200';
  if (['error', 'failing', 'failed'].includes(value)) return 'border-red-400/40 bg-red-400/10 text-red-200';
  if (['partial', 'processing'].includes(value)) return 'border-sky-400/40 bg-sky-400/10 text-sky-200';
  if (['planned'].includes(value)) return 'border-slate-400/40 bg-slate-400/10 text-slate-200';
  return 'border-white/20 bg-white/5 text-[#d5e4ff]';
}

export function Panel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-3xl border border-white/10 bg-slate-950/40 p-4 ${className}`}>{children}</section>;
}

export function LoadingState() {
  return <Panel><p className="text-sm text-[#9eb4d6]">Loading…</p></Panel>;
}

export function ErrorState({ message }: { message: string }) {
  return <Panel><p className="text-sm text-red-200">{message}</p></Panel>;
}

export function EmptyState({ message }: { message: string }) {
  return <Panel><p className="text-sm text-[#9eb4d6]">{message}</p></Panel>;
}

