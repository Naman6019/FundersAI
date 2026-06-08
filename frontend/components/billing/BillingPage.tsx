'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Check, Loader2 } from 'lucide-react';
import { MONTHLY_TIERS, PaidTier, UserTier } from '@/lib/billing/tiers';
import { supabaseBrowser } from '@/lib/supabaseBrowser';
import StandardCheckoutPanel from './StandardCheckoutPanel';

type RazorpayCheckoutOptions = {
  key: string;
  subscription_id: string;
  name: string;
  description: string;
  prefill?: { email?: string };
  notes?: Record<string, string>;
  theme?: { color?: string };
  handler?: () => void;
  modal?: { ondismiss?: () => void };
};

type BillingStatus = {
  profile?: { tier?: UserTier; role?: string };
  subscription?: {
    tier?: UserTier;
    status?: string;
    provider_subscription_id?: string;
    current_end?: string | null;
  } | null;
};

async function billingFetch(path: string, init: RequestInit = {}) {
  const { data } = await supabaseBrowser.auth.getSession();
  const token = data.session?.access_token;
  const headers = new Headers(init.headers);
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (init.body) headers.set('Content-Type', 'application/json');
  return fetch(path, { ...init, headers, cache: 'no-store' });
}

function loadRazorpayScript(): Promise<boolean> {
  if (window.Razorpay) return Promise.resolve(true);
  return new Promise((resolve) => {
    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

function formatDate(value?: string | null) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

export default function BillingPage() {
  const [billing, setBilling] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyTier, setBusyTier] = useState<PaidTier | null>(null);
  const [message, setMessage] = useState('');

  const refreshBilling = async () => {
    const res = await billingFetch('/api/billing/subscriptions');
    const payload = await res.json().catch(() => ({}));
    if (res.ok) setBilling(payload as BillingStatus);
    setLoading(false);
  };

  useEffect(() => {
    let ignore = false;

    const loadInitialBilling = async () => {
      const res = await billingFetch('/api/billing/subscriptions');
      const payload = await res.json().catch(() => ({}));
      if (ignore) return;
      if (res.ok) setBilling(payload as BillingStatus);
      setLoading(false);
    };

    void loadInitialBilling();
    return () => {
      ignore = true;
    };
  }, []);

  const startCheckout = async (tier: PaidTier) => {
    setBusyTier(tier);
    setMessage('');

    const res = await billingFetch('/api/billing/subscriptions', {
      method: 'POST',
      body: JSON.stringify({ tier }),
    });
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      setBusyTier(null);
      setMessage(String(payload.error || 'Unable to start checkout.'));
      return;
    }

    const loaded = await loadRazorpayScript();
    if (!loaded || !window.Razorpay) {
      setBusyTier(null);
      setMessage('Unable to load Razorpay Checkout.');
      return;
    }

    const checkout = payload.checkout as RazorpayCheckoutOptions;
    const razorpay = new window.Razorpay({
      ...checkout,
      theme: { color: '#66a3ff' },
      handler: () => {
        setMessage('Payment authorised. Your tier updates after Razorpay confirms the subscription.');
        setBusyTier(null);
        void refreshBilling();
      },
      modal: {
        ondismiss: () => setBusyTier(null),
      },
    } as unknown as Record<string, unknown>);
    razorpay.open();
  };

  const currentTier = billing?.profile?.tier || 'free';
  const currentEnd = formatDate(billing?.subscription?.current_end);

  return (
    <main className="min-h-screen bg-[#050913] px-4 py-6 text-[#e8f0ff]">
      <div className="mx-auto max-w-6xl">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.18em] text-[#8fa9cf]">Billing</p>
            <h1 className="mt-1 text-3xl font-semibold text-white">Choose your FundersAI tier</h1>
            <p className="mt-2 max-w-2xl text-sm text-slate-300">
              Paid access is activated only after Razorpay sends a verified subscription webhook.
            </p>
          </div>
          <Link href="/dashboard" className="rounded-lg border border-white/15 px-3 py-2 text-sm text-[#c7daf5] hover:bg-white/5">
            Back to dashboard
          </Link>
        </div>

        {loading ? (
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 text-sm text-slate-300">Loading billing status...</div>
        ) : null}

        {message ? (
          <div className="mb-4 rounded-2xl border border-[#66a3ff]/30 bg-[#66a3ff]/10 p-4 text-sm text-[#cce0ff]">{message}</div>
        ) : null}

        <div className="grid gap-4 md:grid-cols-3">
          {Object.values(MONTHLY_TIERS).map((tier) => {
            const isCurrent = currentTier === tier.tier;
            const isPaid = tier.tier === 'pro' || tier.tier === 'ultra';
            return (
              <section
                key={tier.tier}
                className={`rounded-2xl border p-5 ${
                  isCurrent
                    ? 'border-[#66a3ff]/60 bg-[#0f2544]'
                    : 'border-white/10 bg-white/[0.04]'
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <h2 className="text-xl font-semibold text-white">{tier.name}</h2>
                    <p className="mt-2 text-3xl font-semibold text-white">{tier.priceLabel}</p>
                  </div>
                  {isCurrent ? (
                    <span className="rounded-full border border-emerald-300/40 bg-emerald-400/10 px-2 py-1 text-xs text-emerald-200">
                      Current
                    </span>
                  ) : null}
                </div>
                <p className="mt-4 min-h-[44px] text-sm text-slate-300">{tier.description}</p>
                <ul className="mt-4 space-y-2 text-sm text-slate-200">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex gap-2">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-[#66a3ff]" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>
                {isPaid ? (
                  <button
                    type="button"
                    onClick={() => startCheckout(tier.tier as PaidTier)}
                    disabled={Boolean(busyTier) || isCurrent}
                    className="mt-6 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-[#66a3ff] px-4 text-sm font-semibold text-slate-950 transition hover:bg-[#8bbcff] disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {busyTier === tier.tier ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                    {isCurrent ? 'Current plan' : `Upgrade to ${tier.name}`}
                  </button>
                ) : (
                  <div className="mt-6 rounded-xl border border-white/10 px-4 py-3 text-center text-sm text-slate-300">
                    Included for every account
                  </div>
                )}
              </section>
            );
          })}
        </div>

        {billing?.subscription ? (
          <section className="mt-5 rounded-2xl border border-white/10 bg-white/[0.04] p-4 text-sm text-slate-300">
            <p>
              Razorpay subscription: <span className="text-white">{billing.subscription.provider_subscription_id || '-'}</span>
            </p>
            <p className="mt-1">
              Status: <span className="text-white">{billing.subscription.status || '-'}</span>
              {currentEnd ? <span> · Current period ends {currentEnd}</span> : null}
            </p>
          </section>
        ) : null}

        <StandardCheckoutPanel />
      </div>
    </main>
  );
}
