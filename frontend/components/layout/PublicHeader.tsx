'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { List, X, ArrowRight } from '@phosphor-icons/react';

export default function PublicHeader() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <header className="fixed top-0 z-50 w-full border-b border-white/10 bg-[#070b12]/90 backdrop-blur-xl transition-all">
      <div className="mx-auto flex w-full max-w-[1500px] items-center justify-between px-5 py-4 sm:px-8">
        <Link href="/" className="flex items-center gap-3">
          <Image
            src="/FUNDERSAI-nobackground.png"
            alt="FundersAI Logo"
            width={132}
            height={34}
            unoptimized
            className="h-8 w-auto object-contain sm:h-10"
            style={{ width: 'auto' }}
            priority
          />
        </Link>

        {/* Desktop Nav */}
        <nav className="hidden items-center gap-7 text-xs font-semibold uppercase tracking-wider text-gray-400 md:flex">
          <Link href="/sample" className="transition hover:text-white">Sample</Link>
          <Link href="/how-it-works" className="transition hover:text-white">Flow</Link>
          <Link href="/intelligence" className="transition hover:text-white">Intelligence</Link>
          <Link href="/pricing" className="transition text-emerald-400 hover:text-emerald-300">Pricing</Link>
          <Link href="/data-trust" className="transition hover:text-white">Data &amp; Trust</Link>
          <Link href="/methodology" className="transition hover:text-white">Methodology</Link>
          <Link href="/synthesis" className="transition text-blue-400 hover:text-blue-300">Synthesis</Link>
        </nav>

        {/* Actions */}
        <div className="flex items-center gap-4">
          <Link href="/login" className="text-xs font-semibold text-gray-400 transition hover:text-white">
            Login
          </Link>
          <div className="hidden sm:block">
            <Link
              href="/dashboard"
              className="inline-flex h-9 items-center justify-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-5 text-xs font-semibold text-emerald-400 backdrop-blur-md transition-all hover:bg-emerald-500/20 hover:border-emerald-500/50"
            >
              <span>Workspace</span>
              <ArrowRight className="h-3.5 w-3.5" />
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
