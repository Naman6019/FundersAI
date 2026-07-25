'use client';

import { Suspense, useEffect, useState } from 'react';
import Link from 'next/link';
import { LoaderCircle } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import AuthShell from '@/components/auth/AuthShell';
import { getAuthErrorMessage } from '@/lib/authErrorMessage';
import { hasSupabaseBrowserEnv, supabaseBrowser } from '@/lib/supabaseBrowser';

const AUTH_NEXT_STORAGE_KEY = 'fundersai_auth_next';

function safeNextPath(value: string | null): string {
  if (!value || !value.startsWith('/') || value.startsWith('//')) return '/dashboard';
  return value;
}

function CallbackCard({ message, hasError = false }: { message: string; hasError?: boolean }) {
  return (
    <AuthShell
      title={hasError ? 'We could not sign you in' : 'Completing sign in'}
      description={message}
    >
      {hasError ? (
        <Link
          href="/auth"
          className="flex min-h-11 w-full items-center justify-center rounded-xl bg-[#66a3ff] px-4 text-sm font-semibold text-[#07111f] transition hover:bg-[#80b3ff] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#9bc3ff]"
        >
          Return to sign in
        </Link>
      ) : (
        <div role="status" className="flex items-center justify-center gap-2 py-4 text-sm text-[#91a3bf]">
          <LoaderCircle aria-hidden="true" className="h-4 w-4 animate-spin" />
          Verifying your session…
        </div>
      )}
    </AuthShell>
  );
}

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [message, setMessage] = useState('Securely verifying your session.');
  const [hasError, setHasError] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const showError = (error: unknown) => {
      if (!cancelled) {
        setHasError(true);
        setMessage(getAuthErrorMessage(error));
      }
    };

    const finishAuth = async () => {
      if (!hasSupabaseBrowserEnv) {
        showError(new Error('Authentication is not configured'));
        return;
      }

      const storedNext = window.localStorage.getItem(AUTH_NEXT_STORAGE_KEY);
      const nextPath = safeNextPath(searchParams.get('next') || storedNext);
      window.localStorage.removeItem(AUTH_NEXT_STORAGE_KEY);
      const url = new URL(window.location.href);
      const providerError = url.searchParams.get('error_description') || url.searchParams.get('error');
      if (providerError) {
        showError(new Error(providerError));
        return;
      }

      const code = url.searchParams.get('code');
      if (code) {
        const { error } = await supabaseBrowser.auth.exchangeCodeForSession(code);
        if (error) {
          showError(error);
          return;
        }
      } else {
        const { data } = await supabaseBrowser.auth.getSession();
        if (!data.session) {
          showError(new Error('Invalid or expired token'));
          return;
        }
      }

      if (!cancelled) {
        router.replace(nextPath);
        router.refresh();
      }
    };

    void finishAuth();
    return () => {
      cancelled = true;
    };
  }, [router, searchParams]);

  return <CallbackCard message={message} hasError={hasError} />;
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<CallbackCard message="Loading the secure sign-in flow." />}>
      <AuthCallbackContent />
    </Suspense>
  );
}
