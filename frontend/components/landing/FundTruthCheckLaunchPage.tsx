'use client';

import { useState } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import {
  ArrowRight,
  BadgeCheck,
  BookOpenCheck,
  CheckCircle2,
  CircleAlert,
  ExternalLink,
  FileSearch,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';

type PreviewState = {
  id: string;
  input: string;
  eyebrow: string;
  title: string;
  detail: string;
  evidence: string;
  tone: 'green' | 'amber' | 'blue';
};

const PREVIEWS: PreviewState[] = [
  {
    id: 'prediction',
    input: 'Will this fund outperform next year?',
    eyebrow: 'Prediction detected',
    title: 'No historical number is turned into a forecast.',
    detail: 'A future return cannot be verified from dated historical evidence. The checker stops instead of reframing past performance as a prediction.',
    evidence: 'Result: no factual verdict · no forecast inferred',
    tone: 'amber',
  },
  {
    id: 'definition',
    input: 'Is this fund safer?',
    eyebrow: 'Definition needed',
    title: '“Safer” needs a measurable meaning first.',
    detail: 'The checker asks for a defined measure—such as volatility or drawdown—before it compares anything.',
    evidence: 'Result: clarification requested · no vague verdict',
    tone: 'blue',
  },
  {
    id: 'evidence',
    input: 'Does this fund have a lower expense ratio?',
    eyebrow: 'Evidence path',
    title: 'A claim is only as current as its dated source.',
    detail: 'The live checker resolves the exact scheme, metric and period, then keeps the historical result separate from its freshness.',
    evidence: 'Required: exact scheme · official source · matching date',
    tone: 'green',
  },
];

const toneStyles: Record<PreviewState['tone'], { border: string; badge: string; icon: string }> = {
  green: {
    border: 'border-emerald-400/25',
    badge: 'bg-emerald-400/10 text-emerald-200',
    icon: 'text-emerald-300',
  },
  amber: {
    border: 'border-amber-300/25',
    badge: 'bg-amber-300/10 text-amber-100',
    icon: 'text-amber-200',
  },
  blue: {
    border: 'border-sky-300/25',
    badge: 'bg-sky-300/10 text-sky-100',
    icon: 'text-sky-200',
  },
};

export default function FundTruthCheckLaunchPage() {
  const [selectedId, setSelectedId] = useState(PREVIEWS[0].id);
  const selected = PREVIEWS.find((preview) => preview.id === selectedId) || PREVIEWS[0];
  const selectedTone = toneStyles[selected.tone];

  return (
    <div className="min-h-screen bg-[#05070f] text-slate-100">
      <EcosystemHeader currentApp="tools" />

      <main>
        <section className="relative overflow-hidden px-4 pb-20 pt-16 sm:px-6 sm:pt-24 lg:px-8">
          <div className="pointer-events-none absolute inset-x-0 top-0 h-[680px] bg-[radial-gradient(circle_at_50%_20%,rgba(0,255,157,0.12),transparent_42%),radial-gradient(circle_at_15%_55%,rgba(56,189,248,0.10),transparent_32%)]" />
          <div className="relative mx-auto grid max-w-7xl gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(430px,0.9fr)] lg:items-center">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1.5 font-mono text-[11px] font-semibold uppercase tracking-[0.15em] text-emerald-200">
                <Sparkles className="size-3.5" />
                Fund Truth Check · private beta
              </div>
              <h1 className="mt-6 max-w-3xl font-serif-display text-4xl font-bold leading-[1.02] tracking-tight text-white sm:text-6xl">
                Turn a fund claim into a trail of proof.
              </h1>
              <p className="mt-6 max-w-2xl text-base leading-8 text-slate-300 sm:text-lg">
                Fund Truth Check breaks a mutual-fund claim into its exact scheme, metric, date, source and calculation—then shows where the evidence stops.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <a
                  href="#preview"
                  className="inline-flex items-center gap-2 rounded-full bg-[#00ff9d] px-5 py-3 text-sm font-bold text-[#04120c] transition hover:bg-[#66ffba]"
                >
                  See the preview <ArrowRight className="size-4" />
                </a>
                <Link
                  href="/contact"
                  className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.03] px-5 py-3 text-sm font-semibold text-white transition hover:border-emerald-300/40 hover:bg-white/[0.06]"
                >
                  Request beta access <ExternalLink className="size-4" />
                </Link>
              </div>
              <p className="mt-5 max-w-xl text-xs leading-5 text-slate-400">
                The public preview below demonstrates the product rules. Live, arbitrary-claim checks remain in private beta while source review is completed.
              </p>
            </div>

            <div className="relative overflow-hidden rounded-[28px] border border-white/10 bg-[#07111d] shadow-[0_32px_110px_rgba(0,0,0,0.45)]">
              <Image
                src="/product-hunt/fund-truth-check-evidence-trail.png"
                alt="Conceptual path from dated evidence to a verified decision and an uncertainty boundary"
                width={1774}
                height={887}
                priority
                className="h-auto w-full opacity-90"
              />
              <div className="absolute inset-x-0 bottom-0 border-t border-white/10 bg-[#07111d]/90 p-4 backdrop-blur">
                <div className="flex items-center gap-3 text-sm text-slate-200">
                  <ShieldCheck className="size-5 text-emerald-300" />
                  <span>Evidence is a boundary, not a decoration.</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section id="preview" className="scroll-mt-24 border-y border-white/10 bg-[#08111d] px-4 py-20 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-6xl">
            <div className="max-w-3xl">
              <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-emerald-300">Interactive product preview</p>
              <h2 className="mt-3 font-serif-display text-3xl font-bold text-white sm:text-5xl">The useful answer is sometimes a stop sign.</h2>
              <p className="mt-4 text-sm leading-7 text-slate-300 sm:text-base">
                Choose a sample claim to see the kind of boundary the live checker makes visible. This preview does not submit or evaluate a live claim.
              </p>
            </div>

            <div className="mt-10 grid gap-6 lg:grid-cols-[0.78fr_1.22fr]">
              <div className="space-y-3" role="list" aria-label="Preview claims">
                {PREVIEWS.map((preview) => {
                  const active = preview.id === selected.id;
                  return (
                    <button
                      key={preview.id}
                      type="button"
                      onClick={() => setSelectedId(preview.id)}
                      aria-pressed={active}
                      className={`w-full rounded-2xl border p-4 text-left transition ${active ? 'border-emerald-300/50 bg-emerald-300/[0.08]' : 'border-white/10 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.04]'}`}
                    >
                      <span className="font-mono text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">Sample claim</span>
                      <span className="mt-2 block text-sm font-medium leading-6 text-white">{preview.input}</span>
                    </button>
                  );
                })}
              </div>

              <article className={`rounded-3xl border ${selectedTone.border} bg-[#050b14] p-6 shadow-2xl sm:p-8`} aria-live="polite">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <span className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold ${selectedTone.badge}`}>
                    <CircleAlert className="size-3.5" /> {selected.eyebrow}
                  </span>
                  <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-slate-500">Preview only</span>
                </div>
                <p className="mt-7 rounded-xl border border-white/10 bg-white/[0.025] px-4 py-3 font-mono text-sm leading-6 text-slate-200">“{selected.input}”</p>
                <div className="mt-7 flex gap-4">
                  <BadgeCheck className={`mt-0.5 size-6 shrink-0 ${selectedTone.icon}`} />
                  <div>
                    <h3 className="text-xl font-semibold text-white sm:text-2xl">{selected.title}</h3>
                    <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-300">{selected.detail}</p>
                  </div>
                </div>
                <div className="mt-8 rounded-xl border border-white/10 bg-white/[0.025] p-4">
                  <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-400">Check boundary</p>
                  <p className="mt-2 text-sm font-medium text-slate-100">{selected.evidence}</p>
                </div>
              </article>
            </div>
          </div>
        </section>

        <section className="px-4 py-20 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-6xl">
            <div className="grid gap-6 md:grid-cols-3">
              {[
                {
                  title: 'Resolve the exact fund',
                  description: 'Names are not enough. The checker works from a scheme identity before it evaluates a claim.',
                  Icon: FileSearch,
                },
                {
                  title: 'Show the dated source',
                  description: 'A number includes its evidence path and as-of date, so a historical fact is not presented as current.',
                  Icon: BookOpenCheck,
                },
                {
                  title: 'Abstain when needed',
                  description: 'Predictions, advice, vague terms and unmatched evidence receive a clear limit—not a confident guess.',
                  Icon: CheckCircle2,
                },
              ].map(({ title, description, Icon }) => (
                <article key={title} className="rounded-3xl border border-white/10 bg-white/[0.025] p-6">
                  <span className="inline-flex rounded-xl border border-emerald-300/20 bg-emerald-300/10 p-3 text-emerald-200"><Icon className="size-5" /></span>
                  <h3 className="mt-5 text-lg font-semibold text-white">{title}</h3>
                  <p className="mt-2 text-sm leading-7 text-slate-400">{description}</p>
                </article>
              ))}
            </div>

            <div className="mt-12 rounded-3xl border border-white/10 bg-gradient-to-br from-emerald-300/[0.08] via-transparent to-sky-300/[0.08] p-8 text-center sm:p-12">
              <p className="font-mono text-xs font-semibold uppercase tracking-[0.18em] text-emerald-200">FundersAI</p>
              <h2 className="mt-4 font-serif-display text-3xl font-bold text-white sm:text-4xl">Research only. Evidence first.</h2>
              <p className="mx-auto mt-4 max-w-2xl text-sm leading-7 text-slate-300">
                Fund Truth Check is designed to clarify evidence, not to make a personal investment decision for you. Verify linked sources before relying on any result.
              </p>
              <div className="mt-7 flex flex-wrap justify-center gap-3">
                <Link href="/tools" className="inline-flex items-center gap-2 rounded-full bg-white/[0.06] px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/[0.10]">
                  Explore research tools <ArrowRight className="size-4" />
                </Link>
                <Link href="/methodology/guardrails" className="inline-flex items-center gap-2 rounded-full border border-white/15 px-5 py-3 text-sm font-semibold text-white transition hover:border-emerald-300/40">
                  Read the guardrails <ShieldCheck className="size-4" />
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>

      <PublicFooter />
    </div>
  );
}
