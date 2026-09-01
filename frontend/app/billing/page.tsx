import { Suspense } from 'react';
import AuthGate from '@/components/auth/AuthGate';
import BillingPage from '@/components/billing/BillingPage';

// Account billing surface: private per user, nothing to rank.
export const metadata = {
  robots: { index: false, follow: false },
};

export default function Billing() {
  return (
    <Suspense fallback={null}>
      <AuthGate>
        <BillingPage />
      </AuthGate>
    </Suspense>
  );
}
