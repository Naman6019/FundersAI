"use client";

import React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Layers,
  ArrowRight,
  GitCompare,
  Wand2,
  FileText,
} from "lucide-react";

const ease = [0.22, 1, 0.36, 1] as const;

function TerminalLedger() {
  return (
    <div className="rounded-xl bg-black/40 border border-white/10 p-4 font-mono text-[11px] leading-relaxed overflow-hidden">
      <p className="text-[#00FF9D]">
        <span className="text-slate-500">$</span> compare ppfas-flexi-cap hdfc-flexi-cap --metrics=cagr,sharpe,alpha
      </p>
      <p className="text-slate-400 mt-1">&gt; Resolving schemes… 2 matched (AMFI 119551, 118955)</p>
      <p className="text-slate-400">&gt; Computing deterministic metrics from NAV history + factsheet…</p>

      <div className="mt-3 grid grid-cols-[1fr_auto_auto] gap-x-4 gap-y-1 text-slate-300">
        <span className="text-slate-500">METRIC</span>
        <span className="text-emerald-300 text-right">PPFAS</span>
        <span className="text-blue-300 text-right">HDFC</span>

        <span>3Y CAGR</span>
        <span className="text-right">21.4%</span>
        <span className="text-right">23.8%</span>

        <span>Sharpe Ratio</span>
        <span className="text-right">1.42</span>
        <span className="text-right">1.28</span>

        <span>Alpha (NIFTY500)</span>
        <span className="text-right text-[#00FF9D]">+2.41%</span>
        <span className="text-right text-slate-500">—</span>
      </div>

      <p className="text-slate-600 mt-3 italic">
        &gt; Source: AMFI daily NAV · AMC factsheet — zero synthetic values
        <span className="inline-block w-1.5 h-3 bg-[#00FF9D]/70 ml-1 align-middle animate-pulse" />
      </p>
    </div>
  );
}

