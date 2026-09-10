import { redirect } from 'next/navigation';

// Legacy alias that redirects to /auth; keep it out of the index.
export const metadata = {
  robots: { index: false, follow: false },
};

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<{ mode?: string; next?: string; reset?: string }>;
}) {
  const params = await searchParams;
  const authParams = new URLSearchParams();

  for (const key of ['mode', 'next', 'reset'] as const) {
    if (params[key]) authParams.set(key, params[key]);
  }

  const query = authParams.toString();
  redirect(query ? `/auth?${query}` : '/auth');
}
