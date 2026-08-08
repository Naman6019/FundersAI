"use client";

import { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { MagicCard } from "@/components/ui/magic-card";
import { ShimmerButton } from "@/components/ui/shimmer-button";
import { BorderBeam } from "@/components/ui/border-beam";
import { AnimatedShinyText } from "@/components/ui/animated-shiny-text";
import { Sparkles } from "@/components/ui/sparkles";
import { FlickeringGrid } from "@/components/ui/flickering-grid";
import { VerticalCutReveal } from "@/components/ui/vertical-cut-reveal";

// Data Definitions
const heroPresets = [
    {
        title: "HDFC Defence Fund vs Quant Small Cap",
        tag: "#DEFENCE_VS_VOLATILITY",
        codes: "151745,120828"
    },
    {
        title: "Parag Parikh Flexi Cap vs SBI Contra",
        tag: "#VALUE_VS_CONTRARIAN",
        codes: "119551,100033"
    },
    {
        title: "ICICI Bluechip vs Mirae Asset Large Cap",
        tag: "#BLUECHIP_ALPHA_BATTLE",
        codes: "100356,112090"
    }
];

const trendingComparisons = [
    {
        title: "PPFAS Flexi Cap vs HDFC Flexi Cap",
        badge: "Flexi Cap Alpha Battle",
        slug: "parag-parikh-flexi-cap-vs-hdfc-flexi-cap",
        tag: "Most Popular"
    },
    {
        title: "Quant Small Cap vs Nippon Small Cap",
        badge: "High Beta Volatility Review",
        slug: "quant-small-cap-vs-nippon-india-small-cap",
        tag: "High CAGR"
    },
    {
        title: "Nifty 50 Index vs Parag Parikh Flexi Cap",
        badge: "Active vs Passive Alpha",
        slug: "nifty-50-vs-parag-parikh-flexi-cap",
        tag: "Benchmark"
    },
    {
        title: "Axis ELSS vs Mirae Asset Tax Saver",
        badge: "80C Tax Saver Review",
        slug: "axis-elss-vs-mirae-asset-tax-saver",
        tag: "Tax Saver"
    }
];

const previewTabs = [
    { id: "verdict", label: "Executive Verdict" },
    { id: "metrics", label: "Risk Metrics Matrix" },
    { id: "visuals", label: "Mermaid Diagrams" },
    { id: "pdf", label: "Direct PDF Export" },
];

const amcPipelines = [
    { name: "PPFAS Mutual Fund", status: "Factsheets Ingested", time: "2m ago", color: "text-emerald-400" },
    { name: "HDFC Mutual Fund", status: "NAV Synced", time: "Just now", color: "text-emerald-400" },
    { name: "SBI Mutual Fund", status: "Factsheets Ingested", time: "5m ago", color: "text-emerald-400" },
    { name: "ICICI Prudential MF", status: "Disclosures Verified", time: "12m ago", color: "text-cyan-400" },
    { name: "Kotak Mutual Fund", status: "Factsheets Ingested", time: "1m ago", color: "text-emerald-400" },
    { name: "Quant Mutual Fund", status: "Risk Metrics Synced", time: "Just now", color: "text-blue-400" }
];

const faqs = [
    {
        q: "How does Synthesis eliminate LLM financial hallucinations?",
        a: "Synthesis operates on strict quantitative boundaries. Every NAV, CAGR return, Sharpe ratio, and expense ratio is calculated deterministically from official AMC factsheet disclosures and Supabase snapshot database rows, completely bypassing LLM text generation for math."
    },
    {
        q: "Which AMC factsheets and scheme documents are supported?",
        a: "We index official monthly factsheets, scheme information documents (SIDs), and portfolio holdings disclosures across all major SEBI-registered Asset Management Companies including PPFAS, HDFC, SBI, ICICI Prudential, Kotak, Nippon India, and Quant AMC."
    },
    {
        q: "Is Synthesis personalized investment advice or research-only?",
        a: "Synthesis is strictly a quantitative research tool for comparative factsheet analysis. No automated buy, sell, or hold recommendations are ever generated. Missing fields and data limitations are disclosed transparently."
    },
    {
        q: "Can I download reports as PDFs for investment committees or clients?",
        a: "Yes! Synthesis features a dedicated serverless Chromium rendering backend powered by Playwright. You can export complete multi-page institutional PDF reports with 1 click."
    }
];

export default function ReportsLandingPage() {
    const [activeTab, setActiveTab] = useState("verdict");
    const [openFaq, setOpenFaq] = useState<number | null>(0);
    const [heroSelectedPreset, setHeroSelectedPreset] = useState(0);
    const [heroSimulatedProgress, setHeroSimulatedProgress] = useState(4);

    const runHeroPreset = (idx: number) => {
        setHeroSelectedPreset(idx);
        setHeroSimulatedProgress(1);
        setTimeout(() => setHeroSimulatedProgress(2), 300);
        setTimeout(() => setHeroSimulatedProgress(3), 600);
        setTimeout(() => setHeroSimulatedProgress(4), 900);
    };

    return (
        <div className="relative flex-1 flex flex-col items-center justify-center px-4 sm:px-6 lg:px-8 py-16 overflow-hidden">
            {/* Optimized High-Performance Flickering Grid Background */}
            <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none [mask-image:radial-gradient(1400px_circle_at_center,white_75%,transparent_100%)]">
                <FlickeringGrid
                    squareSize={6}
                    gridGap={10}
                    color="rgb(37, 99, 235)"
                    maxOpacity={0.22}
                    flickerChance={0.2}
                    className="w-full h-full"
                />
            </div>

            <div className="max-w-[1800px] w-full space-y-24 relative z-10 px-4 sm:px-6 lg:px-8">
                {/* Hero Header Section */}
                <div className="text-center space-y-8 max-w-4xl mx-auto">
                    {/* Status Badge */}
                    <motion.div
                        initial={{ opacity: 0, y: -8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.4, ease: "easeOut" }}
                        className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 shadow-sm backdrop-blur-md"
                    >
                        <span className="w-2 h-2 rounded-full bg-blue-400 animate-ping" />
                        <AnimatedShinyText className="text-xs font-mono font-bold uppercase tracking-widest text-blue-400">
                            ✨ AUTONOMOUS MULTI-AGENT SYNTHESIS ENGINE v2.4
                        </AnimatedShinyText>
                    </motion.div>

                    {/* Per-Letter Character Reveal Headline with 60fps GPU Acceleration */}
                    <div className="flex flex-col items-center justify-center space-y-3">
                        <VerticalCutReveal
                            splitBy="characters"
                            staggerDuration={0.015}
                            staggerFrom="first"
                            transition={{ duration: 0.4, ease: [0.25, 1, 0.5, 1] }}
                            containerClassName="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight leading-[1.1] font-serif-display justify-center text-center"
                            elementClassName="text-white"
                        >
                            Institutional-Grade Synthesis.
                        </VerticalCutReveal>

                        <VerticalCutReveal
                            splitBy="characters"
                            staggerDuration={0.015}
                            staggerFrom="first"
                            transition={{ duration: 0.4, ease: [0.25, 1, 0.5, 1], delay: 0.35 }}
                            containerClassName="text-4xl sm:text-6xl lg:text-7xl font-extrabold tracking-tight leading-[1.1] font-serif-display justify-center text-center"
                            elementClassName="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-cyan-400 to-emerald-400"
                        >
                            Generated in Seconds.
                        </VerticalCutReveal>
                    </div>

                    {/* Hero Subtitle */}
                    <motion.p
                        initial={{ opacity: 0, y: 15 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.4, delay: 0.7, ease: "easeOut" }}
                        className="text-base sm:text-lg text-gray-400 max-w-2xl mx-auto leading-relaxed font-sans"
                    >
                        <strong className="text-gray-200">Synthesis by FundersAI</strong> leverages autonomous multi-agent graphs to ingest, parse, and synthesize hundreds of official AMC factsheets and SEBI disclosures into clear quantitative comparison reports.
                    </motion.p>

                    {/* Action Button Group */}
                    <motion.div
                        initial={{ opacity: 0, y: 15 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.4, delay: 0.85, ease: "easeOut" }}
                        className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2"
                    >
                        <Link href="/reports/generate">
                            <ShimmerButton
                                className="px-8 py-3.5 shadow-2xl transition-transform duration-200 hover:-translate-y-0.5"
                                shimmerColor="#ffffff"
                                shimmerSize="0.06em"
                                borderRadius="12px"
                                background="#2563eb"
                            >
                                <span className="text-white font-mono font-bold text-xs uppercase tracking-wider flex items-center gap-2">
                                    <span>Start Synthesizing</span>
                                    <span>→</span>
                                </span>
                            </ShimmerButton>
                        </Link>
                        <Link
                            href="/billing"
                            className="px-6 py-3 bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-600 text-white font-mono font-bold text-xs uppercase tracking-wider rounded-xl hover:brightness-110 transition-all duration-200 hover:-translate-y-0.5 backdrop-blur-md shadow-lg shadow-blue-900/30 flex items-center gap-1.5"
                        >
                            <span>⚡ Upgrade Plan</span>
                        </Link>
                        <Link
                            href="/reports/supported-funds"
                            className="px-6 py-3 bg-gray-950/90 border border-gray-800 text-gray-300 font-mono font-medium text-xs uppercase tracking-wider rounded-xl hover:bg-gray-800 hover:text-white transition-all duration-200 hover:-translate-y-0.5 backdrop-blur-md"
                        >
                            Supported Directory
                        </Link>
                    </motion.div>

                    {/* Interactive Hero Studio Workspace Frame */}
                    <motion.div
                        initial={{ opacity: 0, y: 25 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.6, delay: 1.0, ease: "easeOut" }}
                        className="relative max-w-5xl mx-auto w-full pt-6"
                    >
                        {/* Background Subtle Radial Aura */}
                        <div className="absolute inset-0 bg-blue-600/15 blur-[120px] rounded-full pointer-events-none" />

                        {/* Floating Telemetry Badge Left */}
                        <div className="hidden lg:flex absolute -left-12 top-20 z-30 items-center gap-3 p-3.5 rounded-2xl bg-[#070b12]/90 border border-emerald-500/40 shadow-2xl backdrop-blur-xl transition-transform duration-300 hover:-translate-y-1">
                            <div className="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-bold text-sm">
                                🛡️
                            </div>
                            <div className="text-left font-mono">
                                <div className="text-[10px] text-gray-400 uppercase tracking-wider">Zero-Hallucination</div>
                                <div className="text-xs font-bold text-emerald-400">100% Factsheet Verifiable</div>
                            </div>
                        </div>

                        {/* Floating Telemetry Badge Right */}
                        <div className="hidden lg:flex absolute -right-12 bottom-20 z-30 items-center gap-3 p-3.5 rounded-2xl bg-[#070b12]/90 border border-cyan-500/40 shadow-2xl backdrop-blur-xl transition-transform duration-300 hover:-translate-y-1">
                            <div className="w-8 h-8 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 font-bold text-sm">
                                ⚡
                            </div>
                            <div className="text-left font-mono">
                                <div className="text-[10px] text-gray-400 uppercase tracking-wider">PDF Export Speed</div>
                                <div className="text-xs font-bold text-cyan-400">0.4s Serverless Latency</div>
                            </div>
                        </div>

                        {/* Main Studio Frame Mockup Container */}
                        <div className="relative bg-[#070b12]/95 border border-gray-800/90 rounded-2xl p-6 sm:p-8 space-y-6 shadow-2xl backdrop-blur-2xl overflow-hidden text-left border-t-blue-500/40">
                            {/* Magic UI Border Beam Component */}
                            <BorderBeam size={280} duration={12} delay={9} colorFrom="#2563eb" colorTo="#22d3ee" />
                            <Sparkles density={20} color="#3b82f6" className="absolute inset-0 pointer-events-none opacity-20" />

                            {/* Studio Window Header */}
                            <div className="flex items-center justify-between border-b border-gray-800/80 pb-4 relative z-10">
                                <div className="flex items-center gap-2">
                                    <span className="w-3 h-3 rounded-full bg-red-500/80 inline-block" />
                                    <span className="w-3 h-3 rounded-full bg-amber-500/80 inline-block" />
                                    <span className="w-3 h-3 rounded-full bg-emerald-500/80 inline-block" />
                                    <span className="text-xs font-mono text-gray-400 ml-2 font-bold">FundersAI / Synthesis / [ LIVE_DEMO_WORKSTATION ]</span>
                                </div>
                                <div className="flex items-center gap-2 font-mono text-[10px]">
                                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                                    <span className="text-emerald-400 font-bold">SEBI AMC PIPELINE ACTIVE</span>
                                </div>
                            </div>

                            {/* Interactive Preset Selector Bar inside Hero */}
                            <div className="space-y-3 relative z-10">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs font-mono font-bold uppercase tracking-wider text-gray-300">
                                        Test Live Synthesis Presets:
                                    </span>
                                    <span className="text-[10px] font-mono text-blue-400 font-semibold">Click to run interactive pipeline ↓</span>
                                </div>

                                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                    {heroPresets.map((preset, idx) => (
                                        <button
                                            key={idx}
                                            onClick={() => runHeroPreset(idx)}
                                            className={`p-3.5 rounded-xl text-left border transition-all duration-150 font-mono text-xs flex flex-col justify-between space-y-2 transform-gpu ${
                                                heroSelectedPreset === idx
                                                    ? "bg-blue-600/20 border-blue-500 text-white shadow-lg shadow-blue-900/30 scale-[1.01]"
                                                    : "bg-gray-900/60 border-gray-800 text-gray-400 hover:border-gray-700 hover:text-white hover:scale-[1.01]"
                                            }`}
                                        >
                                            <div className="font-bold truncate">{preset.title}</div>
                                            <div className="text-[10px] text-cyan-400 font-semibold">{preset.tag}</div>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            {/* Execution Pipeline Progress Animation inside Hero Frame */}
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 relative z-10 font-mono text-xs">
                                <div className={`p-3 rounded-xl border flex items-center gap-2.5 transition-all duration-200 ${
                                    heroSimulatedProgress >= 1 ? 'bg-blue-500/10 border-blue-500/40 text-blue-400 shadow-md shadow-blue-500/10' : 'bg-gray-900/40 border-gray-800 text-gray-600'
                                }`}>
                                    <span className="font-bold text-[10px] px-1.5 py-0.5 rounded bg-blue-500/20">#01</span>
                                    <span className="font-semibold text-[11px]">INGEST_AMC</span>
                                </div>
                                <div className={`p-3 rounded-xl border flex items-center gap-2.5 transition-all duration-200 ${
                                    heroSimulatedProgress >= 2 ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-400 shadow-md shadow-emerald-500/10' : 'bg-gray-900/40 border-gray-800 text-gray-600'
                                }`}>
                                    <span className="font-bold text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/20">#02</span>
                                    <span className="font-semibold text-[11px]">RISK_MATRIX</span>
                                </div>
                                <div className={`p-3 rounded-xl border flex items-center gap-2.5 transition-all duration-200 ${
                                    heroSimulatedProgress >= 3 ? 'bg-purple-500/10 border-purple-500/40 text-purple-400 shadow-md shadow-purple-500/10' : 'bg-gray-900/40 border-gray-800 text-gray-600'
                                }`}>
                                    <span className="font-bold text-[10px] px-1.5 py-0.5 rounded bg-purple-500/20">#03</span>
                                    <span className="font-semibold text-[11px]">MERMAID_TREES</span>
                                </div>
                                <div className={`p-3 rounded-xl border flex items-center gap-2.5 transition-all duration-200 ${
                                    heroSimulatedProgress >= 4 ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-400 shadow-md shadow-cyan-500/10' : 'bg-gray-900/40 border-gray-800 text-gray-600'
                                }`}>
                                    <span className="font-bold text-[10px] px-1.5 py-0.5 rounded bg-cyan-500/20">#04</span>
                                    <span className="font-semibold text-[11px]">FORMAT_PDF</span>
                                </div>
                            </div>

                            {/* Workstation Action Footer */}
                            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4 border-t border-gray-800/80 relative z-10">
                                <div className="flex items-center gap-4 text-xs font-mono text-gray-400">
                                    <span>Preset Active: <strong className="text-blue-400">{heroPresets[heroSelectedPreset].title}</strong></span>
                                </div>

                                <Link href={`/reports/generate?codes=${heroPresets[heroSelectedPreset].codes}`} className="w-full sm:w-auto">
                                    <button className="w-full sm:w-auto px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-mono font-bold text-xs uppercase tracking-wider rounded-xl transition-all duration-200 hover:-translate-y-0.5 shadow-lg shadow-blue-600/30 flex items-center justify-center gap-2">
                                        <span>Launch Workstation with Selected Presets</span>
                                        <span>→</span>
                                    </button>
                                </Link>
                            </div>
                        </div>
                    </motion.div>
                </div>

                {/* SECTION 1: One-Click Popular Comparison Pills */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5 }}
                    className="space-y-4"
                >
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-emerald-400">⚡ Trending Synthesis Comparisons</span>
                        </div>
                        <span className="text-xs text-gray-500 font-mono">1-Click Launch</span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        {trendingComparisons.map((item, idx) => (
                            <Link key={idx} href={`/reports/vs/${item.slug}`}>
                                <div className="transition-transform duration-200 hover:-translate-y-1 transform-gpu">
                                    <MagicCard 
                                        className="p-4 bg-gray-950/80 border-gray-800/80 hover:border-emerald-500/40 rounded-xl space-y-2 group transition-colors"
                                        gradientFrom="#3b82f6"
                                        gradientTo="#10b981"
                                        gradientColor="rgba(16, 185, 129, 0.1)"
                                    >
                                        <div className="flex items-center justify-between text-[10px] font-mono">
                                            <span className="text-gray-400">{item.badge}</span>
                                            <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">{item.tag}</span>
                                        </div>
                                        <h4 className="text-xs font-bold text-white group-hover:text-emerald-400 transition-colors line-clamp-1">
                                            {item.title}
                                        </h4>
                                        <div className="text-[11px] text-gray-500 font-mono flex items-center justify-between pt-1">
                                            <span>Synthesize →</span>
                                            <span className="text-blue-400">Ready</span>
                                        </div>
                                    </MagicCard>
                                </div>
                            </Link>
                        ))}
                    </div>
                </motion.div>

                {/* SECTION 2: Interactive Live Report Preview Widget */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5 }}
                    className="space-y-4"
                >
                    <div className="text-center space-y-2">
                        <span className="text-xs font-mono font-semibold uppercase tracking-wider text-cyan-400">Live Output Interactive Preview</span>
                        <h2 className="text-2xl sm:text-3xl font-extrabold text-white">Experience Synthesis in Action</h2>
                    </div>

                    <div className="bg-gray-950/90 border border-gray-800/80 rounded-2xl overflow-hidden shadow-2xl backdrop-blur-xl">
                        {/* Tab Bar */}
                        <div className="flex items-center gap-2 border-b border-gray-800 p-3 bg-gray-900/60 overflow-x-auto">
                            {previewTabs.map((tab) => (
                                <button
                                    key={tab.id}
                                    onClick={() => setActiveTab(tab.id)}
                                    className={`px-4 py-2 rounded-lg text-xs font-mono font-semibold transition-all duration-150 whitespace-nowrap ${
                                        activeTab === tab.id
                                            ? "bg-blue-600 text-white shadow-md shadow-blue-500/20 border border-blue-400/30"
                                            : "text-gray-400 hover:text-white hover:bg-gray-800/50"
                                    }`}
                                >
                                    {tab.label}
                                </button>
                            ))}
                        </div>

                        {/* Interactive Tab Body */}
                        <div className="p-6 sm:p-8 min-h-[260px] flex flex-col justify-center">
                            <AnimatePresence mode="wait">
                                {activeTab === "verdict" && (
                                    <motion.div
                                        key="verdict"
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0 }}
                                        transition={{ duration: 0.2 }}
                                        className="space-y-4"
                                    >
                                        <div className="flex items-center justify-between border-b border-gray-800 pb-3">
                                            <div>
                                                <h3 className="text-base font-bold text-white">PPFAS Flexi Cap Fund vs HDFC Flexi Cap Fund</h3>
                                                <p className="text-xs text-gray-400">Side-by-Side Factsheet Verdict Analysis</p>
                                            </div>
                                            <span className="text-xs font-mono px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">98.4% Match Score</span>
                                        </div>
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            <div className="p-4 bg-gray-900/60 rounded-xl border border-gray-800/60 space-y-2">
                                                <span className="text-[10px] font-mono text-blue-400">Parag Parikh Flexi Cap</span>
                                                <div className="text-2xl font-bold text-white">+18.4% <span className="text-xs font-normal text-gray-400">3Y CAGR</span></div>
                                                <p className="text-xs text-gray-400">Higher allocation to US Tech leaders (Alphabet, Amazon) providing international currency hedge.</p>
                                            </div>
                                            <div className="p-4 bg-gray-900/60 rounded-xl border border-gray-800/60 space-y-2">
                                                <span className="text-[10px] font-mono text-emerald-400">HDFC Flexi Cap</span>
                                                <div className="text-2xl font-bold text-white">+21.2% <span className="text-xs font-normal text-gray-400">3Y CAGR</span></div>
                                                <p className="text-xs text-gray-400">Strong domestic financial sector overweighting (ICICI, HDFC Bank) capturing Indian credit expansion.</p>
                                            </div>
                                        </div>
                                    </motion.div>
                                )}

                                {activeTab === "metrics" && (
                                    <motion.div
                                        key="metrics"
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0 }}
                                        transition={{ duration: 0.2 }}
                                        className="space-y-4"
                                    >
                                        <h3 className="text-base font-bold text-white">Quantitative Risk & Volatility Matrix</h3>
                                        <div className="overflow-x-auto">
                                            <table className="w-full text-xs text-left">
                                                <thead className="border-b border-gray-800 text-gray-400 uppercase font-mono">
                                                    <tr>
                                                        <th className="py-2">Metric Name</th>
                                                        <th className="py-2">PPFAS Flexi Cap</th>
                                                        <th className="py-2">HDFC Flexi Cap</th>
                                                        <th className="py-2">Winner</th>
                                                    </tr>
                                                </thead>
                                                <tbody className="divide-y divide-gray-900 text-gray-300 font-mono">
                                                    <tr>
                                                        <td className="py-2.5 font-sans font-semibold text-white">Sharpe Ratio (3Y)</td>
                                                        <td className="py-2.5 text-emerald-400">1.42</td>
                                                        <td className="py-2.5 text-blue-400">1.58</td>
                                                        <td className="py-2.5 text-emerald-400 font-bold">HDFC Flexi Cap</td>
                                                    </tr>
                                                    <tr>
                                                        <td className="py-2.5 font-sans font-semibold text-white">Sortino Ratio (Downside)</td>
                                                        <td className="py-2.5 text-emerald-400">2.14</td>
                                                        <td className="py-2.5 text-blue-400">1.95</td>
                                                        <td className="py-2.5 text-emerald-400 font-bold">PPFAS Flexi Cap</td>
                                                    </tr>
                                                    <tr>
                                                        <td className="py-2.5 font-sans font-semibold text-white">Expense Ratio (Direct)</td>
                                                        <td className="py-2.5 text-emerald-400">0.57%</td>
                                                        <td className="py-2.5 text-blue-400">0.78%</td>
                                                        <td className="py-2.5 text-emerald-400 font-bold">PPFAS Flexi Cap</td>
                                                    </tr>
                                                </tbody>
                                            </table>
                                        </div>
                                    </motion.div>
                                )}

                                {activeTab === "visuals" && (
                                    <motion.div
                                        key="visuals"
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0 }}
                                        transition={{ duration: 0.2 }}
                                        className="space-y-4 text-center py-4"
                                    >
                                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-400 text-xs font-mono">
                                            <span>Mermaid SVG Graph Rendered</span>
                                        </div>
                                        <div className="p-6 bg-gray-900/80 rounded-xl border border-gray-800 font-mono text-xs text-cyan-300 space-y-2 max-w-lg mx-auto">
                                            <div>[PPFAS] -- 15.2% --&gt; [US Tech Basket]</div>
                                            <div>[HDFC] -- 32.4% --&gt; [Indian Financials]</div>
                                            <div className="text-gray-500 pt-2 text-[10px]">Overlapping Holdings: HDFC Bank, ICICI Bank, Infosys</div>
                                        </div>
                                    </motion.div>
                                )}

                                {activeTab === "pdf" && (
                                    <motion.div
                                        key="pdf"
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        exit={{ opacity: 0 }}
                                        transition={{ duration: 0.2 }}
                                        className="space-y-4 text-center py-4"
                                    >
                                        <h3 className="text-base font-bold text-white">Playwright Serverless PDF Generator</h3>
                                        <p className="text-xs text-gray-400 max-w-md mx-auto">Generates crisp, multi-page vector PDFs with formatted tables, graphs, and SEBI research disclaimers in 1 click.</p>
                                        <Link href="/reports/generate" className="inline-block px-5 py-2.5 bg-blue-600 text-white rounded-lg text-xs font-bold hover:bg-blue-500 transition-all shadow-lg shadow-blue-600/30">
                                            Try Generating PDF →
                                        </Link>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </div>
                </motion.div>

                {/* SECTION 3: Quantitative Risk Factor Decomposition Grid */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5 }}
                    className="space-y-6"
                >
                    <div className="text-center space-y-2 max-w-2xl mx-auto">
                        <span className="text-xs font-mono font-semibold uppercase tracking-wider text-emerald-400">Quantitative Depth</span>
                        <h2 className="text-2xl sm:text-3xl font-extrabold text-white">Factor Risk & Overlap Decomposition</h2>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <div className="transition-transform duration-200 hover:-translate-y-1 transform-gpu">
                            <MagicCard className="p-6 bg-gray-950/80 border-gray-800/80 rounded-2xl space-y-3">
                                <div className="text-xs font-mono text-emerald-400">Ratio 01</div>
                                <h3 className="text-base font-bold text-white">Sharpe & Sortino</h3>
                                <p className="text-xs text-gray-400 leading-relaxed">
                                    Evaluates excess returns per unit of total risk and downside volatility during market corrections.
                                </p>
                            </MagicCard>
                        </div>

                        <div className="transition-transform duration-200 hover:-translate-y-1 transform-gpu">
                            <MagicCard className="p-6 bg-gray-950/80 border-gray-800/80 rounded-2xl space-y-3">
                                <div className="text-xs font-mono text-cyan-400">Ratio 02</div>
                                <h3 className="text-base font-bold text-white">Alpha & Beta Volatility</h3>
                                <p className="text-xs text-gray-400 leading-relaxed">
                                    Quantifies benchmark outperformance (Alpha) and systematic benchmark sensitivity (Beta).
                                </p>
                            </MagicCard>
                        </div>

                        <div className="transition-transform duration-200 hover:-translate-y-1 transform-gpu">
                            <MagicCard className="p-6 bg-gray-950/80 border-gray-800/80 rounded-2xl space-y-3">
                                <div className="text-xs font-mono text-blue-400">Ratio 03</div>
                                <h3 className="text-base font-bold text-white">Max Drawdown Test</h3>
                                <p className="text-xs text-gray-400 leading-relaxed">
                                    Tracks peak-to-trough decline percentage during historic market selloffs to test crash resilience.
                                </p>
                            </MagicCard>
                        </div>

                        <div className="transition-transform duration-200 hover:-translate-y-1 transform-gpu">
                            <MagicCard className="p-6 bg-gray-950/80 border-gray-800/80 rounded-2xl space-y-3">
                                <div className="text-xs font-mono text-indigo-400">Ratio 04</div>
                                <h3 className="text-base font-bold text-white">Portfolio Overlap %</h3>
                                <p className="text-xs text-gray-400 leading-relaxed">
                                    Identifies identical stock holdings across mutual funds to prevent portfolio over-diversification.
                                </p>
                            </MagicCard>
                        </div>
                    </div>
                </motion.div>

                {/* SECTION 4: AMC Data Provenance & Real-time Sync Ticker */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5 }}
                    className="space-y-6 bg-gray-950/80 border border-gray-800/80 rounded-2xl p-6 sm:p-8 backdrop-blur-xl"
                >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-800 pb-4">
                        <div>
                            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-blue-400">AMC Source Provenance</span>
                            <h3 className="text-xl font-bold text-white mt-1">Live Factsheet Document Ingestion Pipeline</h3>
                        </div>
                        <div className="flex items-center gap-2 text-xs font-mono text-gray-400">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                            <span>12+ Asset Management Companies Synced</span>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                        {amcPipelines.map((amc, idx) => (
                            <div
                                key={idx}
                                className="p-3 bg-gray-900/60 rounded-xl border border-gray-800/60 flex items-center justify-between hover:border-gray-700 transition-colors"
                            >
                                <div>
                                    <div className="text-xs font-bold text-white">{amc.name}</div>
                                    <div className={`text-[10px] font-mono ${amc.color}`}>{amc.status}</div>
                                </div>
                                <span className="text-[10px] font-mono text-gray-500">{amc.time}</span>
                            </div>
                        ))}
                    </div>
                </motion.div>

                {/* SECTION: Transparent Pricing & Tier Limits */}
                <motion.div
                    id="pricing"
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5 }}
                    className="space-y-8 max-w-5xl mx-auto pt-4 scroll-mt-24"
                >
                    <div className="text-center space-y-3">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-mono font-medium">
                            <span>⚡ Unified Subscription</span>
                        </div>
                        <h2 className="text-3xl sm:text-4xl font-extrabold text-white">Simple, Transparent Pricing</h2>
                        <p className="text-sm text-gray-400 max-w-xl mx-auto">
                            Choose the right tier for your research workflows. Access Synthesis AI reports and Research Platform limits in one simple plan.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        {/* Free Card */}
                        <div className="transition-transform duration-200 hover:-translate-y-1 transform-gpu">
                            <MagicCard className="p-6 bg-gray-950/80 border-gray-800 rounded-2xl flex flex-col justify-between space-y-6">
                                <div className="space-y-4">
                                    <div>
                                        <span className="text-xs font-mono font-semibold uppercase tracking-wider text-gray-400">Free Tier</span>
                                        <div className="flex items-baseline gap-1 mt-2">
                                            <span className="text-4xl font-extrabold text-white">₹0</span>
                                            <span className="text-xs text-gray-400">/ forever</span>
                                        </div>
                                        <p className="text-xs text-gray-400 mt-2">Starter research limits for fund research & synthesis reports.</p>
                                    </div>
                                    <div className="space-y-2 border-t border-gray-900 pt-4">
                                        <div className="flex items-center gap-2 text-xs text-gray-200">
                                            <span className="text-emerald-400 font-bold">✓</span>
                                            <span><strong>1 report per day</strong> (Synthesis Studio)</span>
                                        </div>
                                        <div className="flex items-center gap-2 text-xs text-gray-200">
                                            <span className="text-emerald-400 font-bold">✓</span>
                                            <span>Token-based queries in Research platform</span>
                                        </div>
                                        <div className="flex items-center gap-2 text-xs text-gray-400">
                                            <span className="text-emerald-400 font-bold">✓</span>
                                            <span>25k daily / 100k monthly AI tokens</span>
                                        </div>
                                    </div>
                                </div>
                                <Link href="/reports/generate" className="w-full">
                                    <button className="w-full py-2.5 rounded-xl bg-gray-900 border border-gray-800 text-gray-300 font-medium text-xs hover:bg-gray-800 hover:text-white transition-all">
                                        Start Synthesizing (Free)
                                    </button>
                                </Link>
                            </MagicCard>
                        </div>

                        {/* Pro Card */}
                        <div className="transition-transform duration-200 hover:-translate-y-1 transform-gpu">
                            <MagicCard className="p-6 bg-gray-950/90 border-blue-500/50 rounded-2xl flex flex-col justify-between space-y-6 relative shadow-xl shadow-blue-500/10">
                                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full bg-blue-600 text-[10px] font-mono font-bold text-white uppercase tracking-wider shadow-sm">
                                    Most Popular
                                </div>
                                <div className="space-y-4">
                                    <div>
                                        <span className="text-xs font-mono font-semibold uppercase tracking-wider text-blue-400">Pro Tier</span>
                                        <div className="flex items-baseline gap-1 mt-2">
                                            <span className="text-4xl font-extrabold text-white">₹99</span>
                                            <span className="text-xs text-gray-400">/ month</span>
                                        </div>
                                        <p className="text-xs text-gray-400 mt-2">Higher limits for regular mutual-fund and stock research.</p>
                                    </div>
                                    <div className="space-y-2 border-t border-gray-900 pt-4">
                                        <div className="flex items-center gap-2 text-xs text-gray-100">
                                            <span className="text-blue-400 font-bold">✓</span>
                                            <span><strong>5 reports per day</strong> (Synthesis Studio)</span>
                                        </div>
                                        <div className="flex items-center gap-2 text-xs text-gray-100">
                                            <span className="text-blue-400 font-bold">✓</span>
                                            <span><strong>10X Higher usage</strong> in Research platform</span>
                                        </div>
                                        <div className="flex items-center gap-2 text-xs text-gray-300">
                                            <span className="text-blue-400 font-bold">✓</span>
                                            <span>250k daily / 2M monthly AI tokens</span>
                                        </div>
                                        <div className="flex items-center gap-2 text-xs text-gray-300">
                                            <span className="text-blue-400 font-bold">✓</span>
                                            <span>Dashboard, Canvas & Overlap Tool</span>
                                        </div>
                                    </div>
                                </div>
                                <Link href="/billing" className="w-full">
                                    <button className="w-full py-2.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 text-white font-semibold text-xs hover:from-blue-500 hover:to-indigo-500 transition-all shadow-md shadow-blue-500/25">
                                        Upgrade to Pro (₹99)
                                    </button>
                                </Link>
                            </MagicCard>
                        </div>

                        {/* Ultra Card */}
                        <div className="transition-transform duration-200 hover:-translate-y-1 transform-gpu">
                            <MagicCard className="p-6 bg-gray-950/80 border-indigo-500/40 rounded-2xl flex flex-col justify-between space-y-6">
                                <div className="space-y-4">
                                    <div>
                                        <span className="text-xs font-mono font-semibold uppercase tracking-wider text-indigo-400">Ultra Tier</span>
                                        <div className="flex items-baseline gap-1 mt-2">
                                            <span className="text-4xl font-extrabold text-white">₹199</span>
                                            <span className="text-xs text-gray-400">/ month</span>
                                        </div>
                                        <p className="text-xs text-gray-400 mt-2">Highest limits for heavy institutional research workflows.</p>
                                    </div>
                                    <div className="space-y-2 border-t border-gray-900 pt-4">
                                        <div className="flex items-center gap-2 text-xs text-gray-100">
                                            <span className="text-indigo-400 font-bold">✓</span>
                                            <span><strong>15 reports per day</strong> (Synthesis Studio)</span>
                                        </div>
                                        <div className="flex items-center gap-2 text-xs text-gray-100">
                                            <span className="text-indigo-400 font-bold">✓</span>
                                            <span><strong>25X Higher usage than Free</strong> in Research</span>
                                        </div>
                                        <div className="flex items-center gap-2 text-xs text-gray-300">
                                            <span className="text-indigo-400 font-bold">✓</span>
                                            <span>750k daily / 6M monthly AI tokens</span>
                                        </div>
                                        <div className="flex items-center gap-2 text-xs text-gray-300">
                                            <span className="text-indigo-400 font-bold">✓</span>
                                            <span>Priority PDF export & high-priority budget</span>
                                        </div>
                                    </div>
                                </div>
                                <Link href="/billing" className="w-full">
                                    <button className="w-full py-2.5 rounded-xl bg-indigo-600 text-white font-semibold text-xs hover:bg-indigo-500 transition-all">
                                        Upgrade to Ultra (₹199)
                                    </button>
                                </Link>
                            </MagicCard>
                        </div>
                    </div>
                </motion.div>

                {/* SECTION 5: Institutional FAQ Accordion */}
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5 }}
                    className="space-y-6 max-w-3xl mx-auto"
                >
                    <div className="text-center space-y-2">
                        <span className="text-xs font-mono font-semibold uppercase tracking-wider text-cyan-400">Institutional FAQs</span>
                        <h2 className="text-2xl sm:text-3xl font-extrabold text-white">Frequently Asked Questions</h2>
                    </div>

                    <div className="space-y-3">
                        {faqs.map((faq, idx) => (
                            <div 
                                key={idx} 
                                className="bg-gray-950/80 border border-gray-800/80 rounded-xl overflow-hidden backdrop-blur-xl transition-all"
                            >
                                <button
                                    onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                                    className="w-full p-4 text-left flex items-center justify-between text-sm font-bold text-white hover:text-blue-400 transition-colors"
                                >
                                    <span>{faq.q}</span>
                                    <span className="text-gray-500 text-base">{openFaq === idx ? "−" : "+"}</span>
                                </button>
                                <AnimatePresence>
                                    {openFaq === idx && (
                                        <motion.div
                                            initial={{ height: 0, opacity: 0 }}
                                            animate={{ height: "auto", opacity: 1 }}
                                            exit={{ height: 0, opacity: 0 }}
                                            transition={{ duration: 0.2 }}
                                            className="px-4 pb-4 text-xs text-gray-400 leading-relaxed border-t border-gray-900 pt-3"
                                        >
                                            {faq.a}
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>
                        ))}
                    </div>
                </motion.div>
            </div>

            {/* Schema.org Structured Data */}
            <script
                type="application/ld+json"
                dangerouslySetInnerHTML={{
                    __html: JSON.stringify({
                        "@context": "https://schema.org",
                        "@type": "SoftwareApplication",
                        "name": "Synthesis by FundersAI",
                        "operatingSystem": "Web",
                        "applicationCategory": "FinanceApplication",
                        "offers": {
                            "@type": "Offer",
                            "price": "0",
                            "priceCurrency": "INR"
                        },
                        "description": "Synthesis by FundersAI is an autonomous multi-agent platform for generating institutional mutual fund comparison reports, factsheet analysis, risk metrics, and PDF exports.",
                        "image": "https://www.fundersai.co.in/Synthesis_FUNDERSAI.png",
                        "publisher": {
                            "@type": "Organization",
                            "name": "FundersAI",
                            "url": "https://www.fundersai.co.in",
                            "logo": "https://www.fundersai.co.in/Synthesis_FUNDERSAI.png"
                        }
                    })
                }}
            />
        </div>
    );
}
