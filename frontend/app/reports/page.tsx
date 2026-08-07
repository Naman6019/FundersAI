"use client";

import { useState } from "react";
import Link from "next/link";
import { AnimatedGridPattern } from "@/components/ui/animated-grid-pattern";
import { MagicCard } from "@/components/ui/magic-card";
import { ShimmerButton } from "@/components/ui/shimmer-button";
import { NumberTicker } from "@/components/ui/number-ticker";

// Data Definitions
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

    return (
        <div className="relative flex-1 flex flex-col items-center justify-center px-4 sm:px-6 lg:px-8 py-16 overflow-hidden">
            {/* Background Animated Grid Pattern */}
            <AnimatedGridPattern
                numSquares={30}
                maxOpacity={0.15}
                duration={3}
                repeatDelay={1}
                className="[mask-image:radial-gradient(600px_circle_at_center,white,transparent)] inset-x-0 inset-y-[-30%] h-[200%] w-full text-blue-500/20 stroke-blue-500/20"
            />

            <div className="max-w-[1800px] w-full space-y-20 relative z-10 px-4 sm:px-6 lg:px-8">
                {/* Hero Header */}
                <div className="text-center space-y-6 max-w-3xl mx-auto">
                    <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-mono font-medium shadow-sm">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
                        <span>Synthesis Engine Active v2.4</span>
                    </div>

                    <h1 className="text-4xl sm:text-6xl font-extrabold text-white tracking-tight leading-[1.1]">
                        Institutional-Grade Synthesis. <br />
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-teal-400 to-emerald-400">
                            Generated in Seconds.
                        </span>
                    </h1>
                    
                    <p className="text-base sm:text-lg text-gray-400 max-w-2xl mx-auto leading-relaxed">
                        <strong className="text-gray-200">Synthesis by FundersAI</strong> leverages autonomous multi-agent graphs to ingest, parse, and synthesize hundreds of official AMC factsheets and market disclosures into clear comparison reports.
                    </p>

                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-2">
                        <Link href="/reports/generate">
                            <ShimmerButton
                                className="px-8 py-3.5 shadow-2xl"
                                shimmerColor="#ffffff"
                                shimmerSize="0.06em"
                                borderRadius="9999px"
                                background="#2563eb"
                            >
                                <span className="text-white font-semibold text-sm tracking-wide flex items-center gap-2">
                                    <span>Start Synthesizing</span>
                                    <span>→</span>
                                </span>
                            </ShimmerButton>
                        </Link>
                        <Link
                            href="/billing"
                            className="px-6 py-3 bg-gradient-to-r from-blue-600 via-indigo-600 to-emerald-500 text-white font-semibold text-sm rounded-full hover:brightness-110 transition-all backdrop-blur-md shadow-lg shadow-blue-500/20 flex items-center gap-1.5"
                        >
                            <span>⚡ Upgrade Plan</span>
                        </Link>
                        <Link
                            href="/reports/dashboard"
                            className="px-6 py-3 bg-gray-900/80 border border-gray-800 text-gray-300 font-medium text-sm rounded-full hover:bg-gray-800 hover:text-white transition-all backdrop-blur-md"
                        >
                            View Saved Reports
                        </Link>
                    </div>
                </div>

                {/* SECTION 1: One-Click Popular Comparison Pills */}
                <div className="space-y-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-emerald-400">⚡ Trending Synthesis Comparisons</span>
                        </div>
                        <span className="text-xs text-gray-500 font-mono">1-Click Launch</span>
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                        {trendingComparisons.map((item, idx) => (
                            <Link key={idx} href={`/reports/vs/${item.slug}`}>
                                <MagicCard 
                                    className="p-4 bg-gray-950/80 border-gray-800/80 hover:border-emerald-500/40 rounded-xl space-y-2 group transition-all"
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
                            </Link>
                        ))}
                    </div>
                </div>

                {/* SECTION 2: Interactive Live Report Preview Widget */}
                <div className="space-y-4">
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
                                    className={`px-4 py-2 rounded-lg text-xs font-mono font-semibold transition-all whitespace-nowrap ${
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
                            {activeTab === "verdict" && (
                                <div className="space-y-4 animate-in fade-in duration-300">
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
                                </div>
                            )}

                            {activeTab === "metrics" && (
                                <div className="space-y-4 animate-in fade-in duration-300">
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
                                </div>
                            )}

                            {activeTab === "visuals" && (
                                <div className="space-y-4 animate-in fade-in duration-300 text-center py-4">
                                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-400 text-xs font-mono">
                                        <span>Mermaid SVG Graph Rendered</span>
                                    </div>
                                    <div className="p-6 bg-gray-900/80 rounded-xl border border-gray-800 font-mono text-xs text-cyan-300 space-y-2 max-w-lg mx-auto">
                                        <div>[PPFAS] -- 15.2% --&gt; [US Tech Basket]</div>
                                        <div>[HDFC] -- 32.4% --&gt; [Indian Financials]</div>
                                        <div className="text-gray-500 pt-2 text-[10px]">Overlapping Holdings: HDFC Bank, ICICI Bank, Infosys</div>
                                    </div>
                                </div>
                            )}

                            {activeTab === "pdf" && (
                                <div className="space-y-4 animate-in fade-in duration-300 text-center py-4">
                                    <h3 className="text-base font-bold text-white">Playwright Serverless PDF Generator</h3>
                                    <p className="text-xs text-gray-400 max-w-md mx-auto">Generates crisp, multi-page vector PDFs with formatted tables, graphs, and SEBI research disclaimers in 1 click.</p>
                                    <Link href="/reports/generate" className="inline-block px-5 py-2.5 bg-blue-600 text-white rounded-lg text-xs font-bold hover:bg-blue-500 transition-all">
                                        Try Generating PDF →
                                    </Link>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* SECTION 3: Quantitative Risk Factor Decomposition Grid */}
                <div className="space-y-6">
                    <div className="text-center space-y-2 max-w-2xl mx-auto">
                        <span className="text-xs font-mono font-semibold uppercase tracking-wider text-emerald-400">Quantitative Depth</span>
                        <h2 className="text-2xl sm:text-3xl font-extrabold text-white">Factor Risk & Overlap Decomposition</h2>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        <MagicCard className="p-6 bg-gray-950/80 border-gray-800/80 rounded-2xl space-y-3">
                            <div className="text-xs font-mono text-emerald-400">Ratio 01</div>
                            <h3 className="text-base font-bold text-white">Sharpe & Sortino</h3>
                            <p className="text-xs text-gray-400 leading-relaxed">
                                Evaluates excess returns per unit of total risk and downside volatility during market corrections.
                            </p>
                        </MagicCard>

                        <MagicCard className="p-6 bg-gray-950/80 border-gray-800/80 rounded-2xl space-y-3">
                            <div className="text-xs font-mono text-cyan-400">Ratio 02</div>
                            <h3 className="text-base font-bold text-white">Alpha & Beta Volatility</h3>
                            <p className="text-xs text-gray-400 leading-relaxed">
                                Quantifies benchmark outperformance (Alpha) and systematic benchmark sensitivity (Beta).
                            </p>
                        </MagicCard>

                        <MagicCard className="p-6 bg-gray-950/80 border-gray-800/80 rounded-2xl space-y-3">
                            <div className="text-xs font-mono text-blue-400">Ratio 03</div>
                            <h3 className="text-base font-bold text-white">Max Drawdown Test</h3>
                            <p className="text-xs text-gray-400 leading-relaxed">
                                Tracks peak-to-trough decline percentage during historic market selloffs to test crash resilience.
                            </p>
                        </MagicCard>

                        <MagicCard className="p-6 bg-gray-950/80 border-gray-800/80 rounded-2xl space-y-3">
                            <div className="text-xs font-mono text-indigo-400">Ratio 04</div>
                            <h3 className="text-base font-bold text-white">Portfolio Overlap %</h3>
                            <p className="text-xs text-gray-400 leading-relaxed">
                                Identifies identical stock holdings across mutual funds to prevent portfolio over-diversification.
                            </p>
                        </MagicCard>
                    </div>
                </div>

                {/* SECTION 4: AMC Data Provenance & Real-time Sync Ticker */}
                <div className="space-y-6 bg-gray-950/80 border border-gray-800/80 rounded-2xl p-6 sm:p-8 backdrop-blur-xl">
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
                            <div key={idx} className="p-3 bg-gray-900/60 rounded-xl border border-gray-800/60 flex items-center justify-between">
                                <div>
                                    <div className="text-xs font-bold text-white">{amc.name}</div>
                                    <div className={`text-[10px] font-mono ${amc.color}`}>{amc.status}</div>
                                </div>
                                <span className="text-[10px] font-mono text-gray-500">{amc.time}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* SECTION: Transparent Pricing & Tier Limits */}
                <div id="pricing" className="space-y-8 max-w-5xl mx-auto pt-4 scroll-mt-24">
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

                        {/* Pro Card */}
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

                        {/* Ultra Card */}
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

                {/* SECTION 5: Institutional FAQ Accordion */}
                <div className="space-y-6 max-w-3xl mx-auto">
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
                                {openFaq === idx && (
                                    <div className="px-4 pb-4 text-xs text-gray-400 leading-relaxed border-t border-gray-900 pt-3">
                                        {faq.a}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* Schema.org Structured Data for Google / Bing / AI Search Engines */}
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
