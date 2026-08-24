'use client';

import React, { useState, useMemo } from 'react';
import Link from 'next/link';
import { Calculator, TrendingUp, Sparkles, ArrowRight, ShieldCheck, HelpCircle, ChevronDown, ChevronUp } from 'lucide-react';

interface CategoryBenchmark {
  category: string;
  rate: number;
  description: string;
  slug: string;
}

const CATEGORY_BENCHMARKS: CategoryBenchmark[] = [
  { category: 'Large Cap', rate: 12.0, description: 'Stable blue-chip equity (Nifty 50 TRI)', slug: 'large-cap' },
  { category: 'Flexi Cap', rate: 14.5, description: 'Multi-cap dynamic allocation', slug: 'flexi-cap' },
  { category: 'Mid Cap', rate: 16.5, description: 'High-growth mid-sized companies', slug: 'mid-cap' },
  { category: 'Small Cap', rate: 19.0, description: 'Aggressive alpha & high volatility', slug: 'small-cap' },
  { category: 'ELSS Tax Saver', rate: 14.0, description: 'Section 80C tax deduction with 3Y lock-in', slug: 'elss' },
];

function formatInr(val: number): string {
  if (val >= 10000000) {
    return `₹${(val / 10000000).toFixed(2)} Cr`;
  }
  if (val >= 100000) {
    return `₹${(val / 100000).toFixed(2)} Lakh`;
  }
  return `₹${Math.round(val).toLocaleString('en-IN')}`;
}

