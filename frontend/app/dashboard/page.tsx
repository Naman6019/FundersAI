import { Suspense } from 'react';
import AuthGate from '@/components/auth/AuthGate';
import DashboardLayout from '@/components/layout/DashboardLayout';

export default function Dashboard() {
  return (
    <Suspense fallback={null}>
      <AuthGate>
        <DashboardLayout />
      </AuthGate>
    </Suspense>
  );
}
