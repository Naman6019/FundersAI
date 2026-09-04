import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { FlaskConical } from 'lucide-react';
import AuthGate from '@/components/auth/AuthGate';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PublicFooter from '@/components/layout/PublicFooter';
import Breadcrumbs from '@/components/navigation/Breadcrumbs';
import TruthCheckWorkbench from '@/components/truth-check/TruthCheckWorkbench';
import { isFundTruthCheckPrivateEnabled } from '@/lib/fundTruthCheckPrivate';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: 'Fund Truth Check — Private Review | FundersAI',
  description: 'Private review build for checking mutual-fund claims against dated official evidence.',
  robots: { index: false, follow: false, nocache: true },
};

export default function FundTruthCheckPage() {
  if (!isFundTruthCheckPrivateEnabled()) notFound();

  return (
    <AuthGate>
      <div className="flex min-h-screen flex-col bg-background text-foreground">
        <EcosystemHeader currentApp="tools" />
        <main className="mx-auto w-full max-w-5xl flex-1 space-y-8 px-4 py-10 sm:px-6 lg:px-8">
          <header className="space-y-5">
            <Breadcrumbs items={[{ label: 'Home', href: '/' }, { label: 'Private review' }, { label: 'Fund Truth Check' }]} />
            <div className="flex flex-col gap-5 border-b border-line pb-7 sm:flex-row sm:items-end sm:justify-between">
              <div className="max-w-3xl">
                <p className="font-mono text-xs uppercase tracking-[0.2em] text-primary">Evidence before answers</p>
                <h1 className="mt-3 font-serif-display text-3xl font-extrabold tracking-tight text-white sm:text-5xl">Fund Truth Check</h1>
                <p className="mt-3 max-w-2xl text-sm leading-relaxed text-text-3 sm:text-base">
                  Break a mutual-fund statement into factual claims, compare deterministic values, and inspect the dated official evidence behind each result.
                </p>
              </div>
              <span className="inline-flex w-fit items-center gap-2 rounded-full border border-amber-300/30 bg-amber-300/10 px-3 py-2 text-xs font-semibold text-amber-200">
                <FlaskConical className="size-4" /> Private · Under review
              </span>
            </div>
          </header>
          <TruthCheckWorkbench />
        </main>
        <PublicFooter />
      </div>
    </AuthGate>
  );
}
