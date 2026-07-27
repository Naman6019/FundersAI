'use client';

import { KeyboardEvent, ReactNode, useId, useState } from 'react';
import { CircleHelp } from 'lucide-react';
import { statusColorClass, statusDotClass } from '@/lib/dataHealth';

type StatusLabelProps = {
  label: string;
  status: string;
  description: string;
  details?: ReactNode;
  actions?: ReactNode;
  className?: string;
};

export default function StatusLabel({
  label,
  status,
  description,
  details,
  actions,
  className = '',
}: StatusLabelProps) {
  const tooltipId = useId();
  const [open, setOpen] = useState(false);
  const [pinned, setPinned] = useState(false);

  const close = () => {
    setOpen(false);
    setPinned(false);
  };
  const handleKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      close();
    }
  };

  return (
    <span
      className={`group/status relative inline-flex ${className}`}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => { if (!pinned) setOpen(false); }}
      onFocus={() => setOpen(true)}
      onBlur={(event) => {
        if (!pinned && !event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
    >
      <button
        type="button"
        className="inline-flex min-h-8 items-center gap-2 rounded-full border border-white/10 bg-white/[0.045] px-3 py-1.5 text-[11px] font-semibold transition hover:border-white/25 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#66a3ff]/70"
        aria-describedby={open ? tooltipId : undefined}
        aria-expanded={open}
        onClick={() => {
          setPinned((value) => !value);
          setOpen(true);
        }}
        onKeyDown={handleKeyDown}
      >
        <span className={`h-2 w-2 rounded-full ${statusDotClass(status)}`} aria-hidden="true" />
        <span className="text-slate-300">{label}</span>
        <span className={statusColorClass(status)}>{status}</span>
        <CircleHelp className="h-3.5 w-3.5 text-slate-500" aria-hidden="true" />
      </button>

      {open ? (
        <span
          id={tooltipId}
          role="tooltip"
          className="absolute left-0 top-[calc(100%+0.5rem)] z-50 block w-[min(22rem,calc(100vw-2rem))] rounded-xl border border-white/15 bg-[#080d18]/98 p-3 text-left shadow-2xl backdrop-blur-xl"
        >
          <span className="block text-xs font-semibold text-white">{label}: {status}</span>
          <span className="mt-1 block text-[11px] leading-5 text-slate-300">{description}</span>
          {details ? <span className="mt-2 block text-[11px] leading-5 text-slate-400">{details}</span> : null}
          {actions ? <span className="mt-3 flex flex-wrap gap-2">{actions}</span> : null}
          {pinned ? <span className="mt-2 block text-[10px] text-slate-500">Press Escape or tap the label to close.</span> : null}
        </span>
      ) : null}
    </span>
  );
}

