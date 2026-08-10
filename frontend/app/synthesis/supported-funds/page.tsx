"use client";

import { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import { MagicCard } from "@/components/ui/magic-card";
import { ShimmerButton } from "@/components/ui/shimmer-button";

interface FundRow {
    scheme_code: string | number;
    scheme_name: string;
    category?: string;
    return_3y?: number | string | null;
    nav?: number | string | null;
    expense_ratio?: number | string | null;
}

interface AMCGroup {
    amc_name: string;
    schemes: FundRow[];
}

export default function SupportedFundsDirectoryPage() {
    const [amcGroups, setAmcGroups] = useState<AMCGroup[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedAmc, setSelectedAmc] = useState<string>("ALL");
    const [searchTerm, setSearchTerm] = useState("");
    const [selectedCategory, setSelectedCategory] = useState("ALL");
    const [selectedFunds, setSelectedFunds] = useState<FundRow[]>([]);

    const toggleFundSelection = (fund: FundRow) => {
        const isAlreadySelected = selectedFunds.some(f => String(f.scheme_code) === String(fund.scheme_code));
        if (isAlreadySelected) {
            setSelectedFunds(prev => prev.filter(f => String(f.scheme_code) !== String(fund.scheme_code)));
        } else {
            if (selectedFunds.length >= 3) {
                alert("You can select up to 3 funds for side-by-side comparison.");
                return;
            }
            setSelectedFunds(prev => [...prev, fund]);
        }
    };

    useEffect(() => {
        async function fetchSupportedFunds() {
            try {
                const res = await fetch("/api/reports/supported-funds");
                if (res.ok) {
                    const json = await res.json();
                    if (json.amcGroups && json.amcGroups.length > 0) {
                        setAmcGroups(json.amcGroups);
                    }
                }
            } catch (err) {
                console.error("Failed to fetch supported funds:", err);
            } finally {
                setIsLoading(false);
            }
        }
        fetchSupportedFunds();
    }, []);

    const categories = ["ALL", "Flexi Cap", "Small Cap", "Large Cap", "Mid Cap", "ELSS Tax Saver", "Hybrid", "Multi Cap"];

    // Total counts across all AMCs
    const totalFundsCount = useMemo(() => {
        return amcGroups.reduce((acc, g) => acc + g.schemes.length, 0);
    }, [amcGroups]);

    // Filter funds on the left side based on selected AMC in right sidebar, search query, and category
    const filteredAMCGroups = useMemo(() => {
        return amcGroups.map(group => {
            // Check if this AMC matches selected AMC filter
            if (selectedAmc !== "ALL" && group.amc_name !== selectedAmc) {
                return { ...group, schemes: [] };
            }

            const matchingSchemes = group.schemes.filter(fund => {
                const matchesSearch = !searchTerm.trim() || 
                    fund.scheme_name.toLowerCase().includes(searchTerm.toLowerCase()) || 
                    fund.scheme_code.toString().includes(searchTerm) || 
                    group.amc_name.toLowerCase().includes(searchTerm.toLowerCase());
                
                const matchesCategory = selectedCategory === "ALL" || 
                    (fund.category && fund.category.toLowerCase().includes(selectedCategory.toLowerCase()));

                return matchesSearch && matchesCategory;
            });
            return { ...group, schemes: matchingSchemes };
        }).filter(group => group.schemes.length > 0);
    }, [amcGroups, selectedAmc, searchTerm, selectedCategory]);

    const activeVisibleCount = filteredAMCGroups.reduce((acc, g) => acc + g.schemes.length, 0);

    return (
        <div className="max-w-[1800px] mx-auto px-4 sm:px-6 lg:px-8 py-10 w-full space-y-8">
            {/* Header & Title */}
            <div className="border-b border-gray-800/80 pb-6 space-y-4">
                <div className="flex items-center gap-2 text-xs font-mono text-gray-400">
                    <Link href="/synthesis" className="hover:text-blue-400">Synthesis</Link>
                    <span>/</span>
                    <span className="text-blue-400">Supported Funds Directory</span>
                </div>

                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <h1 className="text-2xl sm:text-4xl font-extrabold text-white tracking-tight flex items-center gap-3">
                            <span>Supported Mutual Funds</span>
                            <span className="text-xs font-mono font-normal px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                🟢 {isLoading ? "Loading AMC Directory..." : `${activeVisibleCount} Schemes Shown`}
                            </span>
                        </h1>
                        <p className="text-xs sm:text-sm text-gray-400 max-w-3xl mt-1 leading-relaxed">
                            Browse official mutual fund schemes per AMC family or select an Asset Management Company from the right sidebar.
                        </p>
                    </div>

                    <Link href="/synthesis/generate">
                        <ShimmerButton
                            className="px-6 py-2.5 shadow-xl"
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

            {/* Main Dual Layout: Left Funds Grid + Right AMC Selector Sidebar */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                
                {/* Left Area (8 cols on lg, 9 cols on xl): Search, Filters & Scheme Cards */}
                <div className="lg:col-span-8 xl:col-span-9 space-y-6">
                    {/* Search & Category Filter Bar */}
                    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-gray-950/80 border border-gray-800 p-4 rounded-2xl backdrop-blur-xl">
                        <div className="w-full sm:w-80 relative">
                            <input 
                                type="text"
                                value={searchTerm}
                                onChange={(e) => setSearchTerm(e.target.value)}
                                placeholder="Search fund name or code..."
                                className="w-full bg-gray-900 border border-gray-800 rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition-colors font-mono"
                            />
                        </div>

                        <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
                            <span className="text-[11px] font-mono text-gray-500 uppercase mr-1">Category:</span>
                            {categories.map(cat => (
                                <button
                                    key={cat}
                                    onClick={() => setSelectedCategory(cat)}
                                    className={`px-3 py-1 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                                        selectedCategory === cat
                                            ? "bg-blue-600 text-white shadow-md shadow-blue-600/30"
                                            : "bg-gray-900 text-gray-400 hover:bg-gray-800 hover:text-white border border-gray-800"
                                    }`}
                                >
                                    {cat}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Active AMC Filter Banner */}
                    {selectedAmc !== "ALL" && (
                        <div className="flex items-center justify-between p-3.5 bg-blue-950/40 border border-blue-500/30 rounded-xl text-xs">
                            <div className="flex items-center gap-2 text-white">
                                <span className="font-mono text-blue-400">Filtering by AMC:</span>
                                <span className="font-bold">{selectedAmc}</span>
                            </div>
                            <button 
                                onClick={() => setSelectedAmc("ALL")}
                                className="text-gray-400 hover:text-white underline font-mono text-[11px]"
                            >
                                Show All AMCs ({totalFundsCount})
                            </button>
                        </div>
                    )}

                    {/* Loading State */}
                    {isLoading && (
                        <div className="p-16 flex flex-col items-center justify-center bg-gray-950/80 border border-gray-800/80 rounded-2xl space-y-3">
                            <div className="w-6 h-6 rounded-full bg-blue-500 animate-ping" />
                            <span className="text-xs font-mono text-gray-400">Loading mutual fund schemes...</span>
                        </div>
                    )}

                    {/* Funds Display Grid */}
                    {!isLoading && filteredAMCGroups.length === 0 ? (
                        <div className="p-12 text-center bg-gray-950/80 border border-gray-800/80 rounded-2xl text-gray-500">
                            <p className="text-sm font-semibold text-gray-300">No matching mutual funds found.</p>
                            <p className="text-xs text-gray-500 mt-1">Try clearing your search query or selecting a different AMC from the right sidebar.</p>
                        </div>
                    ) : (
                        <div className="space-y-10">
                            {filteredAMCGroups.map(group => (
                                <div key={group.amc_name} className="space-y-4">
                                    <div className="flex items-center justify-between border-b border-gray-800/80 pb-2">
                                        <div className="flex items-center gap-3">
                                            <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-md bg-blue-500/10 text-blue-400 border border-blue-500/20">
                                                AMC
                                            </span>
                                            <h2 className="text-lg font-extrabold text-white">{group.amc_name}</h2>
                                            <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                                                {group.schemes.length} Funds
                                            </span>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                                        {group.schemes.map(fund => {
                                            const isSelected = selectedFunds.some(f => String(f.scheme_code) === String(fund.scheme_code));
                                            return (
                                                <MagicCard 
                                                    key={fund.scheme_code}
                                                    className={`p-5 bg-gray-950/80 rounded-2xl space-y-3 flex flex-col justify-between transition-all ${
                                                        isSelected 
                                                            ? "border-emerald-500/70 shadow-lg shadow-emerald-950/40 bg-emerald-950/20" 
                                                            : "border-gray-800/80 hover:border-gray-700"
                                                    }`}
                                                    gradientFrom="#3b82f6"
                                                    gradientTo="#10b981"
                                                    gradientColor="rgba(16, 185, 129, 0.08)"
                                                >
                                                    <div className="space-y-2">
                                                        <div className="flex items-center justify-between">
                                                            <span className="text-[10px] font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20 font-semibold">
                                                                #{fund.scheme_code}
                                                            </span>
                                                            <span className="text-[10px] font-mono text-emerald-400 flex items-center gap-1">
                                                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                                                                <span>Factsheet Active</span>
                                                            </span>
                                                        </div>

                                                        <h3 className="text-xs font-bold text-white leading-snug line-clamp-2">
                                                            {fund.scheme_name}
                                                        </h3>
                                                    </div>

                                                    <div className="space-y-3 pt-2">
                                                        <div className="flex items-center justify-between border-t border-gray-800/60 pt-2 text-[11px]">
                                                            <span className="text-gray-400 font-mono truncate max-w-[120px]">{fund.category || "Equity"}</span>
                                                            {fund.return_3y && (
                                                                <span className="font-mono text-emerald-400 font-bold">
                                                                    {typeof fund.return_3y === 'number' ? `+${fund.return_3y}%` : fund.return_3y} <span className="text-[9px] text-gray-500 font-normal">3Y</span>
                                                                </span>
                                                            )}
                                                        </div>

                                                        <button 
                                                            onClick={() => toggleFundSelection(fund)}
                                                            className={`w-full text-center py-2.5 rounded-xl text-xs font-mono font-bold transition-all flex items-center justify-center gap-2 ${
                                                                isSelected 
                                                                    ? "bg-emerald-600 text-white shadow-md shadow-emerald-600/30"
                                                                    : "bg-blue-600/10 hover:bg-blue-600 hover:text-white text-blue-400 border border-blue-500/30"
                                                            }`}
                                                        >
                                                            <span>{isSelected ? "✓ Selected for Comparison" : "+ Add to Comparison"}</span>
                                                        </button>
                                                    </div>
                                                </MagicCard>
                                            );
                                        })}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Right Area (4 cols on lg, 3 cols on xl): Sticky AMC Selector Sidebar */}
                <div className="lg:col-span-4 xl:col-span-3 space-y-4 sticky top-20">
                    <div className="bg-gray-950/90 border border-gray-800/80 rounded-2xl p-5 space-y-4 backdrop-blur-xl shadow-2xl">
                        <div className="flex items-center justify-between border-b border-gray-800/60 pb-3">
                            <h2 className="text-xs font-mono font-bold uppercase tracking-wider text-gray-300 flex items-center gap-2">
                                <span>🏛️ AMC Selector</span>
                            </h2>
                            <span className="text-[10px] font-mono text-cyan-400">{amcGroups.length} AMCs</span>
                        </div>

                        <p className="text-xs text-gray-400 leading-relaxed">
                            Click an AMC family below to filter the funds displayed on the left:
                        </p>

                        <div className="space-y-1.5 max-h-[600px] overflow-y-auto pr-1 divide-y divide-gray-900">
                            {/* All AMCs Option */}
                            <button
                                onClick={() => setSelectedAmc("ALL")}
                                className={`w-full p-2.5 rounded-xl text-left text-xs transition-all flex items-center justify-between font-medium ${
                                    selectedAmc === "ALL"
                                        ? "bg-blue-600 text-white font-bold shadow-lg shadow-blue-600/30"
                                        : "bg-gray-900/60 text-gray-300 hover:bg-gray-800 hover:text-white border border-gray-800/60"
                                }`}
                            >
                                <span>All Asset Management Companies</span>
                                <span className="font-mono text-[10px] opacity-80">({totalFundsCount})</span>
                            </button>

                            {/* Individual AMC Options */}
                            {amcGroups.map(group => (
                                <button
                                    key={group.amc_name}
                                    onClick={() => setSelectedAmc(group.amc_name)}
                                    className={`w-full p-2.5 rounded-xl text-left text-xs transition-all flex items-center justify-between pt-2.5 ${
                                        selectedAmc === group.amc_name
                                            ? "bg-emerald-600 text-white font-bold shadow-lg shadow-emerald-600/30"
                                            : "bg-gray-900/40 text-gray-400 hover:bg-gray-800 hover:text-white"
                                    }`}
                                >
                                    <span className="truncate pr-2">{group.amc_name}</span>
                                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-gray-950 text-cyan-400 border border-gray-800 font-semibold whitespace-nowrap">
                                        {group.schemes.length}
                                    </span>
                                </button>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* Floating Multi-Fund Comparison Dock */}
            {selectedFunds.length > 0 && (
                <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 w-full max-w-2xl px-4 animate-in slide-in-from-bottom duration-300">
                    <div className="bg-[#070b12]/95 border border-emerald-500/50 p-4 rounded-2xl shadow-2xl backdrop-blur-2xl flex flex-col sm:flex-row items-center justify-between gap-4 shadow-emerald-950/40">
                        <div className="flex items-center gap-3 overflow-x-auto w-full sm:w-auto">
                            <span className="text-xs font-mono font-bold text-emerald-400 uppercase tracking-wider whitespace-nowrap">
                                ({selectedFunds.length}/3) Selected:
                            </span>
                            <div className="flex items-center gap-2">
                                {selectedFunds.map(f => (
                                    <div key={f.scheme_code} className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-gray-900 border border-gray-700 text-xs text-white">
                                        <span className="font-mono text-[10px] text-cyan-400">#{f.scheme_code}</span>
                                        <span className="truncate max-w-[110px] font-semibold">{f.scheme_name}</span>
                                        <button onClick={() => toggleFundSelection(f)} className="text-gray-400 hover:text-red-400 text-xs ml-1 font-bold">✕</button>
                                    </div>
                                ))}
                            </div>
                        </div>

                        <Link 
                            href={`/synthesis/generate?codes=${selectedFunds.map(f => f.scheme_code).join(",")}`}
                            className="w-full sm:w-auto px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-mono font-bold text-xs uppercase tracking-wider rounded-xl transition-all shadow-lg shadow-emerald-600/30 whitespace-nowrap text-center"
                        >
                            Synthesize Comparison ({selectedFunds.length}) →
                        </Link>
                    </div>
                </div>
            )}
        </div>
    );
}
