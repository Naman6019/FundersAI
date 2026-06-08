'use client';

import { Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { hasSupabaseBrowserEnv, supabaseBrowser } from '@/lib/supabaseBrowser';

const AUTH_NEXT_STORAGE_KEY = 'fundersai_auth_next';

function safeNextPath(value: string | null): string {
  if (!value || !value.startsWith('/') || value.startsWith('//')) return '/dashboard';
  return value;
}

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [message, setMessage] = useState('Completing sign in...');

  useEffect(() => {
    let cancelled = false;

    const finishAuth = async () => {
      if (!hasSupabaseBrowserEnv) {
        setMessage('Supabase auth is not configured.');
        return;
      }

      const storedNext = window.localStorage.getItem(AUTH_NEXT_STORAGE_KEY);
      const nextPath = safeNextPath(searchParams.get('next') || storedNext);
      window.localStorage.removeItem(AUTH_NEXT_STORAGE_KEY);
      const url = new URL(window.location.href);
      const error = url.searchParams.get('error_description') || url.searchParams.get('error');
      if (error) {
        setMessage(error);
        return;
      }

      const code = url.searchParams.get('code');
      if (code) {
        const { error: exchangeError } = await supabaseBrowser.auth.exchangeCodeForSession(code);
        if (exchangeError) {
          setMessage(exchangeError.message);
          return;
        }
      } else {
        const { data } = await supabaseBrowser.auth.getSession();
        if (!data.session) {
          setMessage('No sign-in session was returned.');
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

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <div className="auth-heading">
          <h1>Signing you in</h1>
          <p>{message}</p>
        </div>
      </section>
    </main>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={null}>
      <AuthCallbackContent />
    </Suspense>
  );
}