function OverlapVenn() {
  return (
    <div className="rounded-xl bg-black/40 border border-white/10 p-4 flex flex-col items-center">
      <svg viewBox="0 0 200 130" className="w-full max-w-[220px]">
        <circle cx="80" cy="62" r="46" fill="#00FF9D" fillOpacity="0.16" stroke="#00FF9D" strokeOpacity="0.55" strokeWidth="1.5" />
        <circle cx="122" cy="62" r="46" fill="#3B82F6" fillOpacity="0.16" stroke="#3B82F6" strokeOpacity="0.55" strokeWidth="1.5" />
        <rect x="80" y="50" width="42" height="24" rx="6" fill="#05070f" fillOpacity="0.75" />
        <text x="101" y="66" textAnchor="middle" fontSize="15" fontWeight="700" fill="#ffffff" fontFamily="monospace">
          24.8%
        </text>
      </svg>
      <div className="flex items-center gap-4 mt-2 text-[10px] font-mono text-slate-400">
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-[#00FF9D]" /> PPFAS Flexi Cap
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-blue-500" /> HDFC Flexi Cap
        </span>
      </div>
    </div>
  );
}

function ScreenerPreview() {
  const rows = [
    { name: "Quant Small Cap Fund", tag: "Small Cap", cagr: "28.1%" },
    { name: "Parag Parikh Flexi Cap", tag: "Flexi Cap", cagr: "21.4%" },
    { name: "Mirae Large Cap Fund", tag: "Large Cap", cagr: "15.4%" },
  ];
  return (
    <div className="rounded-xl bg-black/40 border border-white/10 p-4">
      <div className="flex items-center gap-2 mb-3">
        <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-purple-500/15 border border-purple-500/30 text-purple-300">
          Category: All
        </span>
        <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-purple-500/15 border border-purple-500/30 text-purple-300">
          AMC: All
        </span>
      </div>
      <div className="space-y-2">
        {rows.map((r) => (
          <div
            key={r.name}
            className="flex items-center justify-between text-xs bg-white/[0.02] border border-white/5 rounded-lg px-3 py-2"
          >
            <div className="min-w-0">
              <p className="text-white font-semibold truncate">{r.name}</p>
              <p className="text-slate-500 text-[10px] font-mono">{r.tag}</p>
            </div>
            <span className="font-mono font-bold text-purple-300 shrink-0 ml-2">{r.cagr}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SynthesisDossierPreview() {
  return (
    <div className="relative rounded-xl bg-black/40 border border-white/10 p-4 sm:p-6 min-h-[168px]">
      <div className="absolute top-6 right-6 sm:top-8 sm:right-10 w-40 h-52 rounded-lg bg-slate-900 border border-white/10 rotate-6 shadow-xl" />
      <div className="absolute top-5 right-8 sm:top-7 sm:right-12 w-40 h-52 rounded-lg bg-slate-900 border border-white/10 rotate-2 shadow-xl" />
      <div className="relative w-40 sm:w-44 h-52 rounded-lg bg-slate-950 border border-cyan-500/30 shadow-2xl p-3 space-y-2">
        <div className="flex gap-1">
          <span className="px-1.5 py-0.5 rounded text-[8px] font-mono bg-cyan-500/20 text-cyan-300">Summary</span>
          <span className="px-1.5 py-0.5 rounded text-[8px] font-mono bg-white/5 text-slate-400">Risk</span>
          <span className="px-1.5 py-0.5 rounded text-[8px] font-mono bg-white/5 text-slate-400">Holdings</span>
        </div>
        <div className="h-2 w-3/4 rounded bg-white/10" />
        <div className="space-y-1.5 pt-1">
          <div className="h-1.5 w-full rounded bg-white/[0.06]" />
          <div className="h-1.5 w-full rounded bg-white/[0.06]" />
          <div className="h-1.5 w-2/3 rounded bg-white/[0.06]" />
        </div>
        <div className="h-14 rounded bg-cyan-500/10 border border-cyan-500/20 mt-2" />
      </div>
    </div>
  );
}

export default function EcosystemBentoGrid() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
      {/* Tile 1: Research Workspace — large */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.6, ease }}
        className="lg:col-span-7 group relative rounded-3xl border border-emerald-500/20 bg-gradient-to-b from-emerald-500/[0.06] to-transparent p-6 sm:p-8 flex flex-col gap-5 hover:border-emerald-500/40 transition-all"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-baseline gap-3">
            <span className="font-mono text-3xl sm:text-4xl font-bold text-emerald-500/30 leading-none select-none" aria-hidden="true">
              &gt;_
            </span>
            <div>
              <h3 className="text-lg sm:text-xl font-bold text-white tracking-tight">Interactive Research Workspace</h3>
              <p className="text-xs text-[#aebed6] mt-0.5">Conversational quant terminal — no LLM arithmetic</p>
            </div>
          </div>
          <span className="hidden sm:inline text-[10px] font-mono font-bold uppercase tracking-wider text-[#00FF9D] shrink-0 pt-1">
            Flagship
          </span>
        </div>

        <TerminalLedger />

        <div className="mt-auto pt-2 flex items-center justify-between">
          <Link
            href="/research"
            className="text-xs font-bold text-[#00FF9D] hover:text-[#66ffba] inline-flex items-center gap-1.5 transition"
          >
            <span>Explore Research features</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
          <Link
            href="/dashboard"
            className="px-4 py-2 rounded-xl bg-white/5 border border-white/10 text-xs font-semibold text-white hover:bg-white/10 transition"
          >
            Open App ⚡
          </Link>
        </div>
      </motion.div>

      {/* Tile 2: Portfolio Overlap / Public Tools — compact */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.6, delay: 0.1, ease }}
        className="lg:col-span-5 group relative rounded-3xl border border-blue-500/20 bg-gradient-to-b from-blue-500/[0.06] to-transparent p-6 sm:p-8 flex flex-col gap-5 hover:border-blue-500/40 transition-all"
      >
        <div className="flex items-center gap-3">
          <GitCompare className="w-6 h-6 text-blue-400 shrink-0" />
          <div>
            <h3 className="text-lg sm:text-xl font-bold text-white tracking-tight">Portfolio Overlap & Public Tools</h3>
            <p className="text-xs text-[#aebed6] mt-0.5">Zero-login SVG Venn overlap + SIP calculators</p>
          </div>
        </div>

        <OverlapVenn />

        <div className="mt-auto pt-2 flex items-center justify-between">
          <Link
            href="/tools/portfolio-overlap"
            className="text-xs font-bold text-blue-400 hover:text-blue-300 inline-flex items-center gap-1.5 transition"
          >
            <span>Explore All Public Tools</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
          <span className="text-xs font-mono text-slate-400">100% Free</span>
        </div>
      </motion.div>

      {/* Tile 3: Screener & Registry — compact */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.6, delay: 0.15, ease }}
        className="lg:col-span-5 group relative rounded-3xl border border-purple-500/20 bg-gradient-to-b from-purple-500/[0.06] to-transparent p-6 sm:p-8 flex flex-col gap-5 hover:border-purple-500/40 transition-all"
      >
        <div className="flex items-center gap-3">
          <Layers className="w-6 h-6 text-purple-400 shrink-0" />
          <div>
            <h3 className="text-lg sm:text-xl font-bold text-white tracking-tight">Mutual Fund Screener & Registry</h3>
            <p className="text-xs text-[#aebed6] mt-0.5">30+ schemes across 12 AMC fund houses</p>
          </div>
        </div>

        <ScreenerPreview />

        <div className="mt-auto pt-2 flex items-center justify-between">
          <Link
            href="/mutual-funds"
            className="text-xs font-bold text-purple-400 hover:text-purple-300 inline-flex items-center gap-1.5 transition"
          >
            <span>Launch Screener</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
          <span className="text-xs font-mono text-slate-400">30+ Indexed Funds</span>
        </div>
      </motion.div>

      {/* Tile 4: Synthesis Studio — large */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.6, delay: 0.2, ease }}
        className="lg:col-span-7 group relative rounded-3xl border border-cyan-500/20 bg-gradient-to-b from-cyan-500/[0.06] to-transparent p-6 sm:p-8 flex flex-col gap-5 hover:border-cyan-500/40 transition-all"
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <Wand2 className="w-7 h-7 text-cyan-400 shrink-0" />
            <div>
              <h3 className="text-lg sm:text-xl font-bold text-white tracking-tight">Synthesis Report Studio</h3>
              <p className="text-xs text-[#aebed6] mt-0.5">Autonomous multi-agent institutional dossiers</p>
            </div>
          </div>
          <span className="hidden sm:inline text-[10px] font-mono font-bold uppercase tracking-wider text-cyan-400 shrink-0 pt-1">
            Autonomous AI Studio
          </span>
        </div>

        <SynthesisDossierPreview />

        <div className="mt-auto pt-2 flex items-center justify-between">
          <Link
            href="/synthesis"
            className="text-xs font-bold text-cyan-400 hover:text-cyan-300 inline-flex items-center gap-1.5 transition"
          >
            <span>Explore Synthesis Studio</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
          <Link
            href="/synthesis/generate"
            className="px-4 py-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-xs font-semibold text-cyan-300 hover:bg-cyan-500/20 transition inline-flex items-center gap-1.5"
          >
            <FileText className="w-3.5 h-3.5" />
            Generate Dossier
          </Link>
        </div>
      </motion.div>
    </div>
  );
}
