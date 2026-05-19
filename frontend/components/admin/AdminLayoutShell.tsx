'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useMemo, useState } from 'react';
import { Menu, X } from 'lucide-react';

type Props = { children: React.ReactNode };

const NAV_ITEMS = [
  { href: '/admin', label: 'Overview' },
  { href: '/admin/users', label: 'Users' },
  { href: '/admin/ai-usage', label: 'AI Usage' },
  { href: '/admin/data-coverage', label: 'Data Coverage' },
  { href: '/admin/nav-sync', label: 'NAV Sync' },
  { href: '/admin/resolver-debug', label: 'Resolver Debug' },
];

const PAGE_DESCRIPTIONS: Record<string, string> = {
  '/admin': 'Core KPIs, alerts, and sync health summary.',
  '/admin/users': 'View user roles, tiers, and usage summary.',
  '/admin/ai-usage': 'Track request volume, failures, and quota burn.',
  '/admin/data-coverage': 'AMC-level mutual fund field coverage and freshness.',
  '/admin/nav-sync': 'Monitor NAV sync runs, status, and failures.',
  '/admin/resolver-debug': 'Validate scheme resolver selections and candidates.',
};

export default function AdminLayoutShell({ children }: Props) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const title = useMemo(() => {
    const item = NAV_ITEMS.find((entry) => pathname === entry.href);
    return item?.label || 'Admin';
  }, [pathname]);

  return (
    <div className="min-h-screen bg-[#060d1a] text-[#e8f0ff]">
      <div className="mx-auto flex max-w-[1500px] gap-4 px-3 py-3 md:px-5">
        <aside className="hidden w-[250px] shrink-0 rounded-3xl border border-white/10 bg-slate-950/40 p-4 md:block">
          <p className="text-xs uppercase tracking-[0.14em] text-[#8fa9cf]">Mooliq Admin</p>
          <nav className="mt-4 space-y-1">
            {NAV_ITEMS.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`block rounded-xl px-3 py-2 text-sm transition ${
                    active
                      ? 'border border-[#59a0ff]/60 bg-[#1a2d4c] text-white'
                      : 'text-[#b9cceb] hover:bg-[#12223c] hover:text-white'
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </aside>

        <div className="min-w-0 flex-1">
          <header className="mb-4 rounded-3xl border border-white/10 bg-slate-950/40 px-4 py-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h1 className="text-lg font-semibold">{title}</h1>
                <p className="mt-1 text-xs text-[#97afd2]">{PAGE_DESCRIPTIONS[pathname || '/admin'] || 'Admin dashboard'}</p>
              </div>
              <button
                type="button"
                onClick={() => setMobileOpen((value) => !value)}
                className="rounded-lg border border-white/15 bg-[#101e36] p-2 text-[#bcd1ef] md:hidden"
                aria-label="Toggle navigation"
              >
                {mobileOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
              </button>
            </div>
            {mobileOpen ? (
              <nav className="mt-3 space-y-1 border-t border-white/10 pt-3 md:hidden">
                {NAV_ITEMS.map((item) => {
                  const active = pathname === item.href;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`block rounded-xl px-3 py-2 text-sm ${
                        active ? 'bg-[#1a2d4c] text-white' : 'text-[#b9cceb]'
                      }`}
                      onClick={() => setMobileOpen(false)}
                    >
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
            ) : null}
          </header>

          <main>{children}</main>
        </div>
      </div>
    </div>
  );
}

