import Link from "next/link";
import { ReactNode } from "react";
import type { Metadata } from "next";
import { AnimatedGridPattern } from "@/components/ui/animated-grid-pattern";
import { FlickeringGrid } from "@/components/ui/flickering-grid";
import { EcosystemHeader } from "@/components/ecosystem/EcosystemHeader";
import { ReportsSubNav } from "@/components/layout/ReportsSubNav";

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
        url: "https://synthesis.fundersai.co.in/synthesis",
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

export default function SynthesisLayout({ children }: { children: ReactNode }) {
    return (
        <div className="relative min-h-screen bg-gray-950 text-gray-100 flex flex-col overflow-hidden selection:bg-blue-500/30 selection:text-blue-200">
            {/* Ambient Subtly Dimmed Flickering Grid Background Pattern */}
            <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden [mask-image:linear-gradient(to_bottom,transparent_0%,white_8%,white_92%,transparent_100%)]">
                <FlickeringGrid
                    squareSize={6}
                    gridGap={10}
                    color="rgb(37, 99, 235)"
                    maxOpacity={0.18}
                    flickerChance={0.15}
                    className="w-full h-full"
                />
            </div>

            {/* Shared ecosystem header, plus product-specific sub-nav for the Synthesis Studio surface */}
            <EcosystemHeader currentApp="synthesis" />
            <ReportsSubNav />

            {/* Main Content */}
            <main className="flex-1 flex flex-col relative">
                {children}
            </main>

            {/* Synthesis Studio Global Footer with FundersAI Redirect Banner */}
            <footer className="border-t border-gray-800/80 bg-gray-950/90 py-6 px-4 sm:px-6 lg:px-8 mt-auto text-xs text-gray-400">
                <div className="max-w-[1800px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        <span className="text-white font-semibold">Synthesis by FundersAI</span>
                        <span className="text-gray-600">|</span>
                        <span>Autonomous Financial Multi-Agent Research Engine</span>
                    </div>
                    <div className="flex items-center gap-4">
                        <Link
                            href="/dashboard"
                            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-bold hover:bg-emerald-500/20 transition-all"
                        >
                            <span>← Back to Research</span>
                        </Link>
                    </div>
                </div>
            </footer>
        </div>
    );
}

