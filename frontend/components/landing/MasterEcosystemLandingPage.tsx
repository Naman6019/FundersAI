"use client";

import React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { EcosystemHeader } from "@/components/ecosystem/EcosystemHeader";
import PublicFooter from "@/components/layout/PublicFooter";
import ProductHuntBadge from "@/components/growth/ProductHuntBadge";
import AmcLogoMarquee from "@/components/landing/AmcLogoMarquee";
import EcosystemBentoGrid from "@/components/landing/EcosystemBentoGrid";
import LiveFundShowcase from "@/components/landing/LiveFundShowcase";
import ZeroHallucinationPipeline from "@/components/landing/ZeroHallucinationPipeline";
import { InteractiveHeroSandbox } from "@/components/workspace/InteractiveHeroSandbox";
import {
  BarChart3,
  ArrowRight,
  CheckCircle2,
} from "lucide-react";

const ease = [0.22, 1, 0.36, 1] as const;
const productHuntPostId = process.env.NEXT_PUBLIC_PRODUCT_HUNT_POST_ID;
const productHuntPostSlug = process.env.NEXT_PUBLIC_PRODUCT_HUNT_POST_SLUG;

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

export default function MasterEcosystemLandingPage() {
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
            className="font-serif-display text-3xl sm:text-5xl lg:text-6xl font-bold text-white tracking-tight leading-[1.12] max-w-5xl mx-auto"
          >
            The Operating System for Modern{" "}
            <span className="text-primary">Mutual Fund Intelligence</span>
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
              className="inline-flex items-center gap-2 px-7 py-3.5 rounded-full bg-[#00FF9D] text-slate-950 font-bold text-sm hover:bg-[#66ffba] transition-all shadow-[0_0_25px_rgba(0,255,157,0.3)] hover:scale-[1.02]"
            >
              <BarChart3 className="w-4 h-4" />
              <span>Explore Research Workspace</span>
              <ArrowRight className="w-4 h-4" />
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
            <Link
              href="/synthesis"
              className="px-3 py-1 rounded-full bg-white/[0.02] border border-white/10 hover:border-cyan-400/30 hover:text-cyan-300 transition"
            >
              📄 Synthesis Studio
            </Link>
            <Link
              href="/mutual-funds"
              className="px-3 py-1 rounded-full bg-white/[0.02] border border-white/10 hover:border-purple-400/30 hover:text-purple-300 transition"
            >
              🔍 Fund Screener
            </Link>
          </motion.div>

          {/* Interactive Hero Sandbox: live fund-duel preview */}
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.5, ease }}
          >
            <InteractiveHeroSandbox />
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
            <h2 className="font-serif-display text-2xl sm:text-4xl font-bold text-white tracking-tight">
              Four Specialized Pillars of Financial Intelligence
            </h2>
            <p className="text-sm text-[#aebed6] leading-relaxed">
              Every tool in FundersAI is designed for deterministic precision, complete source traceability, and zero generative hallucinations.
            </p>
          </div>

          <EcosystemBentoGrid />
        </section>

        {/* ========================================================================= */}
        {/* LIVE FUND & METRICS SHOWCASE                                              */}
        {/* ========================================================================= */}
        <section className="px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
          <LiveFundShowcase />
        </section>

        {/* ========================================================================= */}
        {/* THE ZERO-HALLUCINATION GUARANTEE PIPELINE                                 */}
        {/* ========================================================================= */}
        <section className="px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
          <div className="text-center max-w-3xl mx-auto mb-16 space-y-3">
            <p className="text-xs font-mono font-bold uppercase tracking-[0.22em] text-primary">
              Verification Engine
            </p>
            <h2 className="font-serif-display text-2xl sm:text-4xl font-bold text-white tracking-tight">
              The Zero-Hallucination Pipeline
            </h2>
            <p className="text-sm text-[#aebed6] leading-relaxed">
              How FundersAI transforms raw financial filings into auditable mathematical truth before any AI synthesis.
            </p>
          </div>

          <ZeroHallucinationPipeline />
        </section>

        {/* ========================================================================= */}
        {/* CAPABILITY MATRIX: FUNDERSAI VS COMPETITORS                               */}
        {/* ========================================================================= */}
        <section className="px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
          <div className="text-center max-w-3xl mx-auto mb-12 space-y-3">
            <p className="text-xs font-mono font-bold uppercase tracking-[0.22em] text-accent-synthesis">
              Comparative Advantage
            </p>
            <h2 className="font-serif-display text-2xl sm:text-3xl font-bold text-white tracking-tight">
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
        <AmcLogoMarquee />

        {/* ========================================================================= */}
        {/* FINAL CALL TO ACTION                                                      */}
        {/* ========================================================================= */}
        <section className="px-4 sm:px-6 lg:px-8 max-w-5xl mx-auto text-center">
          <div className="rounded-3xl border border-white/10 bg-gradient-to-b from-white/[0.04] to-transparent p-10 sm:p-16 space-y-6 relative overflow-hidden">
            <h2 className="font-serif-display text-3xl sm:text-5xl font-bold text-white tracking-tight">
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

            {productHuntPostId && productHuntPostSlug ? (
              <div className="pt-6 flex flex-col items-center justify-center gap-2">
                <span className="text-xs font-mono text-slate-400">Find FundersAI on Product Hunt</span>
                <ProductHuntBadge postId={productHuntPostId} postSlug={productHuntPostSlug} theme="neutral" />
              </div>
            ) : null}
          </div>
        </section>
      </main>

      {/* Standard Public Footer */}
      <PublicFooter />
    </div>
  );
}
