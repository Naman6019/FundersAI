import { Suspense } from 'react';
import AuthForm from '@/components/auth/AuthForm';
import AuthShell from '@/components/auth/AuthShell';

function AuthPageFallback() {
  return (
    <AuthShell title="Welcome to FundersAI" description="Loading your secure sign-in options…">
      <div className="h-11 animate-pulse rounded-xl bg-white/[0.06]" />
      <div className="my-5 h-px bg-white/[0.08]" />
      <div className="space-y-4">
        <div className="h-16 animate-pulse rounded-xl bg-white/[0.04]" />
        <div className="h-16 animate-pulse rounded-xl bg-white/[0.04]" />
        <div className="h-11 animate-pulse rounded-xl bg-[#66a3ff]/20" />
      </div>
    </AuthShell>
  );
}

export default function AuthPage() {
  return (
    <Suspense fallback={<AuthPageFallback />}>
      <AuthForm />
    </Suspense>
  );
}