export default function SipCalculatorPublic() {
  const [mode, setMode] = useState<'sip' | 'lumpsum'>('sip');
  const [monthlyAmount, setMonthlyAmount] = useState<number>(10000);
  const [lumpsumAmount, setLumpsumAmount] = useState<number>(100000);
  const [annualReturn, setAnnualReturn] = useState<number>(14.5);
  const [years, setYears] = useState<number>(15);
  const [stepUpPercent, setStepUpPercent] = useState<number>(0);
  const [adjustInflation, setAdjustInflation] = useState<boolean>(false);
  const [inflationRate, setInflationRate] = useState<number>(6.0);
  const [showSchedule, setShowSchedule] = useState<boolean>(false);

  // ─── Mathematical Compounding Calculations ─────────────────────────────────

  const calculation = useMemo(() => {
    const r = annualReturn / 100 / 12; // Monthly rate
    const totalMonths = years * 12;
    let totalInvested = 0;
    let futureValue = 0;
    const yearlyBreakdown: { year: number; invested: number; totalInvested: number; wealth: number; gains: number }[] = [];

    if (mode === 'lumpsum') {
      totalInvested = lumpsumAmount;
      futureValue = lumpsumAmount * Math.pow(1 + annualReturn / 100, years);

      let currentWealth = lumpsumAmount;
      for (let y = 1; y <= years; y++) {
        currentWealth = lumpsumAmount * Math.pow(1 + annualReturn / 100, y);
        yearlyBreakdown.push({
          year: y,
          invested: y === 1 ? lumpsumAmount : 0,
          totalInvested: lumpsumAmount,
          wealth: Math.round(currentWealth),
          gains: Math.round(currentWealth - lumpsumAmount),
        });
      }
    } else {
      // SIP with optional Step-Up
      let currentMonthly = monthlyAmount;
      let accumulatedWealth = 0;
      let cumulativeInvested = 0;

      for (let y = 1; y <= years; y++) {
        let yearInvested = 0;
        for (let m = 1; m <= 12; m++) {
          accumulatedWealth = (accumulatedWealth + currentMonthly) * (1 + r);
          cumulativeInvested += currentMonthly;
          yearInvested += currentMonthly;
        }
        yearlyBreakdown.push({
          year: y,
          invested: Math.round(yearInvested),
          totalInvested: Math.round(cumulativeInvested),
          wealth: Math.round(accumulatedWealth),
          gains: Math.round(accumulatedWealth - cumulativeInvested),
        });

        // Step-up for next year
        if (stepUpPercent > 0) {
          currentMonthly = currentMonthly * (1 + stepUpPercent / 100);
        }
      }

      totalInvested = cumulativeInvested;
      futureValue = accumulatedWealth;
    }

    const gains = Math.max(0, futureValue - totalInvested);
    const inflationAdjustedFV = futureValue / Math.pow(1 + inflationRate / 100, years);
    const gainShare = futureValue > 0 ? (gains / futureValue) * 100 : 0;

    return {
      totalInvested: Math.round(totalInvested),
      futureValue: Math.round(futureValue),
      gains: Math.round(gains),
      inflationAdjustedFV: Math.round(inflationAdjustedFV),
      gainShare: Math.round(gainShare * 10) / 10,
      yearlyBreakdown,
    };
  }, [mode, monthlyAmount, lumpsumAmount, annualReturn, years, stepUpPercent, inflationRate]);

  return (
    <div className="space-y-10">
      {/* ─── Mode Selector (SIP vs Lumpsum) ──────────────────────────────────── */}
      <div className="flex justify-center">
        <div className="inline-flex rounded-2xl border border-white/10 bg-white/[0.03] p-1.5 backdrop-blur-md">
          <button
            onClick={() => setMode('sip')}
            className={`px-6 py-2.5 rounded-xl text-xs font-bold transition-all ${
              mode === 'sip'
                ? 'bg-[#00FF9D] text-black shadow-lg shadow-[#00FF9D]/20'
                : 'text-[#aebed6] hover:text-white'
            }`}
          >
            Systematic Investment Plan (SIP)
          </button>
          <button
            onClick={() => setMode('lumpsum')}
            className={`px-6 py-2.5 rounded-xl text-xs font-bold transition-all ${
              mode === 'lumpsum'
                ? 'bg-[#66a3ff] text-black shadow-lg shadow-[#66a3ff]/20'
                : 'text-[#aebed6] hover:text-white'
            }`}
          >
            One-Time Lumpsum
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* ─── Left Column: Interactive Inputs & Sliders ──────────────────────── */}
        <div className="lg:col-span-6 space-y-6 rounded-3xl border border-white/10 bg-[#080e1a] p-6 sm:p-8 shadow-2xl">
          {/* Investment Amount */}
          {mode === 'sip' ? (
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <label className="text-xs font-semibold uppercase tracking-wider text-[#7183a0]">
                  Monthly SIP Amount
                </label>
                <div className="flex items-center rounded-lg border border-white/15 bg-black/40 px-3 py-1.5">
                  <span className="text-xs font-mono text-[#7183a0] mr-1">₹</span>
                  <input
                    type="number"
                    min={500}
                    max={1000000}
                    step={500}
                    value={monthlyAmount}
                    onChange={(e) => setMonthlyAmount(Math.max(500, Number(e.target.value) || 0))}
                    className="w-24 bg-transparent text-right font-mono text-sm font-bold text-white outline-none"
                  />
                </div>
              </div>
              <input
                type="range"
                min={500}
                max={200000}
                step={500}
                value={monthlyAmount}
                onChange={(e) => setMonthlyAmount(Number(e.target.value))}
                className="w-full accent-[#00FF9D] cursor-pointer"
              />
              <div className="flex justify-between text-[10px] font-mono text-[#7183a0]">
                <span>₹500</span>
                <span>₹50,000</span>
                <span>₹2,00,000+</span>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <label className="text-xs font-semibold uppercase tracking-wider text-[#7183a0]">
                  Lumpsum Investment
                </label>
                <div className="flex items-center rounded-lg border border-white/15 bg-black/40 px-3 py-1.5">
                  <span className="text-xs font-mono text-[#7183a0] mr-1">₹</span>
                  <input
                    type="number"
                    min={5000}
                    max={10000000}
                    step={5000}
                    value={lumpsumAmount}
                    onChange={(e) => setLumpsumAmount(Math.max(1000, Number(e.target.value) || 0))}
                    className="w-28 bg-transparent text-right font-mono text-sm font-bold text-white outline-none"
                  />
                </div>
              </div>
              <input
                type="range"
                min={5000}
                max={2500000}
                step={5000}
                value={lumpsumAmount}
                onChange={(e) => setLumpsumAmount(Number(e.target.value))}
                className="w-full accent-[#66a3ff] cursor-pointer"
              />
              <div className="flex justify-between text-[10px] font-mono text-[#7183a0]">
                <span>₹5,000</span>
                <span>₹10 Lakh</span>
                <span>₹25 Lakh+</span>
              </div>
            </div>
          )}

          {/* Expected Return Rate */}
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <label className="text-xs font-semibold uppercase tracking-wider text-[#7183a0]">
                Expected Annual Return (CAGR)
              </label>
              <div className="flex items-center rounded-lg border border-white/15 bg-black/40 px-3 py-1.5">
                <input
                  type="number"
                  min={1}
                  max={35}
                  step={0.5}
                  value={annualReturn}
                  onChange={(e) => setAnnualReturn(Math.max(1, Number(e.target.value) || 0))}
                  className="w-14 bg-transparent text-right font-mono text-sm font-bold text-white outline-none"
                />
                <span className="text-xs font-mono text-[#7183a0] ml-1">%</span>
              </div>
            </div>
            <input
              type="range"
              min={5}
              max={30}
              step={0.5}
              value={annualReturn}
              onChange={(e) => setAnnualReturn(Number(e.target.value))}
              className="w-full accent-[#00FF9D] cursor-pointer"
            />

            {/* Quick Historical Category Presets */}
            <div className="pt-1">
              <span className="text-[10px] text-[#7183a0] block mb-2 font-mono">SEBI Category Historical Baselines:</span>
              <div className="flex flex-wrap gap-1.5">
                {CATEGORY_BENCHMARKS.map((cat) => (
                  <button
                    key={cat.category}
                    onClick={() => setAnnualReturn(cat.rate)}
                    className={`text-[10px] px-2.5 py-1 rounded-lg border transition-all ${
                      annualReturn === cat.rate
                        ? 'border-[#00FF9D]/60 bg-[#00FF9D]/15 text-[#00FF9D] font-bold'
                        : 'border-white/10 bg-white/[0.02] text-[#aebed6] hover:bg-white/5'
                    }`}
                  >
                    {cat.category} ({cat.rate}%)
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Investment Time Horizon */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <label className="text-xs font-semibold uppercase tracking-wider text-[#7183a0]">
                Investment Duration
              </label>
              <div className="flex items-center rounded-lg border border-white/15 bg-black/40 px-3 py-1.5">
                <input
                  type="number"
                  min={1}
                  max={40}
                  value={years}
                  onChange={(e) => setYears(Math.max(1, Number(e.target.value) || 1))}
                  className="w-12 bg-transparent text-right font-mono text-sm font-bold text-white outline-none"
                />
                <span className="text-xs font-mono text-[#7183a0] ml-1">years</span>
              </div>
            </div>
            <input
              type="range"
              min={1}
              max={35}
              step={1}
              value={years}
              onChange={(e) => setYears(Number(e.target.value))}
              className="w-full accent-[#00FF9D] cursor-pointer"
            />
            <div className="flex justify-between text-[10px] font-mono text-[#7183a0]">
              <span>1 Year</span>
              <span>15 Years</span>
              <span>35 Years</span>
            </div>
          </div>

          {/* Step-Up SIP (SIP Mode only) */}
          {mode === 'sip' && (
            <div className="space-y-2 pt-2 border-t border-white/5">
              <div className="flex justify-between items-center">
                <div>
                  <label className="text-xs font-semibold text-white flex items-center gap-1.5">
                    <span>Annual Step-Up Increment</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#00FF9D]/10 text-[#00FF9D]">
                      Wealth Accelerator
                    </span>
                  </label>
                  <p className="text-[11px] text-[#7183a0]">Increase monthly SIP every 12 months with salary increments</p>
                </div>
                <div className="flex items-center rounded-lg border border-white/15 bg-black/40 px-3 py-1.5">
                  <span className="font-mono text-sm font-bold text-white">{stepUpPercent}%</span>
                </div>
              </div>
              <div className="flex gap-2 pt-1">
                {[0, 5, 10, 15, 20].map((rate) => (
                  <button
                    key={rate}
                    onClick={() => setStepUpPercent(rate)}
                    className={`flex-1 py-1.5 rounded-lg border text-xs font-semibold transition-colors ${
                      stepUpPercent === rate
                        ? 'border-[#00FF9D]/60 bg-[#00FF9D]/15 text-[#00FF9D]'
                        : 'border-white/10 bg-white/[0.02] text-[#7183a0] hover:text-white'
                    }`}
                  >
                    {rate === 0 ? 'None' : `+${rate}%`}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Inflation Toggle */}
          <div className="flex items-center justify-between pt-2 border-t border-white/5">
            <div>
              <span className="text-xs font-semibold text-white">Adjust for Inflation</span>
              <p className="text-[11px] text-[#7183a0]">View purchasing power in today's money (assumes 6% CPI)</p>
            </div>
            <button
              onClick={() => setAdjustInflation(!adjustInflation)}
              className={`w-11 h-6 rounded-full transition-colors relative ${
                adjustInflation ? 'bg-[#00FF9D]' : 'bg-white/15'
              }`}
            >
              <div
                className={`w-4 h-4 rounded-full bg-black transition-transform absolute top-1 ${
                  adjustInflation ? 'left-6' : 'left-1'
                }`}
              />
            </button>
          </div>
        </div>

        {/* ─── Right Column: Result Card & Wealth Visualizer ──────────────────── */}
        <div className="lg:col-span-6 space-y-6">
          <div className="rounded-3xl border border-white/10 bg-gradient-to-br from-[#0c162b] via-[#080e1c] to-[#040710] p-6 sm:p-8 shadow-2xl space-y-6">
            <div className="flex justify-between items-center border-b border-white/10 pb-4">
              <span className="text-xs font-mono font-bold uppercase tracking-widest text-[#7183a0]">
                Estimated Wealth at {years} Years
              </span>
              <span className="text-xs font-mono font-semibold px-2.5 py-0.5 rounded-full bg-[#00FF9D]/10 text-[#00FF9D] border border-[#00FF9D]/20">
                {calculation.gainShare}% Gains
              </span>
            </div>

            {/* Big Headline Future Value */}
            <div className="space-y-1">
              <p className="text-4xl sm:text-5xl font-extrabold text-white tracking-tight">
                {formatInr(calculation.futureValue)}
              </p>
              <p className="text-xs text-[#7183a0] font-mono">
                Total expected corpus at {annualReturn}% CAGR
              </p>
            </div>

            {/* Inflation callout */}
            {adjustInflation && (
              <div className="p-3.5 rounded-xl border border-amber-500/20 bg-amber-500/5 text-xs text-amber-200 flex items-center justify-between">
                <span>Real Purchasing Power (at 6% inflation):</span>
                <strong className="font-mono text-sm text-white">{formatInr(calculation.inflationAdjustedFV)}</strong>
              </div>
            )}

            {/* Invested vs Gains Split Bar */}
            <div className="space-y-2">
              <div className="h-4 w-full bg-white/5 rounded-full overflow-hidden flex">
                <div
                  className="h-full bg-white/20 transition-all duration-500"
                  style={{
                    width: `${Math.min(100, Math.max(0, (calculation.totalInvested / calculation.futureValue) * 100))}%`,
                  }}
                  title="Total Invested"
                />
                <div
                  className="h-full bg-[#00FF9D] transition-all duration-500"
                  style={{
                    width: `${Math.min(100, Math.max(0, (calculation.gains / calculation.futureValue) * 100))}%`,
                  }}
                  title="Compounded Returns"
                />
              </div>
              <div className="flex justify-between text-xs font-mono">
                <span className="text-[#aebed6] flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-sm bg-white/30" />
                  Invested: <strong className="text-white">{formatInr(calculation.totalInvested)}</strong>
                </span>
                <span className="text-[#00FF9D] flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-sm bg-[#00FF9D]" />
                  Gains: <strong className="text-white">{formatInr(calculation.gains)}</strong>
                </span>
              </div>
            </div>

            {/* Detailed Metric Grid */}
            <div className="grid grid-cols-2 gap-3 pt-2">
              <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4 text-center">
                <p className="text-[10px] font-bold uppercase tracking-wider text-[#7183a0] mb-1">Total Principal</p>
                <p className="text-lg font-bold text-white">{formatInr(calculation.totalInvested)}</p>
              </div>
              <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4 text-center">
                <p className="text-[10px] font-bold uppercase tracking-wider text-[#7183a0] mb-1">Wealth Multiplier</p>
                <p className="text-lg font-bold text-[#00FF9D]">
                  {calculation.totalInvested > 0 ? (calculation.futureValue / calculation.totalInvested).toFixed(1) : 1}x
                </p>
              </div>
            </div>

            {/* Compounding Visual Spline Graph */}
            <div className="rounded-2xl border border-white/10 bg-black/30 p-4 space-y-2">
              <div className="flex justify-between items-center text-[11px] font-mono text-[#7183a0]">
                <span>Compounding Trajectory ({years} Years)</span>
                <span className="text-[#00FF9D] font-bold">Exponential Corpus Growth</span>
              </div>
              <div className="relative w-full h-32 pt-2">
                <svg viewBox="0 0 400 130" className="w-full h-full overflow-visible">
                  <defs>
                    <linearGradient id="wealthGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#00FF9D" stopOpacity="0.25" />
                      <stop offset="100%" stopColor="#00FF9D" stopOpacity="0.0" />
                    </linearGradient>
                  </defs>

                  {/* Grid Lines */}
                  <line x1="30" y1="110" x2="380" y2="110" stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />
                  <line x1="30" y1="65" x2="380" y2="65" stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />
                  <line x1="30" y1="20" x2="380" y2="20" stroke="rgba(255,255,255,0.08)" strokeDasharray="3 3" />

                  {/* Invested Principal Line */}
                  <line
                    x1="30"
                    y1="110"
                    x2="380"
                    y2={110 - Math.min(90, (calculation.totalInvested / (calculation.futureValue || 1)) * 90)}
                    stroke="rgba(255,255,255,0.3)"
                    strokeWidth="2"
                    strokeDasharray="4 4"
                  />

                  {/* Exponential Wealth Spline Area & Stroke */}
                  {calculation.yearlyBreakdown.length > 0 && (() => {
                    const points = calculation.yearlyBreakdown.map((item, idx) => {
                      const x = 30 + (idx / (calculation.yearlyBreakdown.length - 1 || 1)) * 350;
                      const y = 110 - (item.wealth / (calculation.futureValue || 1)) * 90;
                      return `${x.toFixed(1)},${y.toFixed(1)}`;
                    });
                    const dArea = `M 30,110 L ${points.join(' L ')} L 380,110 Z`;
                    const dLine = `M ${points.join(' L ')}`;
                    return (
                      <>
                        <path d={dArea} fill="url(#wealthGrad)" />
                        <path d={dLine} fill="none" stroke="#00FF9D" strokeWidth="2.5" />
                        <circle cx="380" cy={110 - 90} r="4" fill="#00FF9D" className="animate-pulse" />
                      </>
                    );
                  })()}

                  {/* Labels */}
                  <text x="30" y="125" fill="#7183a0" fontSize="9" fontFamily="monospace">Yr 1</text>
                  <text x="205" y="125" textAnchor="middle" fill="#7183a0" fontSize="9" fontFamily="monospace">Yr {Math.round(years / 2)}</text>
                  <text x="380" y="125" textAnchor="end" fill="#00FF9D" fontSize="9" fontFamily="monospace" fontWeight="bold">Yr {years}</text>
                </svg>
              </div>
            </div>

            {/* Direct Link to Mutual Funds Screener & 1-Click Share Button */}
            <div className="pt-2 flex gap-3">
              <Link
                href="/mutual-funds"
                className="flex-1 py-3.5 rounded-xl bg-[#00FF9D] text-black font-bold text-xs hover:bg-[#00FF9D]/90 transition-colors shadow-lg shadow-[#00FF9D]/20 flex items-center justify-center gap-2"
              >
                <span>Find {annualReturn}%+ Funds</span>
                <ArrowRight className="w-4 h-4" />
              </Link>

              <button
                onClick={() => {
                  if (typeof window !== 'undefined') {
                    const shareUrl = `${window.location.origin}/tools/sip-calculator?amount=${monthlyAmount}&cagr=${annualReturn}&years=${years}`;
                    navigator.clipboard.writeText(shareUrl);
                    alert('Projection link copied to clipboard!');
                  }
                }}
                className="px-4 py-3.5 rounded-xl border border-white/15 bg-white/5 hover:bg-white/10 text-white text-xs font-semibold transition-colors flex items-center gap-1.5"
                title="Share this SIP projection"
              >
                <span>Share</span>
              </button>
            </div>
          </div>

          {/* Interactive Year-by-Year Schedule Toggle */}
          <div className="rounded-2xl border border-white/10 bg-[#080e1a] p-5">
            <button
              onClick={() => setShowSchedule(!showSchedule)}
              className="w-full flex items-center justify-between text-xs font-bold text-white hover:text-[#00FF9D] transition-colors"
            >
              <span>View Year-by-Year Wealth Accumulation Schedule</span>
              {showSchedule ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>

            {showSchedule && (
              <div className="mt-4 overflow-x-auto max-h-60 overflow-y-auto">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-white/10 text-[#7183a0] font-mono text-[10px]">
                    <tr>
                      <th className="py-2 px-2">Year</th>
                      <th className="py-2 px-2 text-right">Invested</th>
                      <th className="py-2 px-2 text-right">Total Invested</th>
                      <th className="py-2 px-2 text-right text-[#00FF9D]">Estimated Corpus</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 font-mono">
                    {calculation.yearlyBreakdown.map((row) => (
                      <tr key={row.year} className="hover:bg-white/[0.02]">
                        <td className="py-2 px-2 text-white">Year {row.year}</td>
                        <td className="py-2 px-2 text-right text-[#7183a0]">{formatInr(row.invested)}</td>
                        <td className="py-2 px-2 text-right text-[#aebed6]">{formatInr(row.totalInvested)}</td>
                        <td className="py-2 px-2 text-right font-bold text-white">{formatInr(row.wealth)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
