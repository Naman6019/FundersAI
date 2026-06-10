'use client';

import { Suspense, useMemo, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, Calculator, MessageSquareText } from 'lucide-react';
import AuthGate from '@/components/auth/AuthGate';

function formatInr(value: number) {
  return `INR ${Math.round(value).toLocaleString('en-IN')}`;
}

function sipFutureValue(monthlyInvestment: number, annualReturn: number, years: number) {
  const months = Math.max(1, Math.round(years * 12));
  const monthlyRate = annualReturn / 100 / 12;
  if (monthlyRate === 0) return monthlyInvestment * months;
  return monthlyInvestment * (((1 + monthlyRate) ** months - 1) / monthlyRate) * (1 + monthlyRate);
}

function SipCalculatorContent() {
  const [monthlyInvestment, setMonthlyInvestment] = useState(10000);
  const [annualReturn, setAnnualReturn] = useState(12);
  const [years, setYears] = useState(10);

  const result = useMemo(() => {
    const futureValue = sipFutureValue(monthlyInvestment, annualReturn, years);
    const invested = monthlyInvestment * Math.round(years * 12);
    const gains = Math.max(futureValue - invested, 0);
    const gainShare = futureValue > 0 ? Math.min(100, Math.max(0, (gains / futureValue) * 100)) : 0;
    return { futureValue, invested, gains, gainShare };
  }, [annualReturn, monthlyInvestment, years]);

  const chatQuery = encodeURIComponent(
    `Explain this SIP estimate: monthly SIP ${formatInr(monthlyInvestment)}, expected annual return ${annualReturn}%, tenure ${years} years, invested ${formatInr(result.invested)}, estimated value ${formatInr(result.futureValue)}. Keep it research-only.`,
  );

  return (
    <main className="min-h-screen bg-[#05070f] px-4 py-6 text-slate-100 sm:px-8">
      <div className="mx-auto max-w-6xl">
        <Link href="/dashboard" className="inline-flex items-center gap-2 text-sm text-slate-400 transition hover:text-[#66a3ff]">
          <ArrowLeft className="h-4 w-4" />
          Back to dashboard
        </Link>

        <section className="mt-6 rounded-2xl border border-white/10 bg-[#0b1220] p-5 sm:p-8">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[#66a3ff]">Investor Tools</p>
              <h1 className="mt-3 font-serif text-3xl font-semibold text-white sm:text-4xl">SIP Calculator</h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
                Estimate future value from a fixed monthly SIP using monthly compounding. This is a planning estimate, not a return promise.
              </p>
            </div>
            <Calculator className="h-8 w-8 text-[#66a3ff]" />
          </div>

          <div className="mt-8 grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
            <div className="rounded-xl border border-white/10 bg-[#080d1a] p-5">
              <div className="space-y-6">
                <label className="block">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium text-slate-200">Monthly investment</span>
                    <input
                      type="number"
                      min={500}
                      step={500}
                      value={monthlyInvestment}
                      onChange={(event) => setMonthlyInvestment(Math.max(0, Number(event.target.value) || 0))}
                      className="w-36 rounded-lg border border-white/10 bg-slate-950 px-3 py-2 text-right font-mono text-sm text-white outline-none focus:border-[#66a3ff]"
                    />
                  </div>
                  <input
                    type="range"
                    min={500}
                    max={200000}
                    step={500}
                    value={monthlyInvestment}
                    onChange={(event) => setMonthlyInvestment(Number(event.target.value))}
                    className="mt-4 w-full accent-[#66a3ff]"
                  />
                </label>

                <label className="block">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium text-slate-200">Expected return rate</span>
                    <div className="flex w-36 items-center rounded-lg border border-white/10 bg-slate-950 px-3 py-2">
                      <input
                        type="number"
                        min={0}
                        max={30}
                        step={0.5}
                        value={annualReturn}
                        onChange={(event) => setAnnualReturn(Math.max(0, Number(event.target.value) || 0))}
                        className="w-full bg-transparent text-right font-mono text-sm text-white outline-none"
                      />
                      <span className="ml-1 text-slate-400">%</span>
                    </div>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={30}
                    step={0.5}
                    value={annualReturn}
                    onChange={(event) => setAnnualReturn(Number(event.target.value))}
                    className="mt-4 w-full accent-[#66a3ff]"
                  />
                </label>

                <label className="block">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-medium text-slate-200">Time period</span>
                    <div className="flex w-36 items-center rounded-lg border border-white/10 bg-slate-950 px-3 py-2">
                      <input
                        type="number"
                        min={1}
                        max={40}
                        value={years}
                        onChange={(event) => setYears(Math.max(1, Number(event.target.value) || 1))}
                        className="w-full bg-transparent text-right font-mono text-sm text-white outline-none"
                      />
                      <span className="ml-1 text-slate-400">yr</span>
                    </div>
                  </div>
                  <input
                    type="range"
                    min={1}
                    max={40}
                    value={years}
                    onChange={(event) => setYears(Number(event.target.value))}
                    className="mt-4 w-full accent-[#66a3ff]"
                  />
                </label>
              </div>
            </div>

            <div className="rounded-xl border border-[#66a3ff]/20 bg-[#0d1728] p-5">
              <div className="grid gap-5 sm:grid-cols-[180px_1fr] sm:items-center">
                <div
                  className="mx-auto h-44 w-44 rounded-full"
                  style={{ background: `conic-gradient(#66a3ff 0 ${result.gainShare}%, #22304a ${result.gainShare}% 100%)` }}
                  aria-label="Estimated returns chart"
                >
                  <div className="flex h-full w-full items-center justify-center rounded-full p-5">
                    <div className="flex h-28 w-28 flex-col items-center justify-center rounded-full bg-[#0d1728] text-center">
                      <span className="text-[11px] text-slate-400">Est. value</span>
                      <span className="mt-1 text-sm font-semibold text-white">{formatInr(result.futureValue)}</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.03] p-3">
                    <span className="text-sm text-slate-400">Invested amount</span>
                    <span className="font-mono text-sm text-white">{formatInr(result.invested)}</span>
                  </div>
                  <div className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.03] p-3">
                    <span className="text-sm text-slate-400">Estimated returns</span>
                    <span className="font-mono text-sm text-[#66a3ff]">{formatInr(result.gains)}</span>
                  </div>
                  <div className="flex items-center justify-between rounded-lg border border-white/10 bg-white/[0.03] p-3">
                    <span className="text-sm text-slate-400">Total value</span>
                    <span className="font-mono text-sm text-white">{formatInr(result.futureValue)}</span>
                  </div>
                </div>
              </div>

              <div className="mt-6 rounded-lg border border-amber-300/20 bg-amber-300/[0.06] p-3 text-xs leading-5 text-amber-50/80">
                Mutual fund investments are subject to market risks. This estimate assumes a constant annual return and monthly compounding.
              </div>

              <Link
                href={`/dashboard?query=${chatQuery}&asset_type=mutual_fund`}
                className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[#66a3ff] px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-[#8bbcff] sm:w-auto"
              >
                Discuss this in chat
                <MessageSquareText className="h-4 w-4" />
              </Link>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

export default function SipCalculatorPage() {
  return (
    <Suspense fallback={null}>
      <AuthGate>
        <SipCalculatorContent />
      </AuthGate>
    </Suspense>
  );
}
