'use client';

import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { adminFetch } from '@/lib/admin/client';

type Props = { children: React.ReactNode };

export default function AdminAccessGate({ children }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const [state, setState] = useState<'checking' | 'allowed' | 'denied'>('checking');

  useEffect(() => {
    let active = true;
    const run = async () => {
      const res = await adminFetch('/api/admin/session');
      if (!active) return;

      if (res.status === 401) {
        router.replace(`/auth?next=${encodeURIComponent(pathname || '/admin')}`);
        return;
      }
      if (res.status === 403) {
        setState('denied');
        return;
      }
      if (!res.ok) {
        setState('denied');
        return;
      }
      setState('allowed');
    };
    run();
    return () => {
      active = false;
    };
  }, [pathname, router]);

  if (state === 'checking') {
    return (
      <div className="grid min-h-screen place-items-center bg-[#060d1a] text-[#d9e8ff]">
        <div className="rounded-2xl border border-white/10 bg-slate-950/40 px-5 py-4 text-sm">Checking admin access…</div>
      </div>
    );
  }

  if (state === 'denied') {
    return (
      <div className="grid min-h-screen place-items-center bg-[#060d1a] text-[#d9e8ff] px-4">
        <div className="max-w-md rounded-3xl border border-red-400/30 bg-slate-950/50 p-6 text-center">
          <h1 className="text-xl font-semibold text-red-200">Access denied</h1>
          <p className="mt-2 text-sm text-[#b8c7e4]">You do not have admin access for this dashboard.</p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

