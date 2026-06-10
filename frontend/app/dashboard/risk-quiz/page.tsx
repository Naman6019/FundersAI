'use client';

import { Suspense, useMemo, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, ArrowRight, MessageSquareText, RotateCcw, ShieldQuestion } from 'lucide-react';
import AuthGate from '@/components/auth/AuthGate';

type QuizOption = {
  label: string;
  score: number;
};

type QuizQuestion = {
  prompt: string;
  options: QuizOption[];
};

const QUESTIONS: QuizQuestion[] = [
  {
    prompt: 'How long can this money stay invested before you may need it?',
    options: [
      { label: 'Less than 2 years', score: 1 },
      { label: '2 to 3 years', score: 2 },
      { label: '3 to 5 years', score: 3 },
      { label: '5 to 10 years', score: 4 },
      { label: 'More than 10 years', score: 5 },
    ],
  },
  {
    prompt: 'Which age band are you in?',
    options: [
      { label: '51 years or above', score: 1 },
      { label: '36 to 50 years', score: 3 },
      { label: '25 to 35 years', score: 4 },
      { label: 'Below 25 years', score: 5 },
    ],
  },
  {
    prompt: 'How comfortable are you with market-linked products?',
    options: [
      { label: 'I am new and prefer simple, stable products', score: 1 },
      { label: 'I understand basic diversification and risk', score: 2 },
      { label: 'I have invested before and understand volatility', score: 3 },
      { label: 'I actively compare strategies and market cycles', score: 5 },
    ],
  },
  {
    prompt: 'How stable are your income sources?',
    options: [
      { label: 'Very unstable', score: 1 },
      { label: 'Somewhat unstable', score: 2 },
      { label: 'Mostly stable', score: 3 },
      { label: 'Very stable', score: 4 },
    ],
  },
  {
    prompt: 'Which outcome range feels acceptable for a long-term investment?',
    options: [
      { label: 'Avoid loss even if return potential is low', score: 1 },
      { label: 'Small loss is acceptable for modest upside', score: 2 },
      { label: 'Moderate loss is acceptable for higher upside', score: 3 },
      { label: 'Large interim loss is acceptable for long-term growth', score: 5 },
    ],
  },
  {
    prompt: 'If the portfolio falls 20% after investing, what would you most likely do?',
    options: [
      { label: 'Exit immediately to preserve capital', score: 1 },
      { label: 'Move part of it to safer assets', score: 2 },
      { label: 'Wait and review the data before acting', score: 3 },
      { label: 'Stay invested because volatility is expected', score: 4 },
      { label: 'Add more if the original thesis still holds', score: 5 },
    ],
  },
  {
    prompt: 'What balance do you prefer between return variability and stability?',
    options: [
      { label: 'Stable returns matter most', score: 1 },
      { label: 'Mostly stable with limited variability', score: 2 },
      { label: 'Some variability for better return potential', score: 3 },
      { label: 'High variability is fine for higher long-term potential', score: 5 },
    ],
  },
  {
    prompt: 'Which best describes your preferred risk range?',
    options: [
      { label: 'Worst year near 0%, best year around 10-15%', score: 1 },
      { label: 'Worst year around -5%, best year around 20%', score: 2 },
      { label: 'Worst year around -10%, best year around 25%', score: 3 },
      { label: 'Worst year below -15%, best year above 30%', score: 5 },
    ],
  },
];

function profileForScore(score: number) {
  if (score <= 16) {
    return {
      name: 'Conservative',
      growth: 15,
      body: 'You appear more focused on capital protection and lower volatility. Defensive assets may need a larger role than pure growth assets.',
      chatFocus: 'conservative risk profile, lower volatility, capital protection, and suitable mutual fund research areas',
    };
  }
  if (score <= 28) {
    return {
      name: 'Moderate',
      growth: 45,
      body: 'You appear comfortable with a mix of income and growth assets, with controlled exposure to market volatility.',
      chatFocus: 'moderate risk profile, balanced allocation, return stability, and mutual fund category comparison',
    };
  }
  return {
    name: 'Aggressive',
    growth: 75,
    body: 'You appear comfortable with higher volatility for long-term growth, but concentration and drawdown risk still need monitoring.',
    chatFocus: 'aggressive risk profile, growth allocation, volatility tolerance, and risk controls for mutual funds',
  };
}

