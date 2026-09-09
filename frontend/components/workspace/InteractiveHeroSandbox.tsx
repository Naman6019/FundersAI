"use client";

import React, { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, Sparkles } from "lucide-react";
import { TrustBadge } from "./TrustBadge";
import { ExplainableSignalChips, type SignalChipData } from "./ExplainableSignalChips";

const presetPairings = [
  {
    id: "flexicap",
    label: "PPFAS vs HDFC",
    name: "Parag Parikh vs HDFC Flexi Cap",
    tag: "Flexi Cap Alpha Battle",
    codes: "119551,118955",
    metrics: {
      fundA: { name: "PPFAS Flexi Cap", cagr3y: "21.4%", sharpe: "1.42", maxDrawdown: "-14.2%", ter: "0.62%" },
      fundB: { name: "HDFC Flexi Cap", cagr3y: "23.8%", sharpe: "1.28", maxDrawdown: "-17.8%", ter: "0.85%" },
      alphaDiff: "+2.41%",
      overlap: "24.8%",
    },
  },
  {
    id: "smallcap",
    label: "Quant vs Nippon",
    name: "Quant Small Cap vs Nippon Small Cap",
    tag: "High Beta Volatility Review",
    codes: "120828,118668",
    metrics: {
      fundA: { name: "Quant Small Cap", cagr3y: "32.1%", sharpe: "1.65", maxDrawdown: "-22.1%", ter: "0.77%" },
      fundB: { name: "Nippon Small Cap", cagr3y: "28.4%", sharpe: "1.51", maxDrawdown: "-19.4%", ter: "0.68%" },
      alphaDiff: "+4.12%",
      overlap: "18.2%",
    },
  },
  {
    id: "largecap",
    label: "ICICI vs Mirae",
    name: "ICICI Bluechip vs Mirae Large Cap",
    tag: "Large Cap Core Battle",
    codes: "100356,112090",
    metrics: {
      fundA: { name: "ICICI Bluechip", cagr3y: "16.8%", sharpe: "1.12", maxDrawdown: "-12.5%", ter: "0.91%" },
      fundB: { name: "Mirae Large Cap", cagr3y: "15.4%", sharpe: "1.05", maxDrawdown: "-14.1%", ter: "0.54%" },
      alphaDiff: "+1.25%",
      overlap: "42.1%",
    },
  },
];

function parseSignedPercent(value: string): number {
  return parseFloat(value.replace("%", "").replace("+", ""));
}

function buildSignals(pairing: (typeof presetPairings)[number]): SignalChipData[] {
  const { fundA, fundB, alphaDiff } = pairing.metrics;
  const higherCagr = parseSignedPercent(fundA.cagr3y) >= parseSignedPercent(fundB.cagr3y) ? fundA : fundB;
  const shallowerDrawdown =
    parseSignedPercent(fundA.maxDrawdown) >= parseSignedPercent(fundB.maxDrawdown) ? fundA : fundB;
  const lowerExpense = parseSignedPercent(fundA.ter) <= parseSignedPercent(fundB.ter) ? fundA : fundB;
  const higherSharpe = parseFloat(fundA.sharpe) >= parseFloat(fundB.sharpe) ? fundA : fundB;

  return [
    { type: "alpha", label: "Alpha Advantage", value: `${alphaDiff} 3Y CAGR Edge`, winner: higherCagr.name, isPositive: true },
    {
      type: "drawdown",
      label: "Lower Drawdown Protection",
      value: `${shallowerDrawdown.maxDrawdown} Max Drawdown`,
      winner: shallowerDrawdown.name,
      isPositive: true,
    },
    {
      type: "expense",
      label: "Lower Expense Ratio",
      value: `${lowerExpense.ter} Direct TER`,
      winner: lowerExpense.name,
      isPositive: true,
    },
    {
      type: "sharpe",
      label: "Higher Sharpe Ratio",
      value: `${higherSharpe.sharpe} Risk-Adjusted`,
      winner: higherSharpe.name,
      isPositive: true,
    },
  ];
}

