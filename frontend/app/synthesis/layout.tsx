import { ReactNode } from "react";
import type { Metadata } from "next";
import { AnimatedGridPattern } from "@/components/ui/animated-grid-pattern";
import { FlickeringGrid } from "@/components/ui/flickering-grid";
import { EcosystemHeader } from "@/components/ecosystem/EcosystemHeader";
import { ReportsSubNav } from "@/components/layout/ReportsSubNav";
import SynthesisFooter from "@/components/synthesis/SynthesisFooter";

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
        <div className="relative min-h-screen bg-background text-text-1 flex flex-col overflow-hidden selection:bg-violet-500/30 selection:text-violet-200">
            {/* Ambient Subtly Dimmed Flickering Grid Background Pattern */}
            <div className="absolute inset-0 pointer-events-none z-0 overflow-hidden [mask-image:linear-gradient(to_bottom,transparent_0%,white_8%,white_92%,transparent_100%)]">
                <FlickeringGrid
                    squareSize={6}
                    gridGap={10}
                    color="rgb(139, 92, 246)"
                    maxOpacity={0.18}
                    flickerChance={0.15}
                    className="w-full h-full"
                />
            </div>

            {/* Shared ecosystem header */}
            <EcosystemHeader currentApp="synthesis" />

            {/* Main Content */}
            <main className="flex-1 flex flex-col relative">
                {children}
            </main>

            {/* Second exit from the silo, below the fold */}
            <SynthesisFooter />
        </div>
    );
}

