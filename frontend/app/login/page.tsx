import { redirect } from 'next/navigation';

// Legacy alias that redirects to /auth; keep it out of the index.
export const metadata = {
  robots: { index: false, follow: false },
};

export default function LoginPage() {
  redirect('/auth');
}
