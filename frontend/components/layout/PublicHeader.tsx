'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { List, X, ArrowRight } from '@phosphor-icons/react';

export default function PublicHeader() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <header className="fixed top-0 z-50 w-full border-b border-gray-800/80 bg-[#050810]/90 backdrop-blur-xl transition-all">
      <div className="mx-auto flex w-full max-w-[1500px] items-center justify-between px-5 py-3.5 sm:px-8">
        <Link href="/" className="flex items-center gap-2.5 group">
          <Image
            src="/FUNDERSAI-nobackground.png"
            alt="FundersAI Logo"
            width={128}
            height={32}
            unoptimized
            className="h-8 w-auto object-contain transition-transform group-hover:scale-[1.02]"
            style={{ width: 'auto' }}
            priority
          />
          <span className="text-gray-700 font-light text-xs">/</span>
          <span className="font-mono text-[10px] uppercase font-bold tracking-widest text-blue-400 px-2 py-0.5 rounded bg-blue-500/10 border border-blue-500/20">
            [ TERMINAL ]
          </span>
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden items-center gap-6 font-mono text-[11px] font-medium tracking-wider uppercase text-gray-400 md:flex">
          <Link href="/reports" className="transition hover:text-cyan-400 flex items-center gap-1">
            <span className="text-cyan-400 font-bold">⚡</span>
            <span>Synthesis</span>
          </Link>
          <Link href="/reports/generate" className="transition hover:text-blue-400">Workstation</Link>
          <Link href="/tools/portfolio-overlap" className="transition hover:text-white">Overlap</Link>
          <Link href="/pricing" className="transition text-emerald-400 hover:text-emerald-300 font-bold">Pricing</Link>
          <Link href="/methodology" className="transition hover:text-white">Methodology</Link>
          <Link href="/sample" className="transition hover:text-white">Sample</Link>
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-3">
          <Link href="/login" className="font-mono text-[11px] uppercase tracking-wider font-semibold text-gray-400 transition hover:text-white px-2 py-1">
            Sign In
          </Link>
          <div className="hidden sm:block">
            <Link
              href="/dashboard"
              className="inline-flex h-8 items-center justify-center gap-1.5 rounded-lg border border-blue-500/40 bg-blue-600/10 px-4 font-mono text-[11px] font-bold uppercase tracking-wider text-blue-400 shadow-md transition-all hover:bg-blue-600 hover:text-white hover:border-blue-600 shadow-blue-900/20"
            >
              <span>Workspace</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          <button
            className="md:hidden p-1 text-gray-400 transition hover:text-white"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            aria-label="Toggle navigation menu"
          >
            {isMobileMenuOpen ? <X weight="bold" size={22} /> : <List weight="bold" size={22} />}
          </button>
        </div>
      </div>

      {/* Mobile Nav */}
      {isMobileMenuOpen && (
        <div className="md:hidden border-t border-white/10 bg-[#070b12]/95 px-5 py-5 flex flex-col gap-4 backdrop-blur-xl">
          <Link href="/sample" onClick={() => setIsMobileMenuOpen(false)} className="text-sm font-semibold text-gray-300 hover:text-white">Sample Report</Link>
          <Link href="/how-it-works" onClick={() => setIsMobileMenuOpen(false)} className="text-sm font-semibold text-gray-300 hover:text-white">Architecture Flow</Link>
          <Link href="/intelligence" onClick={() => setIsMobileMenuOpen(false)} className="text-sm font-semibold text-gray-300 hover:text-white">Source Intelligence</Link>
          <Link href="/pricing" onClick={() => setIsMobileMenuOpen(false)} className="text-sm font-semibold text-emerald-400 hover:text-emerald-300">Pricing &amp; Plans</Link>
          <Link href="/data-trust" onClick={() => setIsMobileMenuOpen(false)} className="text-sm font-semibold text-gray-300 hover:text-white">Data &amp; Trust</Link>
          <Link href="/methodology" onClick={() => setIsMobileMenuOpen(false)} className="text-sm font-semibold text-gray-300 hover:text-white">Methodology</Link>
          <Link href="/synthesis" onClick={() => setIsMobileMenuOpen(false)} className="text-sm font-semibold text-blue-400 hover:text-blue-300">Synthesis Studio</Link>
          <div className="pt-2" onClick={() => setIsMobileMenuOpen(false)}>
            <Link
              href="/dashboard"
              className="flex w-full items-center justify-center gap-2 rounded-full bg-emerald-500 py-2.5 text-xs font-bold text-black transition-all"
            >
              Open Workspace →
            </Link>
          </div>
        </div>
      )}
    </header>
  );
}
