'use client';

import { ReactNode, Suspense, useEffect, useState } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import type { User } from '@supabase/supabase-js';
import { hasSupabaseBrowserEnv, supabaseBrowser } from '@/lib/supabaseBrowser';
import FeedbackPrompt from '@/components/feedback/FeedbackPrompt';

type AuthGateProps = {
  children: ReactNode;
};

const bypassAuth =
  process.env.NODE_ENV === 'development' ||
  process.env.NEXT_PUBLIC_DISABLE_AUTH === '1';

function AuthGateContent({ children }: AuthGateProps) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(!bypassAuth);

  useEffect(() => {
    if (bypassAuth) {
      return;
    }

    const getRedirectTarget = () => {
      const search = searchParams?.toString();
      return search ? `${pathname}?${search}` : pathname;
    };

    if (!hasSupabaseBrowserEnv) {
      router.replace(`/auth?next=${encodeURIComponent(getRedirectTarget())}`);
      return;
    }

    let isActive = true;
    const redirectSignedOut = () => {
      const feedbackPending = window.sessionStorage.getItem('fundersai-logout-feedback-pending') === '1';
      router.replace(feedbackPending ? '/feedback?source=logout' : `/auth?next=${encodeURIComponent(getRedirectTarget())}`);
    };

    supabaseBrowser.auth.getUser().then(({ data }) => {
      if (!isActive) return;
      setUser(data.user);
      setIsLoading(false);
      if (!data.user) {
        redirectSignedOut();
      }
    });

    const { data: listener } = supabaseBrowser.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (!session?.user) {
        redirectSignedOut();
      }
    });

    return () => {
      isActive = false;
      listener.subscription.unsubscribe();
    };
  }, [pathname, router, searchParams]);

  if (!bypassAuth && (isLoading || !user)) {
    return (
      <div className="auth-loading">
        <span>Loading workspace…</span>
      </div>
    );
  }

  return <>{children}{!bypassAuth && user ? <FeedbackPrompt /> : null}</>;
}

export default function AuthGate({ children }: AuthGateProps) {
  return (
    <Suspense
      fallback={
        <div className="auth-loading">
          <span>Loading workspace…</span>
        </div>
      }
    >
      <AuthGateContent>{children}</AuthGateContent>
    </Suspense>
  );
}
