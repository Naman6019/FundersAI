import Link from "next/link";
import Image from "next/image";
import { ReactNode } from "react";
import type { Metadata } from "next";

export const metadata: Metadata = {
    title: {
        default: "Synthesis by FundersAI | AI Mutual Fund & Stock Research Studio",
        template: "%s | Synthesis by FundersAI",
    },
    description: "Synthesis by FundersAI leverages multi-agent graph intelligence to synthesize institutional mutual fund comparison reports, risk metrics, portfolio overlap, and PDF downloads in seconds.",
    keywords: [
        "Synthesis by FundersAI",
        "FundersAI Synthesis",
        "AI mutual fund synthesis",
        "mutual fund comparison tool",
        "AI mutual fund research",
        "Parag Parikh vs HDFC Flexi Cap",
        "mutual fund factsheet parser",
        "quant fund analysis India",
        "NSE mutual fund comparison",
        "portfolio overlap calculator",
        "SIP returns comparison AI"
    ],
    icons: {
        icon: "/Synthesis_FUNDERSAI.png",
        shortcut: "/Synthesis_FUNDERSAI.png",
        apple: "/Synthesis_FUNDERSAI.png",
    },
    openGraph: {
        title: "Synthesis by FundersAI | AI Mutual Fund & Stock Research Studio",
        description: "Instant institutional-grade mutual fund comparison reports with risk metrics, portfolio overlap, and PDF export.",
        url: "https://www.fundersai.co.in/reports",
        siteName: "Synthesis by FundersAI",
        locale: "en_IN",
        type: "website",
        images: [
            {
                url: "/Synthesis_FUNDERSAI.png",
                width: 1200,
                height: 630,
                alt: "Synthesis by FundersAI",
            },
        ],
    },
    twitter: {
        card: "summary_large_image",
        title: "Synthesis by FundersAI | AI Mutual Fund & Stock Research Studio",
        description: "Instant institutional-grade mutual fund comparison reports with risk metrics, portfolio overlap, and PDF export.",
        images: ["/Synthesis_FUNDERSAI.png"],
    },
    robots: {
        index: true,
        follow: true,
    },
};

export default function ReportsLayout({ children }: { children: ReactNode }) {
    return (
        <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col selection:bg-blue-500/30 selection:text-blue-200">
            {/* Top Navigation for Reports Product */}
            <header className="border-b border-gray-800/60 bg-gray-950/80 backdrop-blur-xl sticky top-0 z-50 transition-colors">
                <div className="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
                    <div className="flex items-center gap-8">
                        <Link href="/reports" className="flex items-center gap-3 group">
                            <div className="flex items-center group-hover:scale-105 transition-transform">
                                <Image 
                                    src="/Synthesis_FUNDERSAI.png" 
                                    alt="Synthesis by FundersAI" 
                                    width={240} 
                                    height={60} 
                                    className="h-10 w-auto object-contain rounded-md border border-gray-800 shadow-md" 
                                    priority
                                />
                            </div>
                            <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">⚡ Synthesis v2</span>
                        </Link>
                        
                        <nav className="hidden md:flex items-center gap-1">
                            <Link 
                                href="/reports/dashboard" 
                                className="text-xs font-semibold px-3 py-1.5 rounded-md text-gray-400 hover:text-white hover:bg-gray-800/50 transition-all"
                            >
                                Dashboard
                            </Link>
                            <Link 
                                href="/reports/generate" 
                                className="text-xs font-semibold px-3 py-1.5 rounded-md text-gray-400 hover:text-white hover:bg-gray-800/50 transition-all"
                            >
                                New Report
                            </Link>
                            <Link 
                                href="/reports/tools/portfolio-overlap" 
                                className="text-xs font-semibold px-3 py-1.5 rounded-md text-gray-400 hover:text-white hover:bg-gray-800/50 transition-all"
                            >
                                Overlap Tool
                            </Link>
                            <Link 
                                href="/reports/supported-funds" 
                                className="text-xs font-semibold px-3 py-1.5 rounded-md text-gray-400 hover:text-white hover:bg-gray-800/50 transition-all"
                            >
                                Supported Funds
                            </Link>
                            <Link 
                                href="/reports/methodology" 
                                className="text-xs font-semibold px-3 py-1.5 rounded-md text-gray-400 hover:text-white hover:bg-gray-800/50 transition-all"
                            >
                                Methodology
                            </Link>
                            <Link
                                href="#pricing"
                                className="text-xs font-semibold px-3 py-1.5 rounded-md text-blue-400 hover:text-blue-300 hover:bg-blue-950/30 transition-all"
                            >
                                Pricing
                            </Link>
                        </nav>
                    </div>

                    <div className="flex items-center gap-3">
                        <Link
                            href="/billing"
                            className="text-xs font-semibold text-white bg-gradient-to-r from-blue-600 via-indigo-600 to-emerald-500 hover:from-blue-500 hover:to-emerald-400 px-3.5 py-1.5 rounded-lg border border-blue-400/30 shadow-lg shadow-blue-500/20 transition-all flex items-center gap-1.5 group"
                        >
                            <span className="text-amber-300 group-hover:scale-110 transition-transform">⚡</span>
                            <span>Upgrade</span>
                        </Link>
                        <Link
                            href="/"
                            className="text-xs font-bold text-emerald-400 hover:text-emerald-300 bg-emerald-950/40 hover:bg-emerald-900/60 px-3.5 py-1.5 rounded-lg border border-emerald-500/40 backdrop-blur-md transition-all flex items-center gap-1.5 shadow-sm hover:border-emerald-400"
                        >
                            <span>🌐 FundersAI Platform</span>
                            <span className="text-emerald-400 font-bold">→</span>
                        </Link>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 flex flex-col relative">
                {children}
            </main>

            {/* Reports Global Footer with FundersAI Redirect Banner */}
            <footer className="border-t border-gray-800/80 bg-gray-950/90 py-6 px-4 sm:px-6 lg:px-8 mt-auto text-xs text-gray-400">
                <div className="max-w-[1800px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <span className="text-white font-semibold">Synthesis by FundersAI</span>
                        <span className="text-gray-600">|</span>
                        <span>Autonomous Financial Multi-Agent Research Engine</span>
                    </div>
                    <div className="flex items-center gap-4">
                        <Link
                            href="/"
                            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-bold hover:bg-emerald-500/20 transition-all"
                        >
                            <span>🌐 Return to FundersAI Main Platform</span>
                            <span>→</span>
                        </Link>
                    </div>
                </div>
            </footer>
        </div>
    );
}

