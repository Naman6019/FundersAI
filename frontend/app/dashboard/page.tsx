import { Suspense } from 'react';
import AuthGate from '@/components/auth/AuthGate';
import { DataHealthProvider } from '@/components/data-health/DataHealthProvider';
import DashboardLayout from '@/components/layout/DashboardLayout';

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
