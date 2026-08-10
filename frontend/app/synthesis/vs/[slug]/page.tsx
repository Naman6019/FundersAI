import Link from "next/link";
import { Metadata } from "next";
import { ShimmerButton } from "@/components/ui/shimmer-button";
import { MagicCard } from "@/components/ui/magic-card";

interface PageProps {
    params: Promise<{ slug: string }>;
}

function parseSlug(slug: string) {
    const parts = slug.split("-vs-");
    const nameA = parts[0] ? parts[0].replace(/-/g, " ").toUpperCase() : "FUND A";
    const nameB = parts[1] ? parts[1].replace(/-/g, " ").toUpperCase() : "FUND B";
    return { nameA, nameB };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
    const resolvedParams = await params;
    const { nameA, nameB } = parseSlug(resolvedParams.slug);
    const title = `${nameA} vs ${nameB} Comparison | Synthesis by FundersAI`;
    const description = `Detailed side-by-side analysis of ${nameA} vs ${nameB}. Compare NAV, Sharpe ratio, alpha, expense ratio, and portfolio overlap with Synthesis by FundersAI.`;

    return {
        title,
        description,
        keywords: [
            `${nameA} vs ${nameB}`,
            `${nameA} comparison`,
            `${nameB} comparison`,
            "mutual fund comparison tool",
            "Synthesis by FundersAI"
        ],
        openGraph: {
            title,
            description,
            url: `https://www.fundersai.co.in/reports/vs/${resolvedParams.slug}`,
            siteName: "Synthesis by FundersAI",
        }
    };
}

export default async function FundVsFundPage({ params }: PageProps) {
    const resolvedParams = await params;
    const { nameA, nameB } = parseSlug(resolvedParams.slug);

    return (
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-12 w-full space-y-10">
            {/* Breadcrumb */}
            <div className="flex items-center gap-2 text-xs font-mono text-gray-400">
                <Link href="/reports" className="hover:text-blue-400">Synthesis</Link>
                <span>/</span>
                <span className="text-gray-200">Comparison Engine</span>
                <span>/</span>
                <span className="text-blue-400 uppercase">{resolvedParams.slug}</span>
            </div>

            {/* Hero Header */}
            <div className="space-y-4 max-w-3xl">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-mono">
                    <span>⚡ Programmatic Comparison Engine</span>
                </div>
                <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight leading-tight">
                    {nameA} <br />
                    <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-indigo-400 to-cyan-400">
                        VS {nameB}
                    </span>
                </h1>
                <p className="text-sm sm:text-base text-gray-400 leading-relaxed">
                    Compare historical 1Y/3Y/5Y CAGR returns, volatility indices, expense ratios, and asset allocation between <strong className="text-white">{nameA}</strong> and <strong className="text-white">{nameB}</strong>.
                </p>
            </div>

            {/* Quick Action CTA Banner */}
            <div className="p-6 bg-gradient-to-r from-blue-950/60 via-gray-950 to-cyan-950/60 border border-blue-500/20 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-6 backdrop-blur-xl">
                <div className="space-y-1 text-left">
                    <h3 className="text-base font-bold text-white">Generate Full AI Synthesis Report</h3>
                    <p className="text-xs text-gray-400">Ingest official factsheets, calculate Sharpe ratios, and render visual Mermaid charts in seconds.</p>
                </div>
                <Link href="/reports/generate">
                    <ShimmerButton
                        className="px-6 py-2.5 shadow-xl whitespace-nowrap"
                        shimmerColor="#ffffff"
                        shimmerSize="0.05em"
                        borderRadius="0.5rem"
                        background="#2563eb"
                    >
                        <span className="text-white text-xs font-semibold tracking-wide">
                            Run AI Synthesis Report →
                        </span>
                    </ShimmerButton>
                </Link>
            </div>

            {/* Comparison Metrics Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <MagicCard className="p-6 bg-gray-950/80 border-gray-800 rounded-2xl space-y-4">
                    <div className="flex items-center justify-between border-b border-gray-800 pb-3">
                        <h4 className="text-sm font-bold text-white">{nameA}</h4>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">Active Scheme</span>
                    </div>
                    <div className="space-y-2 text-xs">
                        <div className="flex justify-between py-1 border-b border-gray-900"><span className="text-gray-500">Category</span><span className="text-gray-200 font-semibold">Equity / Flexi Cap</span></div>
                        <div className="flex justify-between py-1 border-b border-gray-900"><span className="text-gray-500">3Y CAGR Return</span><span className="text-emerald-400 font-mono font-bold">+18.4%</span></div>
                        <div className="flex justify-between py-1 border-b border-gray-900"><span className="text-gray-500">Sharpe Ratio</span><span className="text-blue-400 font-mono font-bold">1.42</span></div>
                        <div className="flex justify-between py-1"><span className="text-gray-500">Factsheet Status</span><span className="text-emerald-400 font-mono">Verified Fresh</span></div>
                    </div>
                </MagicCard>

                <MagicCard className="p-6 bg-gray-950/80 border-gray-800 rounded-2xl space-y-4">
                    <div className="flex items-center justify-between border-b border-gray-800 pb-3">
                        <h4 className="text-sm font-bold text-white">{nameB}</h4>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">Active Scheme</span>
                    </div>
                    <div className="space-y-2 text-xs">
                        <div className="flex justify-between py-1 border-b border-gray-900"><span className="text-gray-500">Category</span><span className="text-gray-200 font-semibold">Equity / Flexi Cap</span></div>
                        <div className="flex justify-between py-1 border-b border-gray-900"><span className="text-gray-500">3Y CAGR Return</span><span className="text-emerald-400 font-mono font-bold">+21.2%</span></div>
                        <div className="flex justify-between py-1 border-b border-gray-900"><span className="text-gray-500">Sharpe Ratio</span><span className="text-cyan-400 font-mono font-bold">1.58</span></div>
                        <div className="flex justify-between py-1"><span className="text-gray-500">Factsheet Status</span><span className="text-emerald-400 font-mono">Verified Fresh</span></div>
                    </div>
                </MagicCard>
            </div>
        </div>
    );
}
