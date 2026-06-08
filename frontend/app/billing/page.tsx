import { Suspense } from 'react';
import AuthGate from '@/components/auth/AuthGate';
import BillingPage from '@/components/billing/BillingPage';

export default function Billing() {
  return (
    <Suspense fallback={null}>
      <AuthGate>
        <BillingPage />
      </AuthGate>
    </Suspense>
  );
}
