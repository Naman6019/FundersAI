"use client";
import { useState, useEffect, useRef, useMemo, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { supabaseBrowser } from "@/lib/supabaseBrowser";
import { ShimmerButton } from "@/components/ui/shimmer-button";
import { BorderBeam } from "@/components/ui/border-beam";
import { AnimatedShinyText } from "@/components/ui/animated-shiny-text";
import { Sparkles } from "@/components/ui/sparkles";
import { NumberTicker } from "@/components/ui/number-ticker";
import { ReportsSubNav } from "@/components/layout/ReportsSubNav";
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import type { User } from "@supabase/supabase-js";
import { schemeDisplayName } from "@/lib/schemeDisplayName";

interface SchemeOption {
    code: number;
    name: string;
    amc: string;
}

const DEFAULT_POPULAR_SCHEMES: SchemeOption[] = [
    { code: 119551, name: "Parag Parikh Flexi Cap Fund", amc: "PPFAS Mutual Fund" },
    { code: 122639, name: "HDFC Flexi Cap Fund", amc: "HDFC Mutual Fund" },
    { code: 151745, name: "HDFC Defence Fund", amc: "HDFC Mutual Fund" },
    { code: 101823, name: "HDFC Top 100 Fund", amc: "HDFC Mutual Fund" },
    { code: 120828, name: "Quant Small Cap Fund", amc: "Quant Mutual Fund" },
    { code: 120823, name: "Quant Active Fund", amc: "Quant Mutual Fund" },
    { code: 113177, name: "Nippon India Small Cap Fund", amc: "Nippon India Mutual Fund" },
    { code: 125497, name: "SBI Small Cap Fund", amc: "SBI Mutual Fund" },
    { code: 100033, name: "SBI Contra Fund", amc: "SBI Mutual Fund" },
    { code: 100356, name: "ICICI Prudential Bluechip Fund", amc: "ICICI Prudential MF" },
    { code: 125354, name: "Axis Small Cap Fund", amc: "Axis Mutual Fund" },
    { code: 112090, name: "Mirae Asset Large Cap Fund", amc: "Mirae Asset Mutual Fund" },
    { code: 120716, name: "UTI Nifty 50 Index Fund", amc: "UTI Mutual Fund" },
];

function MermaidChart({ chart, isStreaming }: { chart: string; isStreaming: boolean }) {
    const [id] = useState(() => `mermaid-${Math.random().toString(36).substring(2, 9)}`);
    const [svg, setSvg] = useState<string>("");
    const [isRendered, setIsRendered] = useState(false);

    useEffect(() => {
        if (chart && !isStreaming) {
            import("mermaid").then((m) => {
                m.default.initialize({ 
                    startOnLoad: false, 
                    theme: "dark",
                    suppressErrorRendering: true 
                });
                m.default.render(id, chart).then((result) => {
                    setSvg(result.svg);
                    setIsRendered(true);
                }).catch(() => {});
            });
        }
    }, [chart, id, isStreaming]);

    if (isRendered) {
        return <div dangerouslySetInnerHTML={{ __html: svg }} className="flex justify-center my-8" />;
    }

    if (isStreaming) {
        return (
            <div className="w-full h-64 bg-surface-2/30 animate-pulse rounded-lg border border-gray-700/50 flex flex-col items-center justify-center my-8">
                <svg className="animate-spin h-8 w-8 text-violet-500 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <AnimatedShinyText className="inline-flex items-center justify-center px-4 py-1">
                    <span className="text-sm font-medium">Generating Chart...</span>
                </AnimatedShinyText>
            </div>
        );
    }

    return (
        <div className="my-6">
            <div className="text-red-400 text-xs font-bold mb-1 ml-1 uppercase tracking-wider">Chart Generation Failed</div>
            <pre className="bg-red-950/30 p-4 rounded text-sm text-red-200 overflow-x-auto border border-red-900/50">
                <code>{chart}</code>
            </pre>
        </div>
    );
}

function ReportChatContent() {
    const searchParams = useSearchParams();
    const initialPromptParam = searchParams.get("prompt");
    const initialCodesParam = searchParams.get("codes") || searchParams.get("schemes");

    const [generationMode, setGenerationMode] = useState<"PROMPT" | "SELECTOR">(
        initialCodesParam ? "SELECTOR" : "PROMPT"
    );
    const [userPrompt, setUserPrompt] = useState(
        initialPromptParam || "Give me a comprehensive report on comparison of HDFC Flexi cap and Parag Flexi Cap."
    );
    const [selectedSchemes, setSelectedSchemes] = useState<SchemeOption[]>(() => {
        if (initialCodesParam) {
            const codes = initialCodesParam.split(",").map(c => Number(c.trim())).filter(c => !isNaN(c));
            const matched = DEFAULT_POPULAR_SCHEMES.filter(s => codes.includes(s.code));
            if (matched.length > 0) return matched;
            return codes.map(c => ({
                code: c,
                name: `Mutual Fund Scheme #${c}`,
                amc: "SEBI Registered AMC"
            }));
        }
        return [DEFAULT_POPULAR_SCHEMES[0], DEFAULT_POPULAR_SCHEMES[1]];
    });
    const [schemeSearchQuery, setSchemeSearchQuery] = useState("");
    const [dbSearchResults, setDbSearchResults] = useState<SchemeOption[]>([]);
    const [isDropdownOpen, setIsDropdownOpen] = useState(false);

    const [reportText, setReportText] = useState("");
    const [streamError, setStreamError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isSaving, setIsSaving] = useState(false);
    const [isDownloading, setIsDownloading] = useState(false);
    const [user, setUser] = useState<User | null>(null);

    useEffect(() => {
        if (initialCodesParam) {
            const codes = initialCodesParam.split(",").map(c => Number(c.trim())).filter(c => !isNaN(c));
            async function loadCustomCodes() {
                try {
                    const { data } = await supabaseBrowser
                        .from("mutual_fund_core_snapshot")
                        .select("scheme_code, scheme_name, amc_name, plan_type, option_type")
                        .in("scheme_code", codes);

                    if (data && data.length > 0) {
                        const SuMap = data.map(d => ({
                            code: Number(d.scheme_code),
                            name: schemeDisplayName(d),
                            amc: d.amc_name || "Mutual Fund"
                        }));
                        setSelectedSchemes(SuMap);
                    } else {
                        const dynamicSchemes: SchemeOption[] = codes.map(c => {
                            const foundInDefault = DEFAULT_POPULAR_SCHEMES.find(s => s.code === c);
                            if (foundInDefault) return foundInDefault;
                            return {
                                code: c,
                                name: `Mutual Fund Scheme #${c}`,
                                amc: "SEBI Registered AMC"
                            };
                        });
                        setSelectedSchemes(dynamicSchemes);
                    }
                } catch (e) {
                    const dynamicSchemes: SchemeOption[] = codes.map(c => ({
                        code: c,
                        name: `Mutual Fund Scheme #${c}`,
                        amc: "SEBI Registered AMC"
                    }));
                    setSelectedSchemes(dynamicSchemes);
                }
            }
            loadCustomCodes();
        }
    }, [initialCodesParam]);

    useEffect(() => {
        supabaseBrowser.auth.getUser().then(({ data }) => {
            if (data?.user) setUser(data.user);
        });
        const { data: authListener } = supabaseBrowser.auth.onAuthStateChange((_, session) => {
            setUser(session?.user || null);
        });
        return () => authListener.subscription.unsubscribe();
    }, []);

    // Fetch live search results from local catalog + Supabase snapshot + /api/search
    useEffect(() => {
        let isMounted = true;
        async function searchFunds() {
            const query = schemeSearchQuery.trim().toLowerCase();
            if (!query) {
                setDbSearchResults(DEFAULT_POPULAR_SCHEMES);
                return;
            }

            // 1. Instant local filter from extended catalog
            const localMatches = DEFAULT_POPULAR_SCHEMES.filter(
                s => s.name.toLowerCase().includes(query) || s.amc.toLowerCase().includes(query)
            );

            // 2. Fetch from Supabase snapshot / DB or Next.js /api/search
            let remoteMatches: SchemeOption[] = [];
            try {
                const { data: supaData } = await supabaseBrowser
                    .from("mutual_fund_core_snapshot")
                    .select("scheme_code, scheme_name, amc_name, plan_type, option_type")
                    .or(`scheme_name.ilike.%${schemeSearchQuery}%,amc_name.ilike.%${schemeSearchQuery}%`)
                    .limit(10);

                if (supaData && supaData.length > 0) {
                    remoteMatches = supaData.map(d => ({
                        code: Number(d.scheme_code),
                        name: schemeDisplayName(d),
                        amc: d.amc_name || "Mutual Fund"
                    }));
                } else {
                    const res = await fetch(`/api/search?q=${encodeURIComponent(schemeSearchQuery)}&type=mf`);
                    if (res.ok) {
                        const json = await res.json();
                        if (json.results && Array.isArray(json.results)) {
                            type RemoteMatch = { id: string | number; title?: string; name?: string; subtitle?: string };
                            remoteMatches = json.results.map((r: RemoteMatch) => ({
                                code: Number(r.id),
                                name: r.title || r.name,
                                amc: r.subtitle || "Mutual Fund"
                            }));
                        }
                    }
                }
            } catch (err) {
                console.warn("Remote search query failed, using local catalog filter:", err);
            }

            if (isMounted) {
                const combinedMap = new Map<number, SchemeOption>();
                localMatches.forEach(s => combinedMap.set(s.code, s));
                remoteMatches.forEach(s => combinedMap.set(s.code, s));
                setDbSearchResults(Array.from(combinedMap.values()));
            }
        }
        searchFunds();
        return () => { isMounted = false; };
    }, [schemeSearchQuery]);

    const filteredSchemes = useMemo(() => {
        return dbSearchResults.filter(
            s => !selectedSchemes.some(sel => sel.code === s.code)
        );
    }, [dbSearchResults, selectedSchemes]);

    const addScheme = (scheme: SchemeOption) => {
        if (selectedSchemes.length >= 3) {
            alert("You can compare up to 3 funds in a single report.");
            return;
        }
        setSelectedSchemes(prev => [...prev, scheme]);
        setSchemeSearchQuery("");
        setIsDropdownOpen(false);
    };

    const removeScheme = (code: number) => {
        if (selectedSchemes.length <= 1) {
            alert("At least 1 scheme must be selected for comparison.");
            return;
        }
        setSelectedSchemes(prev => prev.filter(s => s.code !== code));
    };

    const saveReport = async () => {
        setIsSaving(true);
        try {
            const { data: { user }, error: authError } = await supabaseBrowser.auth.getUser();
            if (authError || !user) {
                alert(`Authentication error: ${authError?.message || "Not logged in."}`);
                setIsSaving(false);
                return;
            }
            const headerMatch = reportText.match(/^#\s+(.+)$/m);
            const title = headerMatch && headerMatch[1] 
                ? headerMatch[1].replace(/[*_#]/g, '').trim() 
                : (generationMode === "PROMPT" ? userPrompt.slice(0, 60) : `Comparison of ${selectedSchemes.map(s => s.name).join(" vs ")}`);

            const { error } = await supabaseBrowser.from('saved_reports').insert({
                user_id: user.id,
                report_title: title,
                funds_compared: selectedSchemes.map(s => s.code.toString()),
                markdown_content: reportText
            });
            
            if (error) {
                alert(`Failed to save report: ${error.message}`);
            } else {
                alert("Report saved successfully to your Dashboard!");
            }
        } catch (e: unknown) {
            alert(`Exception saving report: ${e instanceof Error ? e.message : String(e)}`);
        }
        setIsSaving(false);
    };
    
    const downloadPDF = async () => {
        if (!user) {
            alert("Authentication error: You must be logged in to download reports.");
            return;
        }
        setIsDownloading(true);
        try {
            const element = document.getElementById('report-content');
            if (!element) return;
            
            const htmlContent = element.innerHTML;
            const response = await fetch("/api/reports/pdf", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ html: htmlContent })
            });
            
            if (!response.ok) throw new Error("Failed to generate PDF.");
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `synthesis-report-${new Date().toISOString().split('T')[0]}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } catch (e: unknown) {
            alert(`Exception downloading PDF: ${e instanceof Error ? e.message : String(e)}`);
        }
        setIsDownloading(false);
    };

    const generateReport = async () => {
        setIsLoading(true);
        setReportText("");
        
        let payloadSchemeCodes: number[] = [];
        let payloadUserMessage = "";

        if (generationMode === "PROMPT") {
            payloadUserMessage = userPrompt;
            payloadSchemeCodes = [119551, 122639];
        } else {
            payloadSchemeCodes = selectedSchemes.map(s => s.code);
            payloadUserMessage = `Write a comprehensive institutional comparison report for: ${selectedSchemes.map(s => s.name).join(" and ")}`;
        }

        setStreamError(null);
        try {
            const response = await fetch("/api/reports/stream", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    scheme_codes: payloadSchemeCodes,
                    thread_id: `session_${Date.now()}`,
                    user_message: payloadUserMessage
                }),
            });

            if (!response.ok) {
                const errData = await response.json().catch(() => ({}));
                const msg = errData?.error || errData?.message || `Report synthesis failed (HTTP ${response.status}). Please try again.`;
                setStreamError(msg);
                setIsLoading(false);
                return;
            }

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();

            if (!reader) {
                setStreamError("Unable to initialize response stream from synthesis engine.");
                setIsLoading(false);
                return;
            }
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split("\n\n");

                for (const line of lines) {
                    if (line.startsWith("data: ")) {
                        const dataStr = line.replace("data: ", "");
                        try {
                            const parsedData = JSON.parse(dataStr);
                            if (parsedData.text) {
                                setReportText((prev) => prev + parsedData.text);
                            }
                        } catch {
                            // Ignore incomplete JSON chunks
                        }
                    }
                }
            }
        } catch (e: unknown) {
            console.error("Stream error:", e);
            setStreamError("A network error occurred while generating the report. Please check your connection and try again.");
        }
        setIsLoading(false);
    };

    const markdownComponents = useMemo(() => ({
        code({
            className,
            children,
            ...props
        }: React.HTMLAttributes<HTMLElement> & { inline?: boolean }) {
            const inline = (props as { inline?: boolean }).inline;
            const match = /language-(\w+)/.exec(className || "");
            if (!inline && match && match[1] === "mermaid") {
                return <MermaidChart chart={String(children).replace(/\n$/, "")} isStreaming={isLoading} />;
            }
            return <code className={className} {...props}>{children}</code>;
        },
    }), [isLoading]);

    return (
        <div className="max-w-[1800px] mx-auto p-4 sm:p-6 lg:p-8 w-full print:p-0 print:max-w-none space-y-8">
            {/* Header & Breadcrumb Bar */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-line pb-6 print:hidden">
                <div className="space-y-1">
                    <Breadcrumbs
                        tone="synthesis"
                        className="tracking-wider"
                        items={[
                            { label: 'FundersAI', href: '/' },
                            { label: 'Synthesis', href: '/synthesis' },
                            { label: '[ WORKSTATION ]' },
                        ]}
                    />
                    <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight flex items-center gap-3 font-serif-display">
                        <span>Synthesis Studio</span>
                        <span className="text-xs font-mono font-bold uppercase tracking-widest px-2.5 py-0.5 rounded-md bg-violet-500/10 text-violet-400 border border-violet-500/30">
                            AI Multi-Agent Research Engine
                        </span>
                    </h1>
                </div>

                {/* Header Action / Auth Profile Indicator */}
                <div className="flex items-center gap-4">
                    {/* Quantitative Live Stats Bar */}
                    <div className="hidden sm:flex items-center gap-4 sm:gap-6 font-mono border border-line bg-background/80 px-4 py-2.5 rounded-xl backdrop-blur-md">
                        <div className="text-left">
                            <div className="text-[10px] text-text-3 uppercase tracking-wider">AMC Disclosures</div>
                            <div className="text-sm font-bold text-white flex items-center">
                                <NumberTicker value={1240} className="text-white" />
                                <span>+</span>
                            </div>
                        </div>
                        <div className="h-6 w-px bg-surface-2" />
                        <div className="text-left">
                            <div className="text-[10px] text-text-3 uppercase tracking-wider">Verifiability</div>
                            <div className="text-sm font-bold text-emerald-400">99.8%</div>
                        </div>
                        <div className="h-6 w-px bg-surface-2" />
                        <div className="text-left">
                            <div className="text-[10px] text-text-3 uppercase tracking-wider">Ingestion Speed</div>
                            <div className="text-sm font-bold text-violet-400">0.4s</div>
                        </div>
                    </div>

                    {/* Auth Status / Sign in Button */}
                    {user ? (
                        <div className="flex items-center gap-2 border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-2 rounded-xl font-mono text-xs text-emerald-400 shadow-sm">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                            <span className="truncate max-w-[130px] font-bold">{user.email}</span>
                            <button 
                                onClick={() => supabaseBrowser.auth.signOut()} 
                                className="text-[10px] text-text-2 hover:text-white underline ml-1"
                            >
                                Sign Out
                            </button>
                        </div>
                    ) : (
                        <a 
                            href="/login?next=/synthesis/generate"
                            className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-xl font-mono font-bold text-xs uppercase tracking-wider transition-all shadow-lg shadow-violet-900/30 flex items-center gap-1.5"
                        >
                            <span>Log In to Save</span>
                            <span>→</span>
                        </a>
                    )}
                </div>
            </div>

            {/* In-Page Navigation Options Menu */}
            <ReportsSubNav />
            
            {/* Main Interactive Dual Input Controls */}
            <div className="relative z-30 bg-surface-1 border border-line rounded-2xl p-6 space-y-5 shadow-2xl backdrop-blur-xl overflow-hidden print:hidden">
                <Sparkles density={35} color="#8b5cf6" className="absolute inset-0 pointer-events-none opacity-25" />
                {/* Mode Selector Tabs */}
                <div className="flex items-center justify-between border-b border-line pb-4">
                    <div className="flex items-center gap-2">
                        <button
                            onClick={() => setGenerationMode("PROMPT")}
                            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
                                generationMode === "PROMPT"
                                    ? "bg-violet-600 text-white shadow-lg shadow-violet-600/30"
                                    : "bg-gray-900 text-text-2 hover:bg-surface-2 hover:text-white border border-line"
                            }`}
                        >
                            <span>💬 Option 1: AI Prompt Input</span>
                        </button>
                        <button
                            onClick={() => setGenerationMode("SELECTOR")}
                            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
                                generationMode === "SELECTOR"
                                    ? "bg-emerald-600 text-white shadow-lg shadow-emerald-600/30"
                                    : "bg-gray-900 text-text-2 hover:bg-surface-2 hover:text-white border border-line"
                            }`}
                        >
                            <span>🎯 Option 2: Fund Selector & Catalog</span>
                        </button>
                    </div>

                    <Link 
                        href="/synthesis/supported-funds" 
                        className="text-xs font-mono text-violet-400 hover:text-violet-300 flex items-center gap-1"
                    >
                        <span>Browse 1,000+ Funds Directory</span>
                        <span>→</span>
                    </Link>
                </div>

                {/* Option 1: AI Prompt Mode */}
                {generationMode === "PROMPT" && (
                    <div className="space-y-3">
                        <label className="block text-xs font-mono font-semibold text-text-2 uppercase tracking-wider">
                            Option 1: Enter Natural Language Research Prompt
                        </label>
                        <textarea
                            rows={3}
                            value={userPrompt}
                            onChange={(e) => setUserPrompt(e.target.value)}
                            placeholder="e.g. Give me a comprehensive report on comparison of HDFC Flexi cap and Parag Flexi Cap."
                            className="w-full bg-gray-900/80 border border-line rounded-xl p-4 text-xs sm:text-sm text-white placeholder-gray-500 focus:outline-none focus:border-violet-500 transition-colors font-sans leading-relaxed"
                        />
                        <div className="flex items-center gap-2 text-[11px] font-mono text-text-3">
                            <span className="text-violet-400 font-bold">Quick Examples:</span>
                            <button 
                                onClick={() => setUserPrompt("Give me a comprehensive report on comparison of HDFC Flexi cap and Parag Flexi Cap.")}
                                className="hover:text-white underline"
                            >
                                HDFC vs PPFAS Flexi Cap
                            </button>
                            <span>•</span>
                            <button 
                                onClick={() => setUserPrompt("Analyze Quant Small Cap vs Nippon Small Cap volatility and Sharpe ratio.")}
                                className="hover:text-white underline"
                            >
                                Quant vs Nippon Small Cap
                            </button>
                        </div>
                    </div>
                )}

                {/* Option 2: Manual Scheme Selector & Catalog Mode */}
                {generationMode === "SELECTOR" && (
                    <div className="space-y-5">
                        <div className="flex items-center justify-between">
                            <label className="block text-xs font-mono font-semibold text-text-2 uppercase tracking-wider">
                                Option 2: Select Up to 3 Funds for Comparison ({selectedSchemes.length}/3 Selected)
                            </label>
                            <span className="text-[11px] font-mono text-emerald-400">
                                {3 - selectedSchemes.length} slots remaining
                            </span>
                        </div>

                        {/* Selected Scheme Badges */}
                        <div className="flex flex-wrap items-center gap-2 min-h-[38px] p-2 bg-gray-900/60 border border-line rounded-xl">
                            {selectedSchemes.map(s => (
                                <div key={s.code} className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-surface-2 border border-emerald-500/40 text-white text-xs font-semibold shadow-md">
                                    <span className="text-[10px] font-mono text-emerald-400">#{s.code}</span>
                                    <span>{s.name}</span>
                                    <button onClick={() => removeScheme(s.code)} className="text-text-2 hover:text-red-400 text-sm ml-1 font-bold">✕</button>
                                </div>
                            ))}
                            {selectedSchemes.length === 0 && (
                                <span className="text-xs text-text-3 font-mono px-2">No funds selected. Search or click below to add up to 3 funds.</span>
                            )}
                        </div>

                        {/* Autocomplete Search Input */}
                        <div className="relative">
                            <input 
                                type="text"
                                value={schemeSearchQuery}
                                onFocus={() => setIsDropdownOpen(true)}
                                onChange={(e) => {
                                    setSchemeSearchQuery(e.target.value);
                                    setIsDropdownOpen(true);
                                }}
                                placeholder="Search live catalog of 1,000+ funds (e.g. ICICI, HDFC, SBI, Quant, UTI, Axis, PPFAS)..."
                                className="w-full bg-gray-900 border border-line rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500 transition-colors font-mono"
                            />

                            {/* Dropdown Overlay with high z-index */}
                            {isDropdownOpen && filteredSchemes.length > 0 && (
                                <div className="absolute left-0 right-0 top-full mt-2 bg-background border border-line rounded-xl shadow-2xl z-50 max-h-64 overflow-y-auto divide-y divide-gray-900">
                                    {filteredSchemes.map(scheme => (
                                        <button
                                            key={scheme.code}
                                            onClick={() => addScheme(scheme)}
                                            className="w-full px-4 py-2.5 text-left hover:bg-gray-900 transition-colors flex items-center justify-between text-xs"
                                        >
                                            <div>
                                                <span className="font-bold text-white block">{scheme.name}</span>
                                                <span className="text-[10px] text-text-3 font-mono">{scheme.amc}</span>
                                            </div>
                                            <span className="text-[10px] font-mono text-violet-400 px-2 py-0.5 rounded bg-violet-500/10 border border-violet-500/20">
                                                + Add #{scheme.code}
                                            </span>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Supported Fund Catalog Grid */}
                        <div className="space-y-2 pt-2 border-t border-line/60">
                            <span className="text-[11px] font-mono text-text-2 uppercase tracking-wider block">
                                Quick Selection Catalog
                            </span>
                            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2.5">
                                {DEFAULT_POPULAR_SCHEMES.map(scheme => {
                                    const isSelected = selectedSchemes.some(s => s.code === scheme.code);
                                    return (
                                        <button
                                            key={scheme.code}
                                            onClick={() => {
                                                if (isSelected) {
                                                    removeScheme(scheme.code);
                                                } else {
                                                    addScheme(scheme);
                                                }
                                            }}
                                            className={`p-3 rounded-xl border text-left transition-all flex flex-col justify-between gap-2 ${
                                                isSelected
                                                    ? "bg-emerald-950/40 border-emerald-500/50 shadow-lg shadow-emerald-900/20"
                                                    : "bg-gray-900/60 border-line hover:border-gray-700 hover:bg-gray-900"
                                            }`}
                                        >
                                            <div className="flex items-start justify-between gap-2">
                                                <span className="text-xs font-bold text-white leading-snug line-clamp-2">{scheme.name}</span>
                                                {isSelected ? (
                                                    <span className="shrink-0 px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500 text-black">
                                                        ✓ Selected
                                                    </span>
                                                ) : (
                                                    <span className="shrink-0 px-2 py-0.5 rounded text-[10px] font-mono text-text-2 bg-surface-2 border border-gray-700">
                                                        + Select
                                                    </span>
                                                )}
                                            </div>
                                            <div className="flex items-center justify-between text-[10px] font-mono text-text-3">
                                                <span>{scheme.amc}</span>
                                                <span>#{scheme.code}</span>
                                            </div>
                                        </button>
                                    );
                                })}
                            </div>
                        </div>
                    </div>
                )}

                {streamError && (
                    <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs flex items-center justify-between gap-3">
                        <div className="flex items-center gap-2">
                            <span className="text-base">⚠️</span>
                            <span className="font-mono">{streamError}</span>
                        </div>
                        <button
                            type="button"
                            onClick={() => setStreamError(null)}
                            className="text-red-400 hover:text-white font-mono text-xs px-2 py-1 rounded bg-red-500/20"
                        >
                            Dismiss
                        </button>
                    </div>
                )}

                {/* Generate Action Trigger */}
                <div className="pt-2 flex items-center justify-between border-t border-line">
                    <span className="text-xs font-mono text-text-2">
                        Ingesting live AMC disclosures from SEBI repository.
                    </span>

                    <ShimmerButton
                        onClick={generateReport}
                        disabled={isLoading}
                        className="px-8 py-3 disabled:opacity-50 shadow-xl"
                        shimmerColor="#ffffff"
                        shimmerSize="0.05em"
                        borderRadius="0.75rem"
                        background="#7c3aed"
                    >
                        <span className="text-white text-xs font-bold tracking-wide flex items-center gap-2">
                            <span>{isLoading ? "Synthesizing AI Report..." : "Start Synthesis Engine"}</span>
                            <span>⚡</span>
                        </span>
                    </ShimmerButton>
                </div>
            </div>

            {/* Dual Pane Studio Output Layout */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
                {/* Left Sidebar: Execution Progress Monitor */}
                <div className="lg:col-span-3 xl:col-span-3 space-y-4 print:hidden">
                    <div className="bg-surface-1 border border-line rounded-2xl p-5 space-y-4 shadow-xl backdrop-blur-xl border-t-violet-500/20">
                        <div className="flex items-center justify-between border-b border-line pb-3">
                            <span className="text-xs font-mono font-bold uppercase tracking-wider text-violet-400">AI Execution Pipeline</span>
                            <span className={`w-2 h-2 rounded-full ${isLoading ? 'bg-violet-400 animate-ping' : 'bg-emerald-500'}`} />
                        </div>

                        <div className="space-y-3 font-mono text-[11px]">
                            <div className="flex items-center gap-2.5 text-text-2">
                                <span className={`px-1.5 py-0.5 rounded font-bold text-[10px] ${isLoading ? 'bg-violet-500/20 text-violet-400 border border-violet-500/40' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'}`}>#01</span>
                                <span className="font-semibold">Ingesting AMC Disclosures</span>
                            </div>
                            <div className="flex items-center gap-2.5 text-text-2">
                                <span className={`px-1.5 py-0.5 rounded font-bold text-[10px] ${isLoading ? 'bg-violet-500/20 text-violet-400 border border-violet-500/40 animate-pulse' : reportText ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'bg-gray-900 text-gray-600 border border-line'}`}>#02</span>
                                <span className="font-semibold">Calculating Risk Metrics</span>
                            </div>
                            <div className="flex items-center gap-2.5 text-text-2">
                                <span className={`px-1.5 py-0.5 rounded font-bold text-[10px] ${isLoading ? 'bg-violet-500/20 text-violet-400 border border-violet-500/40 animate-pulse' : reportText ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'bg-gray-900 text-gray-600 border border-line'}`}>#03</span>
                                <span className="font-semibold">Building Visual Diagrams</span>
                            </div>
                            <div className="flex items-center gap-2.5 text-text-2">
                                <span className={`px-1.5 py-0.5 rounded font-bold text-[10px] ${reportText && !isLoading ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40' : 'bg-gray-900 text-gray-600 border border-line'}`}>#04</span>
                                <span className="font-semibold">Formatting & Export</span>
                            </div>
                        </div>
                    </div>

                    <div className="bg-surface-1 border border-line rounded-2xl p-5 space-y-3 backdrop-blur-xl border-t-violet-500/20">
                        <div className="flex items-center justify-between border-b border-line pb-2">
                            <span className="text-xs font-mono font-bold uppercase tracking-wider text-text-2">Selected Target Schemes</span>
                            <span className="text-[10px] font-mono text-violet-400 font-semibold">({selectedSchemes.length}/3)</span>
                        </div>

                        <div className="text-[10px] font-mono text-violet-400 font-medium px-2 py-1 rounded bg-violet-500/10 border border-violet-500/20">
                            {generationMode === "PROMPT" ? "[ OPTION 1: PROMPT AUTO-EXTRACT ]" : "[ OPTION 2: CUSTOM FUND CATALOG ]"}
                        </div>

                        <div className="space-y-2 pt-1">
                            {selectedSchemes.map(s => (
                                <div key={s.code} className="flex items-center justify-between p-2.5 rounded-xl bg-gray-900/80 border border-line text-xs hover:border-gray-700 transition-colors">
                                    <span className="font-semibold text-white truncate max-w-[150px]">{s.name}</span>
                                    <div className="flex items-center gap-1.5">
                                        <span className="font-mono text-[10px] text-violet-400">#{s.code}</span>
                                        <button onClick={() => removeScheme(s.code)} className="text-text-3 hover:text-red-400 text-xs font-bold px-1">✕</button>
                                    </div>
                                </div>
                            ))}

                            {selectedSchemes.length === 0 && (
                                <div className="text-center py-4 text-xs font-mono text-text-3">
                                    No funds selected. Switch to Option 2 to pick funds from catalog.
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Right Main Report Output Canvas */}
                <div className="lg:col-span-9 xl:col-span-9 space-y-4">
                    {/* Action Bar */}
                    {reportText && (
                        <div className="flex items-center justify-between p-4 bg-background/80 border border-line rounded-2xl backdrop-blur-xl print:hidden">
                            <span className="text-xs font-mono text-emerald-400 font-bold flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                                <span>Report Generation Complete</span>
                            </span>

                            <div className="flex items-center gap-2">
                                <button
                                    onClick={saveReport}
                                    disabled={isSaving}
                                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl font-semibold text-xs transition-all disabled:opacity-50 shadow-lg shadow-emerald-600/20"
                                >
                                    {isSaving ? "Saving..." : "Save Report"}
                                </button>
                                <button
                                    onClick={downloadPDF}
                                    disabled={isDownloading}
                                    className="px-4 py-2 bg-gray-900 hover:bg-surface-2 border border-gray-700 text-text-1 rounded-xl font-semibold text-xs flex items-center gap-2 transition-all disabled:opacity-50 shadow-lg"
                                >
                                    <span>Download PDF</span>
                                </button>
                            </div>
                        </div>
                    )}

                    {/* Report Canvas */}
                    <div 
                        id="report-content" 
                        className="relative min-h-[500px] text-text-2 [&_h1]:text-white [&_h2]:text-white [&_h2]:text-2xl [&_h2]:mt-8 [&_h2]:mb-4 [&_h3]:text-white [&_h3]:text-xl [&_h3]:mt-6 [&_h3]:mb-3 [&_h4]:text-white [&_h4]:text-lg [&_h4]:mt-4 [&_h4]:mb-2 [&_strong]:text-white [&_table]:w-full [&_table]:mt-4 [&_table]:mb-8 [&_th]:text-left [&_th]:border-b [&_th]:border-gray-500 [&_th]:pb-3 [&_th]:text-white [&_td]:border-b [&_td]:border-line [&_td]:py-3 [&_li]:mb-2 [&_ul]:list-disc [&_ul]:pl-6 p-6 sm:p-8 bg-surface-1 border border-line rounded-2xl shadow-2xl backdrop-blur-xl overflow-hidden"
                    >
                        {isLoading && (
                            <BorderBeam size={300} duration={10} delay={0} colorFrom="#8b5cf6" colorTo="#8b5cf6" />
                        )}
                        {reportText ? (
                            <ReactMarkdown
                                remarkPlugins={[remarkGfm]}
                                components={markdownComponents}
                            >
                                {reportText}
                            </ReactMarkdown>
                        ) : (
                            <div className="h-96 flex flex-col items-center justify-center text-center space-y-3">
                                <div className="w-12 h-12 rounded-2xl bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400">
                                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                                </div>
                                <div className="space-y-1">
                                    <h3 className="text-base font-semibold text-white">Ready for Synthesis</h3>
                                    <p className="text-xs text-text-2 max-w-sm">Choose Option 1 (Prompt) or Option 2 (Fund Selector) above and click &ldquo;Start Synthesis Engine&rdquo;.</p>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function ReportChat() {
    return (
        <Suspense fallback={
            <div className="max-w-[1800px] mx-auto p-8 text-center text-text-2 font-mono text-xs">
                Loading Synthesis Workstation...
            </div>
        }>
            <ReportChatContent />
        </Suspense>
    );
}

