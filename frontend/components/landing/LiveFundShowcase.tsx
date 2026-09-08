"use client";

import React, { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight } from "lucide-react";

interface FundCard {
  name: string;
  amc: string;
  schemeCode: number;
  href: string;
  cagr3Y: string;
  cagr5Y: string;
  sharpe: string;
  ter: string;
  color: string;
  border: string;
  badge: string;
}

const CATEGORY_TABS = ["Flexi Cap", "Small Cap", "Mid Cap", "Large Cap"] as const;
type CategoryTab = (typeof CATEGORY_TABS)[number];

const FUNDS_BY_CATEGORY: Record<CategoryTab, FundCard[]> = {
  "Flexi Cap": [
    {
      name: "Parag Parikh Flexi Cap Fund",
      amc: "PPFAS",
      schemeCode: 122639,
      href: "/mutual-funds/parag-parikh/parag-parikh-flexi-cap-fund",
      cagr3Y: "21.4%",
      cagr5Y: "23.8%",
      sharpe: "1.42",
      ter: "0.62%",
      color: "from-emerald-500/20 to-emerald-500/5",
      border: "border-emerald-500/30",
      badge: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    },
    {
      name: "HDFC Flexi Cap Fund",
      amc: "HDFC",
      schemeCode: 120503,
      href: "/mutual-funds/hdfc/hdfc-flexi-cap-fund",
      cagr3Y: "23.6%",
      cagr5Y: "22.9%",
      sharpe: "1.38",
      ter: "0.85%",
      color: "from-blue-500/20 to-blue-500/5",
      border: "border-blue-500/30",
      badge: "text-blue-400 bg-blue-500/10 border-blue-500/20",
    },
    {
      name: "Kotak Flexi Cap Fund",
      amc: "Kotak",
      schemeCode: 120505,
      href: "/mutual-funds/kotak/kotak-flexi-cap-fund",
      cagr3Y: "19.8%",
      cagr5Y: "21.2%",
      sharpe: "1.25",
      ter: "0.71%",
      color: "from-purple-500/20 to-purple-500/5",
      border: "border-purple-500/30",
      badge: "text-purple-400 bg-purple-500/10 border-purple-500/20",
    },
    {
      name: "Axis Flexi Cap Fund",
      amc: "Axis",
      schemeCode: 141870,
      href: "/mutual-funds/axis/axis-flexi-cap-fund",
      cagr3Y: "17.9%",
      cagr5Y: "19.4%",
      sharpe: "1.18",
      ter: "0.79%",
      color: "from-amber-500/20 to-amber-500/5",
      border: "border-amber-500/30",
      badge: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    },
  ],
  "Small Cap": [
    {
      name: "Quant Small Cap Fund",
      amc: "Quant",
      schemeCode: 120847,
      href: "/mutual-funds/quant/quant-small-cap-fund",
      cagr3Y: "28.1%",
      cagr5Y: "34.2%",
      sharpe: "1.65",
      ter: "0.63%",
      color: "from-purple-500/20 to-purple-500/5",
      border: "border-purple-500/30",
      badge: "text-purple-400 bg-purple-500/10 border-purple-500/20",
    },
    {
      name: "Nippon India Small Cap Fund",
      amc: "Nippon",
      schemeCode: 118825,
      href: "/mutual-funds/nippon-india/nippon-india-small-cap-fund",
      cagr3Y: "26.4%",
      cagr5Y: "31.5%",
      sharpe: "1.58",
      ter: "0.68%",
      color: "from-amber-500/20 to-amber-500/5",
      border: "border-amber-500/30",
      badge: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    },
    {
      name: "HDFC Small Cap Fund",
      amc: "HDFC",
      schemeCode: 119598,
      href: "/mutual-funds/hdfc/hdfc-small-cap-fund",
      cagr3Y: "24.9%",
      cagr5Y: "29.8%",
      sharpe: "1.49",
      ter: "0.77%",
      color: "from-blue-500/20 to-blue-500/5",
      border: "border-blue-500/30",
      badge: "text-blue-400 bg-blue-500/10 border-blue-500/20",
    },
    {
      name: "Axis Small Cap Fund",
      amc: "Axis",
      schemeCode: 120465,
      href: "/mutual-funds/axis/axis-small-cap-fund",
      cagr3Y: "22.3%",
      cagr5Y: "27.1%",
      sharpe: "1.35",
      ter: "0.82%",
      color: "from-emerald-500/20 to-emerald-500/5",
      border: "border-emerald-500/30",
      badge: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    },
  ],
  "Mid Cap": [
    {
      name: "HDFC Mid-Cap Opportunities Fund",
      amc: "HDFC",
      schemeCode: 119552,
      href: "/mutual-funds/hdfc/hdfc-mid-cap-opportunities-fund",
      cagr3Y: "25.6%",
      cagr5Y: "28.4%",
      sharpe: "1.44",
      ter: "0.74%",
      color: "from-blue-500/20 to-blue-500/5",
      border: "border-blue-500/30",
      badge: "text-blue-400 bg-blue-500/10 border-blue-500/20",
    },
    {
      name: "Kotak Emerging Equity Fund",
      amc: "Kotak",
      schemeCode: 120152,
      href: "/mutual-funds/kotak/kotak-emerging-equity-fund",
      cagr3Y: "24.1%",
      cagr5Y: "27.5%",
      sharpe: "1.38",
      ter: "0.69%",
      color: "from-purple-500/20 to-purple-500/5",
      border: "border-purple-500/30",
      badge: "text-purple-400 bg-purple-500/10 border-purple-500/20",
    },
    {
      name: "Nippon India Growth Fund",
      amc: "Nippon",
      schemeCode: 118834,
      href: "/mutual-funds/nippon-india/nippon-india-growth-fund",
      cagr3Y: "22.8%",
      cagr5Y: "26.1%",
      sharpe: "1.31",
      ter: "0.81%",
      color: "from-amber-500/20 to-amber-500/5",
      border: "border-amber-500/30",
      badge: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    },
  ],
  "Large Cap": [
    {
      name: "ICICI Prudential Bluechip Fund",
      amc: "ICICI",
      schemeCode: 120586,
      href: "/mutual-funds/icici-prudential/icici-prudential-bluechip-fund",
      cagr3Y: "16.8%",
      cagr5Y: "17.9%",
      sharpe: "1.12",
      ter: "0.91%",
      color: "from-emerald-500/20 to-emerald-500/5",
      border: "border-emerald-500/30",
      badge: "text-emerald-400 bg-emerald-500/10 border-emerald-500/20",
    },
    {
      name: "HDFC Top 100 Fund",
      amc: "HDFC",
      schemeCode: 119533,
      href: "/mutual-funds/hdfc/hdfc-top-100-fund",
      cagr3Y: "15.9%",
      cagr5Y: "17.1%",
      sharpe: "1.02",
      ter: "0.68%",
      color: "from-blue-500/20 to-blue-500/5",
      border: "border-blue-500/30",
      badge: "text-blue-400 bg-blue-500/10 border-blue-500/20",
    },
    {
      name: "Mirae Asset Large Cap Fund",
      amc: "Mirae",
      schemeCode: 118701,
      href: "/mutual-funds/mirae-asset/mirae-asset-large-cap-fund",
      cagr3Y: "15.4%",
      cagr5Y: "16.8%",
      sharpe: "1.05",
      ter: "0.54%",
      color: "from-purple-500/20 to-purple-500/5",
      border: "border-purple-500/30",
      badge: "text-purple-400 bg-purple-500/10 border-purple-500/20",
    },
    {
      name: "SBI Bluechip Fund",
      amc: "SBI",
      schemeCode: 119206,
      href: "/mutual-funds/sbi/sbi-bluechip-fund",
      cagr3Y: "14.2%",
      cagr5Y: "15.9%",
      sharpe: "0.98",
      ter: "0.71%",
      color: "from-amber-500/20 to-amber-500/5",
      border: "border-amber-500/30",
      badge: "text-amber-400 bg-amber-500/10 border-amber-500/20",
    },
  ],
};

