import { Suspense } from 'react';
import AuthGate from '@/components/auth/AuthGate';
import { DataHealthProvider } from '@/components/data-health/DataHealthProvider';
import DashboardLayout from '@/components/layout/DashboardLayout';

// Auth-gated workspace: every ?query= permutation is a distinct URL to a crawler.
export const metadata = {
  robots: { index: false, follow: false },
};

export default function Dashboard() {
  return (
    <Suspense fallback={null}>
      <AuthGate>
        <DataHealthProvider>
          <DashboardLayout />
        </DataHealthProvider>
      </AuthGate>
    </Suspense>
  );
}
