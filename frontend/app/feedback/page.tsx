import FeedbackPageForm from '@/components/feedback/FeedbackPageForm';

export default async function FeedbackPage({ searchParams }: { searchParams: Promise<{ source?: string }> }) {
  const params = await searchParams;
  return <FeedbackPageForm source={params.source || 'general'} />;
}