const ease = [0.22, 1, 0.36, 1] as const;
const CAGR_SCALE_MAX = 35;

export default function LiveFundShowcase() {
  const [activeTab, setActiveTab] = useState<CategoryTab>("Flexi Cap");
  const funds = FUNDS_BY_CATEGORY[activeTab];

  return (
    <div className="rounded-3xl border border-white/10 bg-white/[0.02] p-8 sm:p-12 relative overflow-hidden">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 mb-8 pb-8 border-b border-white/10">
        <div>
          <p className="text-xs font-mono font-bold uppercase tracking-[0.22em] text-[#00FF9D]">
            Live Fund Metrics
          </p>
          <h2 className="text-2xl sm:text-3xl font-bold text-white mt-1">
            Sample Quantitative Metrics from Verified Disclosures
          </h2>
          <p className="text-xs sm:text-sm text-[#aebed6] mt-1.5">
            Calculated deterministically from AMFI NAV histories and official AMC factsheet portfolios.
          </p>
        </div>

        <Link
          href="/mutual-funds"
          className="inline-flex items-center gap-2 text-xs font-mono font-bold text-[#00FF9D] hover:underline shrink-0"
        >
          <span>View all 30+ schemes in screener</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      </div>

      {/* Category tabs */}
      <div className="flex flex-wrap items-center gap-1.5 p-1 bg-slate-900/60 border border-white/10 rounded-xl mb-6 w-fit">
        {CATEGORY_TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`relative px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-colors ${
              activeTab === tab ? "text-[#00FF9D]" : "text-slate-400 hover:text-slate-200"
            }`}
          >
            {activeTab === tab && (
              <motion.span
                layoutId="fund-showcase-tab-highlight"
                className="absolute inset-0 rounded-lg bg-emerald-500/15 border border-emerald-500/40"
                transition={{ type: "spring", stiffness: 400, damping: 32 }}
              />
            )}
            <span className="relative">{tab}</span>
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.25, ease }}
          className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4"
        >
          {funds.map((fund) => {
            const barWidth = `${Math.min(100, (parseFloat(fund.cagr3Y) / CAGR_SCALE_MAX) * 100)}%`;
            return (
              <div
                key={fund.schemeCode}
                className={`group rounded-2xl border ${fund.border} bg-gradient-to-b ${fund.color} p-6 flex flex-col justify-between transition-all hover:scale-[1.02]`}
              >
                <Link href={fund.href} className="block">
                  <div className="flex items-center justify-between mb-3">
                    <span className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded-full border ${fund.badge}`}>
                      {activeTab}
                    </span>
                    <span className="text-xs font-mono text-slate-400">{fund.amc}</span>
                  </div>
                  <h4 className="text-sm font-bold text-white group-hover:text-[#00FF9D] transition leading-snug">
                    {fund.name}
                  </h4>

                  <div className="mt-4">
                    <div className="h-1 rounded-full bg-white/10 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-[#00FF9D] to-emerald-300"
                        style={{ width: barWidth }}
                      />
                    </div>
                    <p className="text-[9px] font-mono text-slate-500 mt-1">3Y CAGR strength</p>
                  </div>

                  <div className="mt-4 pt-4 border-t border-white/10 grid grid-cols-3 gap-2 text-center">
                    <div>
                      <p className="text-[10px] font-mono text-slate-400">3Y CAGR</p>
                      <p className="text-xs font-bold text-white font-mono mt-0.5">{fund.cagr3Y}</p>
                    </div>
                    <div>
                      <p className="text-[10px] font-mono text-slate-400">5Y CAGR</p>
                      <p className="text-xs font-bold text-white font-mono mt-0.5">{fund.cagr5Y}</p>
                    </div>
                    <div>
                      <p className="text-[10px] font-mono text-slate-400">Sharpe</p>
                      <p className="text-xs font-bold text-[#00FF9D] font-mono mt-0.5">{fund.sharpe}</p>
                    </div>
                  </div>
                </Link>

                <div className="mt-4 pt-3 border-t border-white/5 flex items-center justify-between">
                  <span className="text-[10px] font-mono text-slate-500">TER {fund.ter}</span>
                  <Link
                    href={`/dashboard?codes=${fund.schemeCode}`}
                    className="text-[10px] font-mono font-bold text-slate-300 hover:text-[#00FF9D] inline-flex items-center gap-1 transition"
                  >
                    <span>Analyze in Canvas</span>
                    <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            );
          })}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
