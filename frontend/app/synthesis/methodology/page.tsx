import Link from "next/link";
import { Metadata } from "next";
import { MagicCard } from "@/components/ui/magic-card";
import { ShimmerButton } from "@/components/ui/shimmer-button";
import { ReportsSubNav } from "@/components/layout/ReportsSubNav";

export const metadata: Metadata = {
    // The parent synthesis layout appends "| Synthesis by FundersAI" via title.template.
    title: "AI Research Methodology & Zero-Hallucination Guardrails",
    description: "Learn how Synthesis by FundersAI ingests official AMC disclosures, parses factsheet tables, calculates risk ratios, and enforces zero-hallucination policies.",
    keywords: [
        "FundersAI research methodology",
        "AMC factsheet parser",
        "zero hallucination AI financial reports",
        "Synthesis by FundersAI"
    ],
    alternates: {
        canonical: "https://synthesis.fundersai.co.in/synthesis/methodology",
    },
    openGraph: {
        title: "AI Research Methodology | Synthesis by FundersAI",
        description: "Institutional-grade financial AI methodology, deterministic risk metrics, and zero-hallucination guardrails.",
        url: "https://synthesis.fundersai.co.in/synthesis/methodology",
        siteName: "Synthesis by FundersAI",
    }
};

export default function MethodologyPage() {
    return (
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-12 w-full space-y-10">
            {/* Breadcrumb */}
            <div className="flex items-center gap-2 text-xs font-mono text-gray-400">
                <Link href="/" className="hover:text-blue-400">FundersAI</Link>
                <span>/</span>
                <Link href="/synthesis" className="hover:text-blue-400">Synthesis</Link>
                <span>/</span>
                <span className="text-blue-400 font-bold">[ METHODOLOGY ]</span>
            </div>

            {/* Header */}
            <div className="space-y-4 max-w-3xl">
                <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-mono font-bold uppercase tracking-widest">
                    <span>[ GUARANTEE: ZERO_HALLUCINATION_POLICY ]</span>
                </div>
                <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-tight font-serif-display">
                    Deterministic <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-cyan-400 to-emerald-400">Financial Intelligence</span>
                </h1>
                <p className="text-sm sm:text-base text-gray-400 leading-relaxed font-sans">
                    Synthesis by FundersAI operates on strict quantitative boundaries. Every metric, Sharpe ratio, and portfolio weighting in our reports is verified against official AMC disclosures.
                </p>
            </div>

            {/* In-Page Navigation Options Menu */}
            <ReportsSubNav />

            {/* Methodology Architecture Pillars Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <MagicCard 
                    className="p-6 bg-gray-950/80 border-gray-800/80 hover:border-emerald-500/40 rounded-2xl space-y-3 transition-all"
                    gradientFrom="#3b82f6"
                    gradientTo="#10b981"
                    gradientColor="rgba(16, 185, 129, 0.12)"
                >
                    <div className="text-xs font-mono text-emerald-400">Pillar 1</div>
                    <h3 className="text-lg font-bold text-white">Official AMC Document Ingestion</h3>
                    <p className="text-xs text-gray-400 leading-relaxed">
                        Factsheets, monthly portfolio disclosures, and Scheme Information Documents (SIDs) are parsed directly from official AMC sources (PPFAS, HDFC, SBI, etc.) into Cloudflare R2 and Supabase.
                    </p>
                </MagicCard>

                <MagicCard 
                    className="p-6 bg-gray-950/80 border-gray-800/80 hover:border-blue-500/40 rounded-2xl space-y-3 transition-all"
                    gradientFrom="#2563eb"
                    gradientTo="#059669"
                    gradientColor="rgba(37, 99, 235, 0.12)"
                >
                    <div className="text-xs font-mono text-cyan-400">Pillar 2</div>
                    <h3 className="text-lg font-bold text-white">Multi-Agent Research Workflows</h3>
                    <p className="text-xs text-gray-400 leading-relaxed">
                        Autonomous agents execute separate tasks: Data Acquisition, Risk Indexing (Beta, Alpha, Sharpe), News Sentiment, and Visual Diagram Rendering via Mermaid SVGs.
                    </p>
                </MagicCard>

                <MagicCard 
                    className="p-6 bg-gray-950/80 border-gray-800/80 hover:border-teal-500/40 rounded-2xl space-y-3 transition-all"
                    gradientFrom="#0284c7"
                    gradientTo="#10b981"
                    gradientColor="rgba(16, 185, 129, 0.12)"
                >
                    <div className="text-xs font-mono text-blue-400">Pillar 3</div>
                    <h3 className="text-lg font-bold text-white">Research-Only Guardrails</h3>
                    <p className="text-xs text-gray-400 leading-relaxed">
                        Synthesis is strictly research-focused. No automated buy, sell, or hold recommendations are ever generated. Missing fields and abstentions are disclosed transparently.
                    </p>
                </MagicCard>
            </div>

            {/* CTA */}
            <div className="p-8 bg-gray-950/90 border border-gray-800 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-6 backdrop-blur-xl">
                <div className="space-y-1">
                    <h3 className="text-base font-bold text-white">Ready to Synthesize Your First Report?</h3>
                    <p className="text-xs text-gray-400">Experience autonomous multi-agent quantitative mutual fund research in action.</p>
                </div>
                <Link href="/synthesis/generate">
                    <ShimmerButton
                        className="px-6 py-3 shadow-xl whitespace-nowrap"
                        shimmerColor="#ffffff"
                        shimmerSize="0.05em"
                        borderRadius="0.5rem"
                        background="#2563eb"
                    >
                        <span className="text-white text-xs font-semibold tracking-wide">
                            Open Synthesis Studio →
                        </span>
                    </ShimmerButton>
                </Link>
            </div>
        </div>
    );
}