function RiskQuizContent() {
  const [answers, setAnswers] = useState<Record<number, number>>({});
  const answeredCount = Object.keys(answers).length;
  const isComplete = answeredCount === QUESTIONS.length;
  const totalScore = useMemo(() => Object.values(answers).reduce((sum, score) => sum + score, 0), [answers]);
  const profile = profileForScore(totalScore);
  const defensive = 100 - profile.growth;
  const chatQuery = encodeURIComponent(
    `My risk quiz result is ${profile.name} with score ${totalScore}/${QUESTIONS.length * 5}. Explain what this means for mutual fund research, category mix, and risk checks. Keep it research-only, not advice.`,
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
              <h1 className="mt-3 font-serif text-3xl font-semibold text-white sm:text-4xl">Risk Quiz</h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
                Answer a short set of questions to estimate your broad risk profile. The result is only a research input.
              </p>
            </div>
            <ShieldQuestion className="h-8 w-8 text-[#66a3ff]" />
          </div>

          <div className="mt-8 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
            <div className="space-y-4">
              {QUESTIONS.map((question, questionIndex) => (
                <div key={question.prompt} className="rounded-xl border border-white/10 bg-[#080d1a] p-4">
                  <div className="flex gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-[#66a3ff]/25 bg-[#66a3ff]/10 text-xs font-semibold text-[#66a3ff]">
                      {questionIndex + 1}
                    </div>
                    <div className="min-w-0 flex-1">
                      <h2 className="text-sm font-semibold text-white">{question.prompt}</h2>
                      <div className="mt-3 grid gap-2">
                        {question.options.map((option) => {
                          const selected = answers[questionIndex] === option.score;
                          return (
                            <button
                              key={option.label}
                              type="button"
                              onClick={() => setAnswers((current) => ({ ...current, [questionIndex]: option.score }))}
                              className={`rounded-lg border px-3 py-2 text-left text-sm transition ${
                                selected
                                  ? 'border-[#66a3ff] bg-[#66a3ff]/15 text-white'
                                  : 'border-white/10 bg-white/[0.03] text-slate-300 hover:border-[#66a3ff]/40 hover:bg-[#66a3ff]/10'
                              }`}
                            >
                              {option.label}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <aside className="h-fit rounded-xl border border-[#66a3ff]/20 bg-[#0d1728] p-5 lg:sticky lg:top-6">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Progress</p>
                  <p className="mt-1 text-sm font-semibold text-white">{answeredCount}/{QUESTIONS.length} answered</p>
                </div>
                <button
                  type="button"
                  onClick={() => setAnswers({})}
                  className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-xs font-semibold text-slate-300 transition hover:border-[#66a3ff]/40 hover:text-white"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                  Reset
                </button>
              </div>

              <div className="mt-5 h-2 overflow-hidden rounded-full bg-slate-800">
                <div className="h-full rounded-full bg-[#66a3ff]" style={{ width: `${(answeredCount / QUESTIONS.length) * 100}%` }} />
              </div>

              {isComplete ? (
                <div className="mt-6">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Your risk profile</p>
                  <h2 className="mt-2 text-3xl font-semibold text-white">{profile.name}</h2>
                  <p className="mt-3 text-sm leading-6 text-slate-300">{profile.body}</p>

                  <div className="mt-5 space-y-3">
                    <div>
                      <div className="mb-1 flex justify-between text-xs text-slate-400">
                        <span>Growth assets</span>
                        <span>{profile.growth}%</span>
                      </div>
                      <div className="h-2 rounded-full bg-slate-800">
                        <div className="h-full rounded-full bg-[#66a3ff]" style={{ width: `${profile.growth}%` }} />
                      </div>
                    </div>
                    <div>
                      <div className="mb-1 flex justify-between text-xs text-slate-400">
                        <span>Defensive assets</span>
                        <span>{defensive}%</span>
                      </div>
                      <div className="h-2 rounded-full bg-slate-800">
                        <div className="h-full rounded-full bg-emerald-300" style={{ width: `${defensive}%` }} />
                      </div>
                    </div>
                  </div>

                  <div className="mt-5 rounded-lg border border-amber-300/20 bg-amber-300/[0.06] p-3 text-xs leading-5 text-amber-50/80">
                    This is an indicative profile, not a suitability recommendation. Use it as context for research.
                  </div>

                  <Link
                    href={`/dashboard?query=${chatQuery}&asset_type=mutual_fund`}
                    className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[#66a3ff] px-4 py-3 text-sm font-semibold text-slate-950 transition hover:bg-[#8bbcff]"
                  >
                    Discuss this in chat
                    <MessageSquareText className="h-4 w-4" />
                  </Link>
                </div>
              ) : (
                <div className="mt-6 rounded-lg border border-white/10 bg-white/[0.03] p-4 text-sm leading-6 text-slate-300">
                  Finish all questions to see your profile and open the result in chat.
                </div>
              )}

              <Link href="/dashboard/sip-calculator" className="mt-4 inline-flex items-center gap-2 text-sm text-slate-400 transition hover:text-[#66a3ff]">
                Open SIP Calculator
                <ArrowRight className="h-4 w-4" />
              </Link>
            </aside>
          </div>
        </section>
      </div>
    </main>
  );
}

export default function RiskQuizPage() {
  return (
    <Suspense fallback={null}>
      <AuthGate>
        <RiskQuizContent />
      </AuthGate>
    </Suspense>
  );
}
