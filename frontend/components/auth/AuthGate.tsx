'use client';

import { ReactNode, useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import type { User } from '@supabase/supabase-js';
import { hasSupabaseBrowserEnv, supabaseBrowser } from '@/lib/supabaseBrowser';

type AuthGateProps = {
  children: ReactNode;
};

export default function AuthGate({ children }: AuthGateProps) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!hasSupabaseBrowserEnv) {
      router.replace(`/auth?next=${encodeURIComponent(pathname)}`);
      return;
    }

    let isActive = true;

    supabaseBrowser.auth.getUser().then(({ data }) => {
      if (!isActive) return;
      setUser(data.user);
      setIsLoading(false);
      if (!data.user) {
        router.replace(`/auth?next=${encodeURIComponent(pathname)}`);
      }
    });

    const { data: listener } = supabaseBrowser.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (!session?.user) {
        router.replace(`/auth?next=${encodeURIComponent(pathname)}`);
      }
    });

    return () => {
      isActive = false;
      listener.subscription.unsubscribe();
    };
  }, [pathname, router]);

  if (isLoading || !user) {
    return (
      <div className="auth-loading">
        <span>Loading workspace...</span>
      </div>
    );
  }

  return children;
}
