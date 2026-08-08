"use client";

import React from "react";
import { TrendingUp, ShieldAlert, Award, Percent, Activity } from "lucide-react";

export interface SignalChipData {
  type: "alpha" | "drawdown" | "expense" | "sharpe" | "beta";
  label: string;
  value: string;
  winner: string;
  isPositive?: boolean;
}

interface ExplainableSignalChipsProps {
  signals?: SignalChipData[];
}

export function ExplainableSignalChips({ signals }: ExplainableSignalChipsProps) {
  const defaultSignals: SignalChipData[] = [
    {
      type: "alpha",
      label: "Alpha Advantage",
      value: "+2.41% vs NIFTY 500",
      winner: "Parag Parikh Flexi Cap",
      isPositive: true,
    },
    {
      type: "drawdown",
      label: "Lower Drawdown Protection",
      value: "-14.2% Max Drawdown",
      winner: "Parag Parikh Flexi Cap",
      isPositive: true,
    },
    {
      type: "expense",
      label: "Lower Expense Ratio",
      value: "0.62% Direct TER",
      winner: "HDFC Flexi Cap",
      isPositive: true,
    },
    {
      type: "sharpe",
      label: "Higher Sharpe Ratio",
      value: "1.42 Risk-Adjusted",
      winner: "Parag Parikh Flexi Cap",
      isPositive: true,
    },
  ];

  const activeSignals = signals || defaultSignals;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-mono uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
          <Award className="w-3.5 h-3.5 text-emerald-400" />
          <span>Explainable Comparison Signals</span>
        </h4>
        <span className="text-[10px] text-slate-500 font-mono">Deterministic Math</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {activeSignals.map((signal, idx) => (
          <div
            key={idx}
            className="p-3 rounded-lg bg-slate-900/70 border border-white/10 hover:border-emerald-500/40 transition-all flex items-start justify-between gap-3 group"
          >
            <div className="space-y-1">
              <div className="flex items-center gap-1.5">
                {signal.type === "alpha" && <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />}
                {signal.type === "drawdown" && <ShieldAlert className="w-3.5 h-3.5 text-cyan-400" />}
                {signal.type === "expense" && <Percent className="w-3.5 h-3.5 text-amber-400" />}
                {signal.type === "sharpe" && <Activity className="w-3.5 h-3.5 text-emerald-400" />}

                <span className="text-xs font-semibold text-white group-hover:text-emerald-300 transition-colors">
                  {signal.label}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-sans">
                Outperformed by <span className="text-slate-200 font-medium">{signal.winner}</span>
              </p>
            </div>

            <div className="text-right">
              <span className="inline-block px-2 py-0.5 rounded font-mono text-xs font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-800/40">
                {signal.value}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
