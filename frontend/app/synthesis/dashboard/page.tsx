"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { supabaseBrowser } from "@/lib/supabaseBrowser";
import { MagicCard } from "@/components/ui/magic-card";
import { ShimmerButton } from "@/components/ui/shimmer-button";
import { ReportsSubNav } from "@/components/layout/ReportsSubNav";
import Breadcrumbs from '@/components/navigation/Breadcrumbs';

/** Only the columns this dashboard actually reads; both tables select *. */
interface SavedReport {
    id: string;
    report_title: string | null;
    funds_compared: string[] | null;
    created_at: string;
}

interface WatchlistItem {
    id: string;
    asset_id: string;
    asset_type: string;
}

export default function ReportsDashboard() {
    const [savedReports, setSavedReports] = useState<SavedReport[]>([]);
    const [watchlists, setWatchlists] = useState<WatchlistItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState("");

    useEffect(() => {
        async function fetchDashboardData() {
            const { data: { user } } = await supabaseBrowser.auth.getUser();
            if (!user) {
                setIsLoading(false);
                return;
            }
            const { data: reports } = await supabaseBrowser.from('saved_reports').select('*').eq('user_id', user.id).order('created_at', { ascending: false });
            const { data: wl } = await supabaseBrowser.from('watchlists').select('*').eq('user_id', user.id).order('created_at', { ascending: false });
            setSavedReports((reports as SavedReport[] | null) ?? []);
            setWatchlists((wl as WatchlistItem[] | null) ?? []);
            setIsLoading(false);
        }
        fetchDashboardData();
    }, []);

    const filteredReports = savedReports.filter(r => 
        r.report_title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (r.funds_compared && r.funds_compared.some((f: string) => f.includes(searchQuery)))
    );

    return (
        <div className="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-8">
            {/* Header & Action Bar */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-line pb-6">
                <div>
                    <Breadcrumbs
                        tone="synthesis"
                        className="mb-1"
                        currentClassName="text-text-1"
                        items={[
                            { label: 'Synthesis', href: '/synthesis' },
                            { label: 'Dashboard' },
                        ]}
                    />
                    <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
                        <span>Saved Reports Dashboard</span>
                        <span className="text-xs font-mono font-normal px-2.5 py-0.5 rounded-full bg-violet-500/10 text-violet-400 border border-violet-500/20">
                            {savedReports.length} Saved
                        </span>
                    </h1>
                </div>

                <Link href="/synthesis/generate">
                    <ShimmerButton
                        className="px-6 py-2.5 shadow-xl"
                        shimmerColor="#ffffff"
                        shimmerSize="0.05em"
                        borderRadius="0.5rem"
                        background="#7c3aed"
                    >
                        <span className="text-white text-xs font-semibold tracking-wide flex items-center gap-1.5">
                            <span>+ Synthesize New Report</span>
                        </span>
                    </ShimmerButton>
                </Link>
            </div>

            {/* In-Page Navigation Options Menu */}
            <ReportsSubNav />
            
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                {/* Main Content Column: Saved Reports Grid */}
                <div className="lg:col-span-8 xl:col-span-9 space-y-6">
                    {/* Search & Filter Control */}
                    <div className="flex items-center justify-between gap-4">
                        <div className="relative flex-1">
                            <input 
                                type="text"
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                placeholder="Search saved reports by title or scheme code..."
                                className="w-full bg-background/80 border border-line rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-violet-500 transition-colors backdrop-blur-md"
                            />
                        </div>
                    </div>

                    <div className="space-y-4">
                        {isLoading ? (
                            <div className="p-12 flex justify-center bg-background/80 border border-line rounded-2xl">
                                <div className="animate-pulse flex items-center gap-2 text-xs font-mono text-text-2">
                                    <span className="w-2 h-2 rounded-full bg-violet-400 animate-ping" />
                                    <span>Fetching saved reports...</span>
                                </div>
                            </div>
                        ) : filteredReports.length === 0 ? (
                            <div className="p-12 text-center text-text-3 bg-background/80 border border-line rounded-2xl backdrop-blur-xl">
                                <p className="text-sm font-semibold text-text-2">No saved reports found.</p>
                                <p className="text-xs text-text-3 mt-1">Generate a side-by-side comparison in Synthesis Studio to save your first report.</p>
                                <Link 
                                    href="/synthesis/generate" 
                                    className="mt-5 inline-block px-5 py-2.5 bg-violet-600 text-white rounded-lg text-xs font-bold hover:bg-violet-500 transition-all shadow-lg shadow-violet-600/20"
                                >
                                    Open Synthesis Studio →
                                </Link>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {filteredReports.map(report => (
                                    <MagicCard 
                                        key={report.id}
                                        className="p-5 bg-background/80 border-line hover:border-emerald-500/40 rounded-2xl space-y-4 transition-all"
                                        gradientFrom="#8b5cf6"
                                        gradientTo="#10b981"
                                        gradientColor="rgba(16, 185, 129, 0.1)"
                                    >
                                        <div className="flex items-center justify-between border-b border-line/60 pb-3">
                                            <div className="flex items-center gap-2">
                                                <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                                    Saved Report
                                                </span>
                                                <span className="text-[10px] text-text-3 font-mono">
                                                    {new Date(report.created_at).toLocaleDateString()}
                                                </span>
                                            </div>
                                        </div>

                                        <h3 className="text-white text-sm font-bold leading-snug line-clamp-2">
                                            {report.report_title}
                                        </h3>

                                        <div className="flex items-center gap-1.5 flex-wrap">
                                            <span className="text-[10px] text-text-3 font-mono">Schemes:</span>
                                            {report.funds_compared?.map((code: string) => (
                                                <span key={code} className="text-[10px] font-mono px-2 py-0.5 rounded bg-gray-900 text-violet-400 border border-line">
                                                    #{code}
                                                </span>
                                            ))}
                                        </div>

                                        <div className="pt-3 border-t border-line/60 flex items-center justify-between">
                                            <Link 
                                                href={`/synthesis/generate?report_id=${report.id}`}
                                                className="text-xs font-semibold text-violet-400 hover:text-violet-300 flex items-center gap-1"
                                            >
                                                <span>View Report</span>
                                                <span>→</span>
                                            </Link>
                                            <span className="text-[10px] font-mono text-emerald-400">PDF Ready</span>
                                        </div>
                                    </MagicCard>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Sidebar Column: Watchlist & Quick Tools */}
                <div className="lg:col-span-4 xl:col-span-3 space-y-6">
                    <div className="bg-background/80 border border-line rounded-2xl p-5 space-y-4 backdrop-blur-xl">
                        <div className="flex items-center justify-between border-b border-line/60 pb-3">
                            <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-text-2">Tracked Schemes</h2>
                            <span className="text-[10px] font-mono text-emerald-400">Watchlist</span>
                        </div>

                        {isLoading ? (
                            <div className="p-4 text-center text-xs font-mono text-text-3">Loading watchlist...</div>
                        ) : watchlists.length === 0 ? (
                            <div className="p-4 text-center text-xs text-text-3">
                                No assets in watchlist yet.
                            </div>
                        ) : (
                            <ul className="space-y-2">
                                {watchlists.map(item => (
                                    <li key={item.id} className="p-2.5 bg-gray-900/60 rounded-xl border border-line/60 flex items-center justify-between text-xs">
                                        <div className="flex items-center gap-2">
                                            <span className="text-[10px] uppercase font-bold text-violet-400 font-mono bg-violet-500/10 px-1.5 py-0.5 rounded border border-violet-500/20">
                                                {item.asset_type === 'stock' ? 'STK' : 'MF'}
                                            </span>
                                            <span className="text-white font-semibold">{item.asset_id}</span>
                                        </div>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>

                    {/* Quick Tools Access Card */}
                    <div className="bg-gradient-to-br from-violet-950/60 via-gray-950 to-emerald-950/60 border border-violet-500/20 rounded-2xl p-5 space-y-3 backdrop-blur-xl">
                        <span className="text-xs font-mono text-violet-400 uppercase font-semibold">Micro-Tool</span>
                        <h4 className="text-sm font-bold text-white">Portfolio Overlap Calculator</h4>
                        <p className="text-xs text-text-2 leading-relaxed">Check common holdings and overlap percentage between mutual funds.</p>
                        <Link 
                            href="/synthesis/tools/portfolio-overlap"
                            className="inline-block text-xs font-semibold text-emerald-400 hover:text-emerald-300 pt-1"
                        >
                            Open Calculator →
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
}
