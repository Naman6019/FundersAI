import Link from "next/link";
import { Metadata } from "next";
import { ShimmerButton } from "@/components/ui/shimmer-button";
import { MagicCard } from "@/components/ui/magic-card";

interface PageProps {
    params: Promise<{ slug: string }>;
}

function parseCategorySlug(slug: string) {
    const formatted = slug.replace(/-/g, " ").toUpperCase();
    return { name: formatted };
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
    const resolvedParams = await params;
    const { name } = parseCategorySlug(resolvedParams.slug);
    const title = `${name} Mutual Funds Analysis & Rankings | Synthesis by FundersAI`;
    const description = `AI-powered analysis and benchmark comparison for top ${name} mutual funds in India. Synthesize factsheet disclosures, risk metrics, and CAGR returns.`;

    return {
        title,
        description,
        keywords: [
            `${name} mutual funds`,
            `best ${name} mutual funds 2026`,
            `${name} FundersAI comparison`,
            "Synthesis by FundersAI"
        ],
        openGraph: {
            title,
            description,
            url: `https://synthesis.fundersai.co.in/synthesis/category/${resolvedParams.slug}`,
            siteName: "Synthesis by FundersAI",
        }
    };
}

export default async function CategoryPage({ params }: PageProps) {
    const resolvedParams = await params;
    const { name } = parseCategorySlug(resolvedParams.slug);

    return (
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-12 w-full space-y-10">
            {/* Breadcrumb */}
            <div className="flex items-center gap-2 text-xs font-mono text-gray-400">
                <Link href="/synthesis" className="hover:text-blue-400">Synthesis</Link>
                <span>/</span>
                <span className="text-gray-200">Category Hub</span>
                <span>/</span>
                <span className="text-blue-400">{name}</span>
            </div>

            {/* Header */}
            <div className="space-y-4 max-w-3xl">
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-xs font-mono">
                    <span>📊 Category Intelligence Hub</span>
                </div>
                <h1 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
                    {name} <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400">Mutual Funds</span>
                </h1>
                <p className="text-sm sm:text-base text-gray-400 leading-relaxed">
                    Explore quantitative rankings, category benchmark return averages, and portfolio overlap analysis across top-performing <strong className="text-white">{name}</strong> schemes.
                </p>
            </div>

            {/* Quick Action Banner */}
            <div className="p-6 bg-gray-950/90 border border-gray-800 rounded-2xl flex flex-col sm:flex-row items-center justify-between gap-6 backdrop-blur-xl">
                <div className="space-y-1">
                    <h3 className="text-base font-bold text-white">Compare {name} Funds with AI</h3>
                    <p className="text-xs text-gray-400">Select any two funds in this category to generate an instant synthesis report.</p>
                </div>
                <Link href="/synthesis/generate">
                    <ShimmerButton
                        className="px-6 py-2.5 shadow-xl whitespace-nowrap"
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

            {/* Top Schemes Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <MagicCard className="p-6 bg-gray-950/80 border-gray-800 rounded-2xl space-y-3">
                    <div className="text-xs font-mono text-blue-400">#1 Top Ranked</div>
                    <h4 className="text-base font-bold text-white">Parag Parikh Flexi Cap Fund</h4>
                    <div className="text-xs text-gray-400 space-y-1">
                        <div>3Y Return: <span className="text-emerald-400 font-mono font-bold">+18.4%</span></div>
                        <div>AUM: <span className="text-gray-200 font-mono">₹93,775 Cr</span></div>
                    </div>
                </MagicCard>

                <MagicCard className="p-6 bg-gray-950/80 border-gray-800 rounded-2xl space-y-3">
                    <div className="text-xs font-mono text-cyan-400">#2 Top Ranked</div>
                    <h4 className="text-base font-bold text-white">HDFC Flexi Cap Fund</h4>
                    <div className="text-xs text-gray-400 space-y-1">
                        <div>3Y Return: <span className="text-emerald-400 font-mono font-bold">+21.2%</span></div>
                        <div>AUM: <span className="text-gray-200 font-mono">₹68,910 Cr</span></div>
                    </div>
                </MagicCard>

                <MagicCard className="p-6 bg-gray-950/80 border-gray-800 rounded-2xl space-y-3">
                    <div className="text-xs font-mono text-indigo-400">#3 Top Ranked</div>
                    <h4 className="text-base font-bold text-white">SBI Flexi Cap Fund</h4>
                    <div className="text-xs text-gray-400 space-y-1">
                        <div>3Y Return: <span className="text-emerald-400 font-mono font-bold">+16.9%</span></div>
                        <div>AUM: <span className="text-gray-200 font-mono">₹21,450 Cr</span></div>
                    </div>
                </MagicCard>
            </div>
        </div>
    );
}
