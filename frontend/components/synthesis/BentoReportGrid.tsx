"use client";

import React from "react";
import { Award, ShieldAlert, PieChart, FileText, CheckCircle2, ArrowRight } from "lucide-react";
import { TrustBadge } from "../workspace/TrustBadge";

interface BentoReportGridProps {
  fundA?: string;
  fundB?: string;
  onExportPDF?: () => void;
}

export function BentoReportGrid({
  fundA = "Parag Parikh Flexi Cap",
  fundB = "HDFC Flexi Cap",
  onExportPDF,
}: BentoReportGridProps) {
  return (
    <div className="space-y-6 my-6">
      
      {/* Top Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 p-4 rounded-xl bg-slate-900/60 border border-white/10">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-cyan-950 text-cyan-300 border border-cyan-800/50">
              Synthesis Studio Report #8492
            </span>
            <TrustBadge status="verified" asOfDate="07 Aug 2026" sourceDoc="AMFI & Factsheet" />
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight font-sans">
            Institutional Research Whitepaper: {fundA} vs {fundB}
          </h2>
        </div>

        <button
          onClick={onExportPDF}
          className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-white bg-gradient-to-r from-cyan-600 to-teal-600 hover:from-cyan-500 hover:to-teal-500 rounded-lg shadow-lg border border-cyan-400/30 transition-all hover:scale-[1.02]"
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Export Official PDF Report</span>
        </button>
      </div>

      {/* Asymmetric Bento Grid */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
        
        {/* Card 1: Executive Verdict (Col span 7) */}
        <div className="md:col-span-7 p-5 rounded-2xl bg-[#0F111A]/90 border border-cyan-500/30 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <div className="flex items-center gap-2">
              <Award className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-bold text-white font-sans uppercase tracking-wider">
                Executive Verdict & Risk Profile
              </h3>
            </div>
            <span className="text-[10px] text-emerald-400 font-mono bg-emerald-950 px-2 py-0.5 rounded border border-emerald-800">
              High Downside Protection
            </span>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed font-sans">
            <strong className="text-white">{fundA}</strong> demonstrates superior risk-adjusted alpha over a 3-year trailing period with a Sharpe Ratio of <span className="font-mono text-emerald-400 font-bold">1.42</span> (vs {fundB}’s <span className="font-mono text-slate-300">1.28</span>). While {fundB} generated slightly higher absolute CAGR (+23.8% vs +21.4%), {fundA} captured <span className="font-mono text-cyan-400 font-bold">14.2% lower downside drawdown</span> during high-volatility market cycles.
          </p>

          <div className="grid grid-cols-3 gap-3 pt-2">
            <div className="p-3 rounded-lg bg-slate-900/80 border border-white/10 text-center font-mono">
              <span className="text-[10px] text-slate-400 block uppercase">3Y Alpha</span>
              <span className="text-sm font-bold text-emerald-400">+2.41%</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-900/80 border border-white/10 text-center font-mono">
              <span className="text-[10px] text-slate-400 block uppercase">Sortino Ratio</span>
              <span className="text-sm font-bold text-cyan-400">2.10</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-900/80 border border-white/10 text-center font-mono">
              <span className="text-[10px] text-slate-400 block uppercase">Beta (vs NIFTY)</span>
              <span className="text-sm font-bold text-slate-200">0.78</span>
            </div>
          </div>
        </div>

        {/* Card 2: Risk Metrics Matrix (Col span 5) */}
        <div className="md:col-span-5 p-5 rounded-2xl bg-[#0F111A]/90 border border-white/10 shadow-xl space-y-3">
          <div className="flex items-center gap-2 border-b border-white/10 pb-3">
            <ShieldAlert className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-white font-sans uppercase tracking-wider">
              Quantitative Risk Matrix
            </h3>
          </div>

          <div className="space-y-2 text-xs font-mono">
            <div className="flex justify-between items-center p-2 rounded bg-slate-900/60">
              <span className="text-slate-400">Sharpe Ratio:</span>
              <div className="space-x-2">
                <span className="text-emerald-400 font-bold">{fundA}: 1.42</span>
                <span className="text-slate-400">|</span>
                <span className="text-slate-300">{fundB}: 1.28</span>
              </div>
            </div>

            <div className="flex justify-between items-center p-2 rounded bg-slate-900/60">
              <span className="text-slate-400">Max Drawdown:</span>
              <div className="space-x-2">
                <span className="text-emerald-400 font-bold">{fundA}: -14.2%</span>
                <span className="text-slate-400">|</span>
                <span className="text-rose-400">{fundB}: -17.8%</span>
              </div>
            </div>

            <div className="flex justify-between items-center p-2 rounded bg-slate-900/60">
              <span className="text-slate-400">Expense Ratio (TER):</span>
              <div className="space-x-2">
                <span className="text-emerald-400 font-bold">{fundA}: 0.62%</span>
                <span className="text-slate-400">|</span>
                <span className="text-slate-300">{fundB}: 0.85%</span>
              </div>
            </div>

            <div className="flex justify-between items-center p-2 rounded bg-slate-900/60">
              <span className="text-slate-400">Portfolio Overlap:</span>
              <span className="text-cyan-400 font-bold">24.8% (14 Holdings)</span>
            </div>
          </div>
        </div>

        {/* Card 3: Portfolio Overlap Treemap (Col span 6) */}
        <div className="md:col-span-6 p-5 rounded-2xl bg-[#0F111A]/90 border border-white/10 shadow-xl space-y-3">
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <div className="flex items-center gap-2">
              <PieChart className="w-4 h-4 text-amber-400" />
              <h3 className="text-sm font-bold text-white font-sans uppercase tracking-wider">
                Holding Overlap & Sector Treemap
              </h3>
            </div>
            <span className="text-[10px] text-slate-400 font-mono">24.8% Total Overlap</span>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/80 border border-white/5 space-y-2">
            <div className="text-xs font-medium text-slate-300 flex justify-between">
              <span>Top Common Holdings:</span>
              <span className="font-mono text-cyan-400">HDFC Bank, ICICI Bank, ITC, Reliance</span>
            </div>
            
            {/* Visual Overlap Bar */}
            <div className="w-full h-3 bg-slate-900 rounded-full overflow-hidden flex">
              <div className="h-full bg-emerald-500 w-[24.8%]" title="Shared Overlap 24.8%" />
              <div className="h-full bg-cyan-500 w-[45.2%]" title="PPFAS Unique 45.2%" />
              <div className="h-full bg-indigo-500 w-[30.0%]" title="HDFC Unique 30.0%" />
            </div>

            <div className="flex justify-between text-[10px] font-mono text-slate-400 pt-1">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" /> Overlap: 24.8%</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-cyan-500" /> PPFAS Unique: 45.2%</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-indigo-500" /> HDFC Unique: 30.0%</span>
            </div>
          </div>
        </div>

        {/* Card 4: Official AMC Factsheet Excerpts (Col span 6) */}
        <div className="md:col-span-6 p-5 rounded-2xl bg-[#0F111A]/90 border border-white/10 shadow-xl space-y-3">
          <div className="flex items-center justify-between border-b border-white/10 pb-3">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-bold text-white font-sans uppercase tracking-wider">
                Official AMC Citations & Excerpts
              </h3>
            </div>
            <span className="text-[10px] text-emerald-400 font-mono">100% Grounded</span>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-950/80 border border-white/5 text-xs text-slate-300 font-sans space-y-2">
            <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
              <span>Source: PPFAS Factsheet July 2026 (Page 4)</span>
              <span className="text-emerald-400 font-bold">Vector Chunk #186</span>
            </div>
            <p className="italic text-slate-300 border-l-2 border-cyan-400 pl-2.5 py-0.5">
              “The Scheme seeks to generate long-term capital growth from an actively managed portfolio primarily consisting of equity and equity-related securities.”
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}
