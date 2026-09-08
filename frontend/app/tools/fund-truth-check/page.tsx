import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import AuthGate from '@/components/auth/AuthGate';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
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
        <main className="mx-auto w-full max-w-[1480px] flex-1 px-4 py-6 sm:px-6 lg:px-10">
          <TruthCheckWorkbench />
        </main>
      </div>
    </AuthGate>
  );
}
