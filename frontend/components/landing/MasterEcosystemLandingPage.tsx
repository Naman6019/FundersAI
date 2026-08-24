"use client";

import React, { useState } from "react";
import Link from "next/link";
import Image from "next/image";
import { motion } from "framer-motion";
import { EcosystemHeader } from "@/components/ecosystem/EcosystemHeader";
import PublicFooter from "@/components/layout/PublicFooter";
import { FUND_REGISTRY } from "@/lib/fund-registry";
import {
  BarChart3,
  Zap,
  Layers,
  Calculator,
  ShieldCheck,
  ArrowRight,
  Sparkles,
  TrendingUp,
  Search,
  CheckCircle2,
  Lock,
  FileText,
  Activity,
  Cpu,
  ChevronRight,
  ExternalLink,
  PieChart,
} from "lucide-react";

const ease = [0.22, 1, 0.36, 1] as const;

const FEATURED_FUNDS = [
  {
    name: "Parag Parikh Flexi Cap Fund",
    category: "Flexi Cap",
    amc: "PPFAS",
    cagr3Y: "21.4%",
    cagr5Y: "23.8%",
    sharpe: "1.42",
    href: "/mutual-funds/parag-parikh/parag-parikh-flexi-cap-fund",
    color: "from-emerald-500/20 to-emerald-500/5",
    border: "border-emerald-500/30",
    badge: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
  },
  {
    name: "HDFC Flexi Cap Fund",
    category: "Flexi Cap",
    amc: "HDFC",
    cagr3Y: "23.6%",
    cagr5Y: "22.9%",
    sharpe: "1.38",
    href: "/mutual-funds/hdfc/hdfc-flexi-cap-fund",
    color: "from-blue-500/20 to-blue-500/5",
    border: "border-blue-500/30",
    badge: "text-blue-400 bg-blue-500/10 border-blue-500/20",
  },
  {
    name: "Quant Small Cap Fund",
    category: "Small Cap",
    amc: "Quant",
    cagr3Y: "28.1%",
    cagr5Y: "34.2%",
    sharpe: "1.65",
    href: "/mutual-funds/quant/quant-small-cap-fund",
    color: "from-purple-500/20 to-purple-500/5",
    border: "border-purple-500/30",
    badge: "text-purple-400 bg-purple-500/10 border-purple-500/20",
  },
  {
    name: "Nippon India Small Cap Fund",
    category: "Small Cap",
    amc: "Nippon",
    cagr3Y: "26.4%",
    cagr5Y: "31.5%",
    sharpe: "1.58",
    href: "/mutual-funds/nippon-india/nippon-india-small-cap-fund",
    color: "from-amber-500/20 to-amber-500/5",
    border: "border-amber-500/30",
    badge: "text-amber-400 bg-amber-500/10 border-amber-500/20",
  },
];

const COMPARISON_ROWS = [
  {
    feature: "Calculation Precision",
    fundersAi: "100% Deterministic pure mathematical code (AMFI NAV daily)",
    genericAi: "Probabilistic text generation (prone to hallucinated returns)",
    traditional: "Static historical tables without custom timeline modeling",
  },
  {
    feature: "Data Freshness & Transparency",
    fundersAi: "Field-level timestamp and freshness status on every metric",
    genericAi: "Training cutoff limitations, no live source auditing",
    traditional: "Monthly delayed updates with opaque missing field gaps",
  },
  {
    feature: "Portfolio Overlap & Holding Duels",
    fundersAi: "Live SVG Venn overlap calculation with stock-level weight matching",
    genericAi: "Unable to calculate exact overlapping stock weights",
    traditional: "Locked behind high-cost institutional paywalls",
  },
  {
    feature: "Automated Synthesis Reports",
    fundersAi: "1-Click multi-agent institutional PDF factsheet dossiers",
    genericAi: "Unformatted raw conversational text",
    traditional: "Manual PDF downloading from disparate AMC portals",
  },
  {
    feature: "Zero-Hallucination Policy",
    fundersAi: "Strict abstention boundary when metrics or data are unavailable",
    genericAi: "Guesses and fabricates missing fund details confidently",
    traditional: "N/A (Static)",
  },
];