export function InteractiveHeroSandbox() {
  const [selectedIdx, setSelectedIdx] = useState(0);
  const currentPairing = presetPairings[selectedIdx];
  const signals = React.useMemo(() => buildSignals(currentPairing), [currentPairing]);

  return (
    <div className="relative w-full max-w-5xl mx-auto my-8 rounded-2xl p-px bg-gradient-to-r from-[#00FF9D]/30 via-white/10 to-cyan-500/30">
      <div className="relative rounded-[calc(1rem-1px)] p-6 bg-gradient-to-b from-[#0F111A]/95 to-[#07080C]/95 shadow-2xl backdrop-blur-xl overflow-hidden">

      {/* Background Decorative Glow */}
      <div className="absolute top-0 right-1/4 w-96 h-96 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6 border-b border-white/10 pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold uppercase tracking-wider bg-emerald-950/80 text-emerald-300 border border-emerald-800/50">
              Interactive Preview
            </span>
            <TrustBadge status="verified" asOfDate="July 2026" sourceDoc="Sample · AMFI & AMC Factsheet" />
          </div>
          <h3 className="text-xl font-bold text-white tracking-tight font-sans">
            Instant Quantitative Mutual Fund Comparison
          </h3>
        </div>

        {/* Preset Switcher Buttons */}
        <div className="flex items-center gap-1.5 p-1 bg-slate-900/80 border border-white/10 rounded-lg">
          {presetPairings.map((preset, idx) => (
            <button
              key={preset.id}
              onClick={() => setSelectedIdx(idx)}
              className={`relative px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                selectedIdx === idx
                  ? "text-emerald-300"
                  : "text-slate-400 hover:text-slate-200 hover:bg-white/5"
              }`}
            >
              {selectedIdx === idx && (
                <motion.span
                  layoutId="sandbox-tab-highlight"
                  className="absolute inset-0 rounded-md bg-emerald-500/20 border border-emerald-500/40 shadow-sm"
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
              <span className="relative">{preset.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Main Sandbox Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-center">

        {/* Left Side: Side-by-Side Metric Cards */}
        <div className="lg:col-span-7 space-y-4">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentPairing.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
              className="space-y-4"
            >
              <div className="grid grid-cols-2 gap-3">
                {/* Fund A Card */}
                <div className="p-4 rounded-xl bg-slate-900/60 border border-emerald-500/30 relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-16 h-16 bg-emerald-500/10 rounded-bl-full pointer-events-none" />
                  <span className="text-[10px] font-mono uppercase tracking-wider text-emerald-400 font-semibold">Fund A</span>
                  <h4 className="text-sm font-bold text-white mt-1 line-clamp-1">{currentPairing.metrics.fundA.name}</h4>

                  <div className="mt-3 space-y-2 text-xs">
                    <div className="flex justify-between font-mono">
                      <span className="text-slate-400">3Y CAGR:</span>
                      <span className="text-emerald-400 font-bold">{currentPairing.metrics.fundA.cagr3y}</span>
                    </div>
                    <div className="flex justify-between font-mono">
                      <span className="text-slate-400">Sharpe Ratio:</span>
                      <span className="text-white font-semibold">{currentPairing.metrics.fundA.sharpe}</span>
                    </div>
                    <div className="flex justify-between font-mono">
                      <span className="text-slate-400">Max Drawdown:</span>
                      <span className="text-rose-400 font-semibold">{currentPairing.metrics.fundA.maxDrawdown}</span>
                    </div>
                    <div className="flex justify-between font-mono">
                      <span className="text-slate-400">Expense Ratio:</span>
                      <span className="text-slate-300">{currentPairing.metrics.fundA.ter}</span>
                    </div>
                  </div>
                </div>

                {/* Fund B Card */}
                <div className="p-4 rounded-xl bg-slate-900/60 border border-white/10 relative overflow-hidden">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold">Fund B</span>
                  <h4 className="text-sm font-bold text-white mt-1 line-clamp-1">{currentPairing.metrics.fundB.name}</h4>

                  <div className="mt-3 space-y-2 text-xs">
                    <div className="flex justify-between font-mono">
                      <span className="text-slate-400">3Y CAGR:</span>
                      <span className="text-emerald-400 font-bold">{currentPairing.metrics.fundB.cagr3y}</span>
                    </div>
                    <div className="flex justify-between font-mono">
                      <span className="text-slate-400">Sharpe Ratio:</span>
                      <span className="text-white font-semibold">{currentPairing.metrics.fundB.sharpe}</span>
                    </div>
                    <div className="flex justify-between font-mono">
                      <span className="text-slate-400">Max Drawdown:</span>
                      <span className="text-rose-400 font-semibold">{currentPairing.metrics.fundB.maxDrawdown}</span>
                    </div>
                    <div className="flex justify-between font-mono">
                      <span className="text-slate-400">Expense Ratio:</span>
                      <span className="text-slate-300">{currentPairing.metrics.fundB.ter}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Explainable Signals Component */}
              <ExplainableSignalChips signals={signals} />
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Right Side: Dual Product CTA Actions */}
        <div className="lg:col-span-5 p-5 rounded-xl bg-slate-950/80 border border-white/10 space-y-4">
          <div>
            <span className="text-[10px] font-mono uppercase tracking-wider text-cyan-400 font-bold flex items-center gap-1">
              <Sparkles className="w-3 h-3" />
              <span>Ecosystem Actions</span>
            </span>
            <h4 className="text-base font-bold text-white mt-1 font-sans">
              Choose Your Research Experience
            </h4>
            <p className="text-xs text-slate-400 mt-1">
              Explore live metrics in the Research Canvas or generate a multi-page autonomous whitepaper.
            </p>
          </div>

          <div className="space-y-2.5 pt-2">
            {/* CTA 1: Open in Synthesis Studio */}
            <Link
              href={`/synthesis?codes=${currentPairing.codes}`}
              className="w-full flex items-center justify-between p-3 rounded-lg bg-gradient-to-r from-cyan-950/80 to-slate-900 border border-cyan-500/40 hover:border-cyan-400 text-white transition-all group shadow-md"
            >
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-md bg-cyan-500/20 flex items-center justify-center text-cyan-400 font-bold text-sm">
                  ⚡
                </div>
                <div className="text-left">
                  <div className="text-xs font-bold group-hover:text-cyan-300 transition-colors">
                    Synthesis Studio Whitepaper
                  </div>
                  <div className="text-[10px] text-slate-400">Autonomous Multi-Agent Report</div>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-cyan-400 group-hover:translate-x-1 transition-transform" />
            </Link>

            {/* CTA 2: Open in Research Canvas */}
            <Link
              href={`/dashboard?codes=${currentPairing.codes}`}
              className="w-full flex items-center justify-between p-3 rounded-lg bg-slate-900/80 border border-emerald-500/30 hover:border-emerald-400 text-white transition-all group"
            >
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-md bg-emerald-500/20 flex items-center justify-center text-emerald-400 font-bold text-sm">
                  📊
                </div>
                <div className="text-left">
                  <div className="text-xs font-bold group-hover:text-emerald-300 transition-colors">
                    Research Interactive Canvas
                  </div>
                  <div className="text-[10px] text-slate-400">Live Copilot & Side-by-Side Charts</div>
                </div>
              </div>
              <ArrowRight className="w-4 h-4 text-emerald-400 group-hover:translate-x-1 transition-transform" />
            </Link>
          </div>
        </div>

      </div>
      </div>
    </div>
  );
}
