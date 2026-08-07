"use client";

import { useState } from "react";
import Link from "next/link";
import { ShimmerButton } from "@/components/ui/shimmer-button";
import { MagicCard } from "@/components/ui/magic-card";

export default function PortfolioOverlapToolPage() {
    const [fundA, setFundA] = useState("Parag Parikh Flexi Cap Fund");
    const [fundB, setFundB] = useState("HDFC Flexi Cap Fund");
    const [overlapPercent, setOverlapPercent] = useState<number>(34.2);

    const commonStocks = [
        { name: "HDFC Bank Ltd", weightA: "7.8%", weightB: "9.2%", sector: "Financial Services" },
        { name: "ICICI Bank Ltd", weightA: "6.2%", weightB: "7.5%", sector: "Financial Services" },
        { name: "Infosys Ltd", weightA: "4.5%", weightB: "5.1%", sector: "Technology" },
        { name: "ITC Ltd", weightA: "3.9%", weightB: "4.0%", sector: "Consumer Goods" }
    ];

    return (
        <div className="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-8">
            {/* Breadcrumb & Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-800/80 pb-6">
                <div>
                    <div className="flex items-center gap-2 text-xs font-mono text-gray-400 mb-1">
                        <Link href="/reports" className="hover:text-blue-400">Synthesis</Link>
                        <span>/</span>
                        <span className="text-gray-200">Tools</span>
                        <span>/</span>
                        <span className="text-blue-400">Portfolio Overlap Calculator</span>
                    </div>
                    <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
                        <span>Mutual Fund Portfolio Overlap Calculator</span>
                        <span className="text-xs font-mono font-normal px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                            Interactive Tool
                        </span>
                    </h1>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                {/* Left Column: Scheme Selection Controls */}
                <div className="lg:col-span-5 space-y-6">
                    <div className="bg-gray-950/80 border border-gray-800/80 rounded-2xl p-6 space-y-5 backdrop-blur-xl shadow-2xl">
                        <div className="border-b border-gray-800/60 pb-3">
                            <span className="text-xs font-mono font-semibold uppercase tracking-wider text-blue-400">Select Mutual Funds</span>
                            <p className="text-xs text-gray-400 mt-1">Enter any two fund names to calculate stock holding duplication.</p>
                        </div>

                        <div className="space-y-4">
                            <div className="space-y-1.5">
                                <label className="block text-xs font-mono font-semibold text-gray-400 uppercase">First Scheme</label>
                                <input 
                                    type="text" 
                                    value={fundA} 
                                    onChange={(e) => setFundA(e.target.value)}
                                    className="w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-blue-500 transition-colors font-semibold"
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label className="block text-xs font-mono font-semibold text-gray-400 uppercase">Second Scheme</label>
                                <input 
                                    type="text" 
                                    value={fundB} 
                                    onChange={(e) => setFundB(e.target.value)}
                                    className="w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-cyan-500 transition-colors font-semibold"
                                />
                            </div>
                        </div>

                        <div className="pt-2">
                            <ShimmerButton
                                className="w-full py-3 shadow-xl"
                                shimmerColor="#ffffff"
                                shimmerSize="0.05em"
                                borderRadius="0.75rem"
                                background="#2563eb"
                            >
                                <span className="text-white text-xs font-semibold tracking-wide flex items-center justify-center gap-2">
                                    <span>Recalculate Overlap</span>
                                    <span>⚡</span>
                                </span>
                            </ShimmerButton>
                        </div>
                    </div>

                    {/* Explanatory Advice Card */}
                    <div className="p-5 bg-blue-950/20 border border-blue-500/20 rounded-2xl space-y-2 backdrop-blur-md">
                        <span className="text-xs font-mono text-blue-400 font-semibold uppercase">Investor Advice</span>
                        <h4 className="text-xs font-bold text-white">Why Portfolio Overlap Matters</h4>
                        <p className="text-xs text-gray-400 leading-relaxed">
                            Holding funds with &gt;40% portfolio overlap creates false diversification. You pay double expense ratios for the exact same underlying stock portfolio.
                        </p>
                    </div>
                </div>

                {/* Right Column: Radial SVG Gauge & Common Stock Breakdown Table */}
                <div className="lg:col-span-7 space-y-6">
                    {/* Radial SVG Gauge & Summary Box */}
                    <MagicCard 
                        className="p-6 bg-gray-950/80 border-gray-800/80 rounded-2xl space-y-6"
                        gradientFrom="#3b82f6"
                        gradientTo="#10b981"
                    >
                        <div className="flex flex-col sm:flex-row items-center gap-8 justify-between">
                            {/* Radial SVG Arc Meter */}
                            <div className="relative w-36 h-36 flex items-center justify-center">
                                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                                    <path
                                        className="text-gray-800"
                                        strokeWidth="3.5"
                                        stroke="currentColor"
                                        fill="none"
                                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                                    />
                                    <path
                                        className="text-emerald-400 transition-all duration-1000 ease-out"
                                        strokeDasharray={`${overlapPercent}, 100`}
                                        strokeWidth="3.5"
                                        strokeLinecap="round"
                                        stroke="currentColor"
                                        fill="none"
                                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                                    />
                                </svg>
                                <div className="absolute text-center">
                                    <span className="text-2xl font-extrabold text-white font-mono">{overlapPercent}%</span>
                                    <span className="block text-[9px] font-mono text-emerald-400 uppercase font-semibold">Overlap</span>
                                </div>
                            </div>

                            <div className="space-y-2 flex-1 text-left">
                                <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-[10px] font-mono border border-emerald-500/20">
                                    <span>Moderate Portfolio Duplication</span>
                                </div>
                                <h3 className="text-lg font-bold text-white">{fundA} vs {fundB}</h3>
                                <p className="text-xs text-gray-400 leading-relaxed">
                                    These two funds share 34.2% common stock equity allocation. Both are heavily weighted in top Indian banking giants.
                                </p>

                                <div className="pt-2">
                                    <Link href="/reports/generate">
                                        <ShimmerButton
                                            className="px-5 py-2 shadow-lg"
                                            shimmerColor="#ffffff"
                                            shimmerSize="0.05em"
                                            borderRadius="0.5rem"
                                            background="#2563eb"
                                        >
                                            <span className="text-white text-xs font-semibold tracking-wide">
                                                Synthesize Full AI Comparison →
                                            </span>
                                        </ShimmerButton>
                                    </Link>
                                </div>
                            </div>
                        </div>

                        {/* Common Stock Holdings Table */}
                        <div className="space-y-3 pt-4 border-t border-gray-800/60">
                            <h4 className="text-xs font-mono font-bold text-white uppercase tracking-wider">Shared Portfolio Holdings</h4>
                            <div className="overflow-x-auto">
                                <table className="w-full text-xs text-left">
                                    <thead className="border-b border-gray-800 text-gray-400 uppercase font-mono">
                                        <tr>
                                            <th className="py-2">Stock Holding</th>
                                            <th className="py-2">Sector</th>
                                            <th className="py-2 text-right">Weight (Fund A)</th>
                                            <th className="py-2 text-right">Weight (Fund B)</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-900 text-gray-300 font-mono">
                                        {commonStocks.map((stock, i) => (
                                            <tr key={i}>
                                                <td className="py-2.5 font-sans font-semibold text-white">{stock.name}</td>
                                                <td className="py-2.5 text-gray-400 font-sans">{stock.sector}</td>
                                                <td className="py-2.5 text-right text-blue-400">{stock.weightA}</td>
                                                <td className="py-2.5 text-right text-emerald-400">{stock.weightB}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </MagicCard>
                </div>
            </div>
        </div>
    );
}
