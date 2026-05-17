import PremiumLandingPage from '@/components/landing/PremiumLandingPage';

export const revalidate = 60;

export default async function LandingPage() {
  return <PremiumLandingPage />;
}
