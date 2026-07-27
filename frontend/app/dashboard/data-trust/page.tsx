import AuthGate from '@/components/auth/AuthGate';
import { DataHealthProvider } from '@/components/data-health/DataHealthProvider';
import DataTrustPage from '@/components/data-health/DataTrustPage';

export default function Page() {
  return (
    <AuthGate>
      <DataHealthProvider>
        <DataTrustPage />
      </DataHealthProvider>
    </AuthGate>
  );
}