const AMC_LIST = [
  "HDFC Mutual Fund",
  "Parag Parikh (PPFAS)",
  "SBI Mutual Fund",
  "ICICI Prudential",
  "Nippon India",
  "Quant Mutual Fund",
  "Mirae Asset",
  "Axis Mutual Fund",
  "Kotak Mahindra",
  "Motilal Oswal",
  "UTI Mutual Fund",
  "DSP Mutual Fund",
];

export default function MasterEcosystemLandingPage() {
  const [activeTab, setActiveTab] = useState<"overlap" | "sip" | "screener">("overlap");

  return (
    <div className="min-h-screen bg-[#05070f] text-slate-100 selection:bg-[#00FF9D]/30 selection:text-white flex flex-col justify-between">
      {/* Ecosystem Header */}
      <EcosystemHeader currentApp="none" />

      <main className="flex-1 w-full space-y-24 sm:space-y-32 pb-24">
        {/* ========================================================================= */}
        {/* HERO SECTION                                                             */}
        {/* ========================================================================= */}
        <section className="relative pt-16 sm:pt-24 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto text-center">
          {/* Subtle Ambient Glows */}
          <div className="pointer-events-none absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[350px] bg-gradient-to-r from-emerald-500/10 via-cyan-500/10 to-blue-500/10 blur-[130px] rounded-full -z-10" />

          {/* Top Live Signal Pill */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease }}
            className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-white/10 bg-white/[0.03] backdrop-blur-md mb-8 text-xs font-mono text-slate-300"
          >
            <span className="w-2 h-2 rounded-full bg-[#00FF9D] animate-pulse" />
            <span className="text-white font-semibold">FundersAI Ecosystem</span>
            <span className="text-slate-500">|</span>
            <span className="text-[#aebed6]">Next-Gen Indian Capital Markets Intelligence</span>
          </motion.div>

          {/* Main Hero Headline */}
          <motion.h1
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1, ease }}
            className="text-3xl sm:text-5xl lg:text-6xl font-extrabold text-white tracking-tight leading-[1.12] max-w-5xl mx-auto"
          >
            The Operating System for Modern{" "}
            <span className="bg-gradient-to-r from-[#00FF9D] via-[#66a3ff] to-[#a78bfa] bg-clip-text text-transparent">
              Mutual Fund Intelligence
            </span>
          </motion.h1>

          {/* Subtitle */}
          <motion.p
            initial={{ opacity: 0, y: 15 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2, ease }}
            className="mt-6 text-base sm:text-lg text-[#aebed6] max-w-3xl mx-auto leading-relaxed"
          >
            Uniting deterministic AMFI quantitative pipelines, autonomous multi-agent research synthesis,
            institutional fund screeners, and investor utility calculators in one unified platform.
          </motion.p>

          {/* Call to Actions */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3, ease }}
            className="mt-10 flex flex-wrap items-center justify-center gap-4"
          >
            <Link
              href="/research"
              className="inline-flex items-center gap-2 px-6 py-3.5 rounded-full bg-[#00FF9D] text-slate-950 font-bold text-sm hover:bg-[#66ffba] transition-all shadow-[0_0_25px_rgba(0,255,157,0.3)] hover:scale-[1.02]"
            >
              <BarChart3 className="w-4 h-4" />
              <span>Explore Research Workspace</span>
              <ArrowRight className="w-4 h-4" />
            </Link>

            <Link
              href="/synthesis"
              className="inline-flex items-center gap-2 px-6 py-3.5 rounded-full bg-white/[0.05] border border-cyan-500/30 text-cyan-300 font-semibold text-sm hover:bg-cyan-500/10 transition-all hover:scale-[1.02]"
            >
              <Zap className="w-4 h-4 text-cyan-400" />
              <span>Launch Synthesis Studio</span>
            </Link>

            <Link
              href="/mutual-funds"
              className="inline-flex items-center gap-2 px-6 py-3.5 rounded-full bg-white/[0.03] border border-white/10 text-slate-200 font-medium text-sm hover:bg-white/[0.07] transition-all"
            >
              <Layers className="w-4 h-4 text-purple-400" />
              <span>Fund Screener</span>
            </Link>
          </motion.div>

          {/* Quick Utility Chips */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="mt-8 flex flex-wrap items-center justify-center gap-2 text-xs text-slate-400"
          >
            <span className="font-mono text-slate-500 uppercase tracking-wider text-[11px]">Quick Jump:</span>
            <Link
              href="/tools/portfolio-overlap"
              className="px-3 py-1 rounded-full bg-white/[0.02] border border-white/10 hover:border-blue-400/30 hover:text-blue-300 transition"
            >
              ⚡ Portfolio Overlap
            </Link>
            <Link
              href="/tools/sip-calculator"
              className="px-3 py-1 rounded-full bg-white/[0.02] border border-white/10 hover:border-[#00FF9D]/30 hover:text-[#00FF9D] transition"
            >
              📈 Step-Up SIP Calculator
            </Link>
            <Link
              href="/compare/hdfc-flexi-cap-fund-vs-parag-parikh-flexi-cap-fund"
              className="px-3 py-1 rounded-full bg-white/[0.02] border border-white/10 hover:border-purple-400/30 hover:text-purple-300 transition"
            >
              ⚔️ PPFAS vs HDFC Flexi Cap
            </Link>
            <Link
              href="/data-trust"
              className="px-3 py-1 rounded-full bg-white/[0.02] border border-white/10 hover:border-amber-400/30 hover:text-amber-300 transition"
            >
              🛡️ Data Trust Standards
            </Link>
          </motion.div>
        </section>

        {/* ========================================================================= */}
        {/* 4 CORE PRODUCT PILLARS                                                    */}
        {/* ========================================================================= */}
        <section className="px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
          <div className="text-center max-w-3xl mx-auto mb-16 space-y-3">
            <p className="text-xs font-mono font-bold uppercase tracking-[0.22em] text-[#00FF9D]">
              Ecosystem Architecture
            </p>
            <h2 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight">
              Four Specialized Pillars of Financial Intelligence
            </h2>
            <p className="text-sm text-[#aebed6] leading-relaxed">
              Every tool in FundersAI is designed for deterministic precision, complete source traceability, and zero generative hallucinations.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Pillar 1: Research Workspace */}
            <div className="relative group rounded-3xl border border-emerald-500/20 bg-gradient-to-b from-emerald-500/[0.06] to-transparent p-8 sm:p-10 flex flex-col justify-between hover:border-emerald-500/40 transition-all">
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="p-3 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-[#00FF9D]">
                    <BarChart3 className="w-6 h-6" />
                  </div>
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-[#00FF9D] px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20">
                    Flagship Workspace
                  </span>
                </div>

                <div>
                  <h3 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                    Interactive Research Workspace
                  </h3>
                  <p className="text-sm text-[#aebed6] mt-2 leading-relaxed">
                    A conversational quantitative terminal with live mathematical computation. Ask complex fund queries, calculate Sharpe ratios, inspect active alphas, and review cited evidence rows in real-time.
                  </p>
                </div>

                <ul className="space-y-2.5 text-xs text-slate-300 font-mono">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-[#00FF9D] shrink-0" />
                    <span>Pure deterministic code execution (no LLM math)</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-[#00FF9D] shrink-0" />
                    <span>Live data freshness timestamps & limitation disclosures</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-[#00FF9D] shrink-0" />
                    <span>Multi-tab side-by-side comparison canvas</span>
                  </li>
                </ul>
              </div>

              <div className="mt-8 pt-6 border-t border-white/10 flex items-center justify-between">
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
            </div>

            {/* Pillar 2: Synthesis Studio */}
            <div className="relative group rounded-3xl border border-cyan-500/20 bg-gradient-to-b from-cyan-500/[0.06] to-transparent p-8 sm:p-10 flex flex-col justify-between hover:border-cyan-500/40 transition-all">
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="p-3 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
                    <Zap className="w-6 h-6" />
                  </div>
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-cyan-400 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20">
                    Autonomous AI Studio
                  </span>
                </div>

                <div>
                  <h3 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                    Synthesis Report Studio
                  </h3>
                  <p className="text-sm text-[#aebed6] mt-2 leading-relaxed">
                    Autonomous multi-agent research engine that generates complete, institutional-grade mutual fund factsheets, risk dossiers, and portfolio overlap comparison reports with 1-click PDF exports.
                  </p>
                </div>

                <ul className="space-y-2.5 text-xs text-slate-300 font-mono">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
                    <span>Multi-agent autonomous research orchestration</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
                    <span>Institutional risk ratings & holding overlap breakdown</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-cyan-400 shrink-0" />
                    <span>Serverless direct PDF dossier download</span>
                  </li>
                </ul>
              </div>

              <div className="mt-8 pt-6 border-t border-white/10 flex items-center justify-between">
                <Link
                  href="/synthesis"
                  className="text-xs font-bold text-cyan-400 hover:text-cyan-300 inline-flex items-center gap-1.5 transition"
                >
                  <span>Explore Synthesis Studio</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
                <Link
                  href="/synthesis/generate"
                  className="px-4 py-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-xs font-semibold text-cyan-300 hover:bg-cyan-500/20 transition"
                >
                  Generate Dossier 📄
                </Link>
              </div>
            </div>

            {/* Pillar 3: Screener & Directory */}
            <div className="relative group rounded-3xl border border-purple-500/20 bg-gradient-to-b from-purple-500/[0.06] to-transparent p-8 sm:p-10 flex flex-col justify-between hover:border-purple-500/40 transition-all">
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="p-3 rounded-2xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
                    <Layers className="w-6 h-6" />
                  </div>
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-purple-400 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20">
                    Directory & Directory
                  </span>
                </div>

                <div>
                  <h3 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                    Mutual Fund Screener & Registry
                  </h3>
                  <p className="text-sm text-[#aebed6] mt-2 leading-relaxed">
                    Filter and discover 30+ top Indian mutual fund schemes across 12 AMC fund houses and SEBI categories. Includes direct plan tracking, benchmark TRI comparisons, and verified AMFI codes.
                  </p>
                </div>

                <ul className="space-y-2.5 text-xs text-slate-300 font-mono">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-purple-400 shrink-0" />
                    <span>Real-time AMC & SEBI category dual-filtering</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-purple-400 shrink-0" />
                    <span>Benchmark TRI comparison & expense ratio metrics</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-purple-400 shrink-0" />
                    <span>Deep fund factsheet and NAV pages for each scheme</span>
                  </li>
                </ul>
              </div>

              <div className="mt-8 pt-6 border-t border-white/10 flex items-center justify-between">
                <Link
                  href="/mutual-funds"
                  className="text-xs font-bold text-purple-400 hover:text-purple-300 inline-flex items-center gap-1.5 transition"
                >
                  <span>Launch Screener</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
                <span className="text-xs font-mono text-slate-400">30+ Indexed Funds</span>
              </div>
            </div>

            {/* Pillar 4: Public Financial Tools Suite */}
            <div className="relative group rounded-3xl border border-blue-500/20 bg-gradient-to-b from-blue-500/[0.06] to-transparent p-8 sm:p-10 flex flex-col justify-between hover:border-blue-500/40 transition-all">
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="p-3 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
                    <Calculator className="w-6 h-6" />
                  </div>
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-blue-400 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20">
                    Public Utilities
                  </span>
                </div>

                <div>
                  <h3 className="text-xl sm:text-2xl font-bold text-white tracking-tight">
                    Public Quantitative Tools Suite
                  </h3>
                  <p className="text-sm text-[#aebed6] mt-2 leading-relaxed">
                    Zero-login, high-performance financial calculators including the Visual Portfolio Overlap Venn Engine, Exponential Step-Up SIP Compounding Calculator, and Comparison Duels.
                  </p>
                </div>

                <ul className="space-y-2.5 text-xs text-slate-300 font-mono">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-blue-400 shrink-0" />
                    <span>Visual SVG Venn diagram overlap percentage calculator</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-blue-400 shrink-0" />
                    <span>Compounding spline charts with salary step-up increments</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-blue-400 shrink-0" />
                    <span>1-Click shareable URLs with clipboard toast feedback</span>
                  </li>
                </ul>
              </div>

              <div className="mt-8 pt-6 border-t border-white/10 flex items-center justify-between">
                <Link
                  href="/tools"
                  className="text-xs font-bold text-blue-400 hover:text-blue-300 inline-flex items-center gap-1.5 transition"
                >
                  <span>Explore All Public Tools</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
                <span className="text-xs font-mono text-slate-400">100% Free · No Login</span>
              </div>
            </div>
          </div>
        </section>

        {/* ========================================================================= */}
        {/* LIVE FUND & METRICS SHOWCASE                                              */}
        {/* ========================================================================= */}
        <section className="px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
          <div className="rounded-3xl border border-white/10 bg-white/[0.02] p-8 sm:p-12 relative overflow-hidden">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-10 pb-8 border-b border-white/10">
              <div>
                <p className="text-xs font-mono font-bold uppercase tracking-[0.22em] text-[#00FF9D]">
                  Live Fund Metrics
                </p>
                <h2 className="text-2xl sm:text-3xl font-bold text-white mt-1">
                  Sample Quantitative Metrics from Verified Disclosures
                </h2>
                <p className="text-xs sm:text-sm text-[#aebed6] mt-1.5">
                  Calculated deterministically from AMFI NAV histories and official AMC factsheet portfolios.
                </p>
              </div>

              <Link
                href="/mutual-funds"
                className="inline-flex items-center gap-2 text-xs font-mono font-bold text-[#00FF9D] hover:underline shrink-0"
              >
                <span>View all 30+ schemes in screener</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {FEATURED_FUNDS.map((fund) => (
                <Link
                  key={fund.name}
                  href={fund.href}
                  className={`group rounded-2xl border ${fund.border} bg-gradient-to-b ${fund.color} p-6 flex flex-col justify-between hover:scale-[1.02] transition-all`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${fund.badge}`}>
                        {fund.category}
                      </span>
                      <span className="text-xs font-mono text-slate-400">{fund.amc}</span>
                    </div>
                    <h4 className="text-sm font-bold text-white group-hover:text-[#00FF9D] transition leading-snug">
                      {fund.name}
                    </h4>
                  </div>

                  <div className="mt-6 pt-4 border-t border-white/10 grid grid-cols-3 gap-2 text-center">
                    <div>
                      <p className="text-[10px] font-mono text-slate-400">3Y CAGR</p>
                      <p className="text-xs font-bold text-white font-mono mt-0.5">{fund.cagr3Y}</p>
                    </div>
                    <div>
                      <p className="text-[10px] font-mono text-slate-400">5Y CAGR</p>
                      <p className="text-xs font-bold text-white font-mono mt-0.5">{fund.cagr5Y}</p>
                    </div>
                    <div>
                      <p className="text-[10px] font-mono text-slate-400">Sharpe</p>
                      <p className="text-xs font-bold text-[#00FF9D] font-mono mt-0.5">{fund.sharpe}</p>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        </section>

        {/* ========================================================================= */}
        {/* THE ZERO-HALLUCINATION GUARANTEE PIPELINE                                 */}
        {/* ========================================================================= */}
        <section className="px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
          <div className="text-center max-w-3xl mx-auto mb-16 space-y-3">
            <p className="text-xs font-mono font-bold uppercase tracking-[0.22em] text-[#66a3ff]">
              Verification Engine
            </p>
            <h2 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight">
              The Zero-Hallucination Pipeline
            </h2>
            <p className="text-sm text-[#aebed6] leading-relaxed">
              How FundersAI transforms raw financial filings into auditable mathematical truth before any AI synthesis.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6 space-y-3">
              <div className="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-[#00FF9D] flex items-center justify-center font-mono font-bold text-xs">
                01
              </div>
              <h4 className="text-base font-bold text-white">Regulated Sourcing</h4>
              <p className="text-xs text-[#aebed6] leading-relaxed">
                Direct ingestion from AMFI daily NAV feeds, NSE benchmark TRI indexes, and official monthly AMC portfolio disclosures.
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6 space-y-3">
              <div className="w-8 h-8 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center font-mono font-bold text-xs">
                02
              </div>
              <h4 className="text-base font-bold text-white">Deterministic Math</h4>
              <p className="text-xs text-[#aebed6] leading-relaxed">
                Pure TypeScript & Python financial formulas calculate CAGR, Sharpe, Sortino, Alpha, and portfolio overlaps. No LLM arithmetic.
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6 space-y-3">
              <div className="w-8 h-8 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center font-mono font-bold text-xs">
                03
              </div>
              <h4 className="text-base font-bold text-white">Visible Limitations</h4>
              <p className="text-xs text-[#aebed6] leading-relaxed">
                Whenever a field is missing, stale, or unavailable, FundersAI discloses the exact limit before generating research answers.
              </p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-6 space-y-3">
              <div className="w-8 h-8 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center font-mono font-bold text-xs">
                04
              </div>
              <h4 className="text-base font-bold text-white">Grounded Synthesis</h4>
              <p className="text-xs text-[#aebed6] leading-relaxed">
                Multi-agent LLM summaries only interpret calculated figures and cite source documents. Financial advice is strictly declined.
              </p>
            </div>
          </div>
        </section>

        {/* ========================================================================= */}
        {/* CAPABILITY MATRIX: FUNDERSAI VS COMPETITORS                               */}
        {/* ========================================================================= */}
        <section className="px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
          <div className="text-center max-w-3xl mx-auto mb-12 space-y-3">
            <p className="text-xs font-mono font-bold uppercase tracking-[0.22em] text-[#a78bfa]">
              Comparative Advantage
            </p>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Why Investors Trust FundersAI
            </h2>
          </div>

          <div className="overflow-x-auto rounded-3xl border border-white/10 bg-white/[0.015]">
            <table className="w-full text-left text-xs sm:text-sm">
              <thead className="bg-white/[0.03] border-b border-white/10 text-slate-300 font-mono text-[11px] uppercase tracking-wider">
                <tr>
                  <th className="p-4 sm:p-5">Capability</th>
                  <th className="p-4 sm:p-5 text-[#00FF9D]">FundersAI Ecosystem</th>
                  <th className="p-4 sm:p-5 text-slate-400">Generic AI Chatbots</th>
                  <th className="p-4 sm:p-5 text-slate-400">Legacy Fund Portals</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-slate-300">
                {COMPARISON_ROWS.map((row) => (
                  <tr key={row.feature} className="hover:bg-white/[0.01]">
                    <td className="p-4 sm:p-5 font-semibold text-white">{row.feature}</td>
                    <td className="p-4 sm:p-5 text-[#aebed6] bg-[#00FF9D]/[0.02] border-x border-[#00FF9D]/10">
                      <div className="flex items-start gap-2">
                        <CheckCircle2 className="w-4 h-4 text-[#00FF9D] shrink-0 mt-0.5" />
                        <span>{row.fundersAi}</span>
                      </div>
                    </td>
                    <td className="p-4 sm:p-5 text-slate-400">{row.genericAi}</td>
                    <td className="p-4 sm:p-5 text-slate-400">{row.traditional}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ========================================================================= */}
        {/* AMC FUND HOUSE COVERAGE                                                   */}
        {/* ========================================================================= */}
        <section className="px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto text-center space-y-6">
          <p className="text-xs font-mono font-bold uppercase tracking-[0.22em] text-slate-400">
            Supported Fund House Families
          </p>
          <div className="flex flex-wrap justify-center gap-2.5 max-w-4xl mx-auto">
            {AMC_LIST.map((amc) => (
              <span
                key={amc}
                className="px-4 py-2 rounded-full border border-white/10 bg-white/[0.02] text-xs font-medium text-[#aebed6]"
              >
                {amc}
              </span>
            ))}
          </div>
        </section>

        {/* ========================================================================= */}
        {/* FINAL CALL TO ACTION                                                      */}
        {/* ========================================================================= */}
        <section className="px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto text-center">
          <div className="rounded-3xl border border-white/10 bg-gradient-to-b from-white/[0.04] to-transparent p-10 sm:p-16 space-y-6 relative overflow-hidden">
            <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
              Ready for Research-Grade Mutual Fund Intelligence?
            </h2>
            <p className="text-sm sm:text-base text-[#aebed6] max-w-2xl mx-auto leading-relaxed">
              Start with our free public tools or open the interactive research workspace to analyze Indian mutual funds with verified mathematical accuracy.
            </p>

            <div className="pt-4 flex flex-wrap justify-center gap-4">
              <Link
                href="/research"
                className="px-6 py-3.5 rounded-full bg-[#00FF9D] text-slate-950 font-bold text-sm hover:bg-[#66ffba] transition shadow-[0_0_25px_rgba(0,255,157,0.3)] hover:scale-[1.02]"
              >
                Launch Research Workspace ⚡
              </Link>
              <Link
                href="/tools"
                className="px-6 py-3.5 rounded-full bg-white/5 border border-white/10 text-white font-semibold text-sm hover:bg-white/10 transition"
              >
                Open Free Public Tools 🛠️
              </Link>
            </div>
          </div>
        </section>
      </main>

      {/* Standard Public Footer */}
      <PublicFooter />
    </div>
  );
}
