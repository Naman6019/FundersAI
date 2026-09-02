import AuthGate from '@/components/auth/AuthGate';
import { EcosystemHeader } from '@/components/ecosystem/EcosystemHeader';
import PortfolioTracker from '@/components/portfolio/PortfolioTracker';

export default function PortfolioPage() {
  return (
    <AuthGate>
      <div className="min-h-screen bg-[#050505] text-white">
        <EcosystemHeader currentApp="research" dataTrustHref="/dashboard/data-trust" />
        <main className="px-5 py-8 sm:px-8">
          <PortfolioTracker />
        </main>
      </div>
    </AuthGate>
  );
}
