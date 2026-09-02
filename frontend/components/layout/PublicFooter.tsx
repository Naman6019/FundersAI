'use client';

import React from 'react';
import Link from 'next/link';
import Image from 'next/image';

export default function PublicFooter() {
  return (
    <footer className="relative border-t border-white/10 bg-[#070b12] px-5 py-16 sm:px-8 text-gray-400">
      <div className="mx-auto grid w-full max-w-[1500px] gap-10 md:grid-cols-2 lg:grid-cols-4">
        {/* Col 1: Brand */}
        <div className="space-y-4">
          <Link href="/" className="flex items-center gap-3">
            <Image
              src="/FUNDERSAI-nobackground.png"
              alt="FundersAI Logo"
              width={160}
              height={40}
              unoptimized
              className="h-10 w-auto object-contain"
              style={{ width: 'auto' }}
            />
          </Link>
          <p className="text-xs text-gray-400 leading-relaxed max-w-sm">
            FundersAI provides research-grade mutual fund and stock analysis powered by deterministic quantitative metrics and multi-agent AI verification.
          </p>
        </div>

        {/* Col 2: Product & Features */}
        <div className="space-y-3">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-emerald-400">Product &amp; Tools</p>
          <ul className="space-y-2 text-xs font-medium">
            <li><Link href="/mutual-funds" className="hover:text-white transition-colors text-[#00FF9D]">Mutual Fund Screener</Link></li>
            <li><Link href="/tools" className="hover:text-white transition-colors">Free Investor Tools Hub</Link></li>
            <li><Link href="/tools/portfolio-overlap" className="hover:text-white transition-colors">Portfolio Overlap Calculator</Link></li>
            <li><Link href="/tools/sip-calculator" className="hover:text-white transition-colors">SIP &amp; Step-Up Calculator</Link></li>
            <li><Link href="/synthesis" className="hover:text-white transition-colors">Synthesis Studio</Link></li>
            <li><Link href="/pricing" className="hover:text-white transition-colors">Pricing &amp; Subscriptions</Link></li>
          </ul>
        </div>

        {/* Col 3: Data & Methodology */}
        <div className="space-y-3">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-400">Data &amp; Trust</p>
          <ul className="space-y-2 text-xs font-medium">
            <li><Link href="/data-trust" className="hover:text-white transition-colors">Data &amp; Trust Portal</Link></li>
            <li><Link href="/methodology" className="hover:text-white transition-colors">Methodology Hub</Link></li>
            <li><Link href="/methodology/data-sources" className="hover:text-white transition-colors">Data Sources &amp; Feeds</Link></li>
            <li><Link href="/methodology/formulas" className="hover:text-white transition-colors">Metric Formulas &amp; Math</Link></li>
            <li><Link href="/methodology/resolution" className="hover:text-white transition-colors">Scheme Resolution &amp; Benchmarks</Link></li>
            <li><Link href="/methodology/guardrails" className="hover:text-white transition-colors">Guardrails &amp; Abstention</Link></li>
          </ul>
        </div>

        {/* Col 4: Company & Legal */}
        <div className="space-y-3">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-cyan-400">Company &amp; Resources</p>
          <ul className="space-y-2 text-xs font-medium">
            <li><Link href="/synthesis/supported-funds" className="hover:text-white transition-colors">Supported AMC Directory</Link></li>
            <li><Link href="/mutual-funds" className="hover:text-white transition-colors">Mutual Fund Index</Link></li>
            <li><Link href="/about" className="hover:text-white transition-colors">About FundersAI</Link></li>
            <li><Link href="/contact" className="hover:text-white transition-colors">Contact Support</Link></li>
            <li>
              <a href="mailto:support@fundersai.co.in" className="text-[#82aff6] hover:underline font-mono text-[11px] inline-flex items-center gap-1">
                ✉ support@fundersai.co.in
              </a>
            </li>
            <li><Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link></li>
            <li><Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link></li>
          </ul>
        </div>
      </div>

      <div className="mx-auto max-w-[1500px] mt-12 pt-6 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px] text-gray-500">
        <div className="flex flex-wrap items-center gap-3">
          <p>© {new Date().getFullYear()} FundersAI. All rights reserved.</p>
          <span className="hidden sm:inline text-gray-700">|</span>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-bold hover:bg-emerald-500/20 transition-all text-[11px]"
          >
            <span>← Back to Workspace</span>
          </Link>
        </div>
        <p className="uppercase tracking-widest text-[10px] text-gray-400 font-mono">
          Research only · Not personalized financial advice · Verify independently
        </p>
      </div>
    </footer>
  );
}
