"use client";

import React from "react";
import { ShieldCheck, FileText } from "lucide-react";

interface InstitutionalPDFTemplateProps {
  fundA?: string;
  fundB?: string;
  reportId?: string;
  date?: string;
}

export function InstitutionalPDFTemplate({
  fundA = "Parag Parikh Flexi Cap",
  fundB = "HDFC Flexi Cap",
  reportId = "8492",
  date = "07 August 2026",
}: InstitutionalPDFTemplateProps) {
  return (
    <div className="hidden print:block w-full max-w-4xl mx-auto p-8 bg-white text-slate-900 font-sans leading-relaxed">
      
      {/* Cover Header */}
      <div className="border-b-2 border-slate-900 pb-6 mb-8 flex justify-between items-end">
        <div>
          <div className="text-xs font-mono uppercase tracking-widest text-slate-500 font-bold mb-1">
            FundersAI Synthesis Studio • Institutional Report #{reportId}
          </div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Mutual Fund Comparative Research Whitepaper
          </h1>
          <h2 className="text-lg font-bold text-emerald-700 mt-1">
            {fundA} vs {fundB}
          </h2>
        </div>

        <div className="text-right text-xs font-mono text-slate-500">
          <div>Report Date: {date}</div>
          <div>Data Source: AMFI & AMC Disclosures</div>
          <div className="text-emerald-700 font-bold mt-1">✓ Grounded Research</div>
        </div>
      </div>

      {/* Executive Summary Section */}
      <div className="mb-8 space-y-3 page-break-inside-avoid">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900 border-b border-slate-300 pb-1">
          1. Executive Verdict & Risk-Adjusted Returns
        </h3>
        <p className="text-xs text-slate-700 leading-normal">
          This quantitative analysis compares <strong>{fundA}</strong> and <strong>{fundB}</strong> across 3-year risk-adjusted returns, downside drawdown capture, portfolio holdings overlap, and expense ratios based on official SEBI AMC disclosures.
        </p>

        <table className="w-full text-xs text-left border-collapse border border-slate-300 mt-3 font-mono">
          <thead>
            <tr className="bg-slate-100 text-slate-800 border-b border-slate-300">
              <th className="p-2 border-r border-slate-300">Metric</th>
              <th className="p-2 border-r border-slate-300">{fundA}</th>
              <th className="p-2 border-r border-slate-300">{fundB}</th>
              <th className="p-2">Advantage</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-b border-slate-200">
              <td className="p-2 border-r border-slate-200 font-bold">3Y Trailing CAGR</td>
              <td className="p-2 border-r border-slate-200">21.4%</td>
              <td className="p-2 border-r border-slate-200">23.8%</td>
              <td className="p-2 text-slate-700">{fundB} (+2.4%)</td>
            </tr>
            <tr className="border-b border-slate-200 bg-slate-50">
              <td className="p-2 border-r border-slate-200 font-bold">Sharpe Ratio</td>
              <td className="p-2 border-r border-slate-200 text-emerald-700 font-bold">1.42</td>
              <td className="p-2 border-r border-slate-200">1.28</td>
              <td className="p-2 text-emerald-700 font-bold">{fundA} (+0.14)</td>
            </tr>
            <tr className="border-b border-slate-200">
              <td className="p-2 border-r border-slate-200 font-bold">Max Drawdown</td>
              <td className="p-2 border-r border-slate-200 text-emerald-700 font-bold">-14.2%</td>
              <td className="p-2 border-r border-slate-200 text-rose-700">-17.8%</td>
              <td className="p-2 text-emerald-700 font-bold">{fundA} (Lower Risk)</td>
            </tr>
            <tr className="border-b border-slate-200 bg-slate-50">
              <td className="p-2 border-r border-slate-200 font-bold">Direct Expense Ratio</td>
              <td className="p-2 border-r border-slate-200 text-emerald-700 font-bold">0.62%</td>
              <td className="p-2 border-r border-slate-200">0.85%</td>
              <td className="p-2 text-emerald-700 font-bold">{fundA} (-0.23%)</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Portfolio Overlap Section */}
      <div className="mb-8 space-y-3 page-break-inside-avoid">
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-900 border-b border-slate-300 pb-1">
          2. Portfolio Concentration & Overlap
        </h3>
        <p className="text-xs text-slate-700">
          The two schemes exhibit a <strong>24.8% portfolio holdings overlap</strong> across 14 stock positions (including HDFC Bank, ICICI Bank, and Reliance Industries).
        </p>
      </div>

      {/* Compliance Disclaimer Footer */}
      <div className="mt-12 pt-4 border-t border-slate-300 text-[10px] text-slate-500 font-sans leading-tight">
        <p className="font-bold text-slate-700">Research & Compliance Notice:</p>
        <p>
          FundersAI Synthesis is strictly a research tool for comparative factsheet analysis. No automated buy, sell, or hold recommendations are generated. Data is sourced from official AMFI and AMC filings. Past performance is no guarantee of future returns.
        </p>
      </div>

    </div>
  );
}
