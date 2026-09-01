import FeedbackPageForm from '@/components/feedback/FeedbackPageForm';

// Form-only page with no ranking content.
export const metadata = {
  robots: { index: false, follow: false },
};

export default async function FeedbackPage({ searchParams }: { searchParams: Promise<{ source?: string }> }) {
  const params = await searchParams;
  return <FeedbackPageForm source={params.source || 'general'} />;
}

