'use client';

import { useEffect, useState, useRef } from 'react';
import Link from 'next/link';
import { Check, Loader2 } from 'lucide-react';
import { MONTHLY_TIERS, PaidTier, UserTier } from '@/lib/billing/tiers';
import { supabaseBrowser } from '@/lib/supabaseBrowser';
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Sparkles as SparklesComp } from "@/components/ui/sparkles";
import { TimelineContent } from "@/components/ui/timeline-animation";
import { VerticalCutReveal } from "@/components/ui/vertical-cut-reveal";
import { cn } from "@/lib/utils";
import NumberFlow from "@number-flow/react";
import { motion } from "framer-motion";

type RazorpayCheckoutOptions = {
  key: string;
  subscription_id: string;
  name: string;
  description: string;
  prefill?: { email?: string };
  notes?: Record<string, string>;
  theme?: { color?: string };
  handler?: (response: RazorpaySubscriptionCheckoutResponse) => void;
  modal?: { ondismiss?: () => void };
  order_id?: unknown;
  amount?: unknown;
  currency?: unknown;
};

type RazorpaySubscriptionCheckoutResponse = {
  razorpay_payment_id?: string;
  razorpay_subscription_id?: string;
  razorpay_signature?: string;
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

const PricingSwitch = ({ onSwitch }: { onSwitch: (value: string) => void }) => {
  const [selected, setSelected] = useState("0");

  const handleSwitch = (value: string) => {
    setSelected(value);
    onSwitch(value);
  };

  return (
    <div className="flex justify-center">
      <div className="relative z-10 mx-auto flex w-fit rounded-full bg-neutral-900 border border-gray-700 p-1">
        <button
          onClick={() => handleSwitch("0")}
          className={cn(
            "relative z-10 w-fit h-10  rounded-full sm:px-6 px-3 sm:py-2 py-1 font-medium transition-colors",
            selected === "0" ? "text-white" : "text-gray-200",
          )}
        >
          {selected === "0" && (
            <motion.span
              layoutId={"switch"}
              className="absolute top-0 left-0 h-10 w-full rounded-full border-4 shadow-sm shadow-blue-600 border-blue-600 bg-gradient-to-t from-blue-500 to-blue-600"
              transition={{ type: "spring", stiffness: 500, damping: 30 }}
            />
          )}
          <span className="relative">Monthly</span>
        </button>

        <button
          onClick={() => handleSwitch("1")}
          className={cn(
            "relative z-10 w-fit h-10 flex-shrink-0 rounded-full sm:px-6 px-3 sm:py-2 py-1 font-medium transition-colors",
            selected === "1" ? "text-white" : "text-gray-200",
          )}
        >
          {selected === "1" && (
            <motion.span
              layoutId={"switch"}
              className="absolute top-0 left-0 h-10 w-full  rounded-full border-4 shadow-sm shadow-blue-600 border-blue-600 bg-gradient-to-t from-blue-500 to-blue-600"
              transition={{ type: "spring", stiffness: 500, damping: 30 }}
            />
          )}
          <span className="relative flex items-center gap-2">Yearly</span>
        </button>
      </div>
    </div>
  );
};

export default function BillingPage() {
  const [billing, setBilling] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyTier, setBusyTier] = useState<PaidTier | null>(null);
  const [message, setMessage] = useState('');
  
  const [isYearly, setIsYearly] = useState(false);
  const pricingRef = useRef<HTMLDivElement>(null);

  const revealVariants = {
    visible: (i: number) => ({
      y: 0,
      opacity: 1,
      filter: "blur(0px)",
      transition: {
        delay: i * 0.2,
        duration: 0.5,
      },
    }),
    hidden: {
      filter: "blur(10px)",
      y: -20,
      opacity: 0,
    },
  };

  const togglePricingPeriod = (value: string) =>
    setIsYearly(parseInt(value) === 1);

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

    if ('order_id' in checkout) {
      setBusyTier(null);
      throw new Error('subscription_checkout_received_order_id');
    }

    if (!checkout.subscription_id?.startsWith('sub_')) {
      setBusyTier(null);
      throw new Error('invalid_subscription_id');
    }

    const checkoutOptions: RazorpayCheckoutOptions = {
      key: checkout.key,
      subscription_id: checkout.subscription_id,
      name: checkout.name,
      description: checkout.description,
      prefill: checkout.prefill,
      notes: checkout.notes,
      theme: { color: '#66a3ff' },
      handler: (response: RazorpaySubscriptionCheckoutResponse) => {
        setMessage('Payment authorised. Your tier updates after Razorpay confirms the subscription.');
        setBusyTier(null);
        void refreshBilling();
      },
      modal: {
        ondismiss: () => setBusyTier(null),
      },
    };

    const razorpay = new window.Razorpay(checkoutOptions as unknown as Record<string, unknown>);
    razorpay.open();
  };

  const currentTier = billing?.profile?.tier || 'free';
  const currentEnd = formatDate(billing?.subscription?.current_end);
  const tiersList = Object.values(MONTHLY_TIERS);

  return (
    <div
      className="min-h-screen mx-auto relative bg-[#050913] overflow-x-hidden"
      ref={pricingRef}
    >
      <TimelineContent
        animationNum={4}
        timelineRef={pricingRef}
        customVariants={revealVariants}
        className="absolute top-0 h-96 w-screen overflow-hidden [mask-image:radial-gradient(50%_50%,white,transparent)] "
      >
        <div className="absolute bottom-0 left-0 right-0 top-0 bg-[linear-gradient(to_right,#ffffff2c_1px,transparent_1px),linear-gradient(to_bottom,#3a3a3a01_1px,transparent_1px)] bg-[size:70px_80px] "></div>
        <SparklesComp
          density={80}
          direction="bottom"
          speed={1}
          color="#FFFFFF"
          className="absolute inset-x-0 bottom-0 h-full w-full [mask-image:radial-gradient(50%_50%,white,transparent_85%)]"
        />
      </TimelineContent>
      <TimelineContent
        animationNum={5}
        timelineRef={pricingRef}
        customVariants={revealVariants}
        className="absolute left-0 top-[-114px] w-full h-[113.625vh] flex flex-col items-start justify-start content-start flex-none flex-nowrap gap-2.5 overflow-hidden p-0 z-0 pointer-events-none"
      >
        <div className="framer-1i5axl2 pointer-events-none">
          <div
            className="absolute left-[-568px] right-[-568px] top-0 h-[2053px] flex-none rounded-full"
            style={{
              border: "200px solid #3131f5",
              filter: "blur(92px)",
              WebkitFilter: "blur(92px)",
            }}
            data-border="true"
          ></div>
          <div
            className="absolute left-[-568px] right-[-568px] top-0 h-[2053px] flex-none rounded-full"
            style={{
              border: "200px solid #3131f5",
              filter: "blur(92px)",
              WebkitFilter: "blur(92px)",
            }}
            data-border="true"
          ></div>
        </div>
      </TimelineContent>

      <div className="relative z-50 flex items-center justify-between p-4 max-w-6xl mx-auto">
        <Link href="/dashboard" className="rounded-lg border border-white/15 bg-black/50 backdrop-blur-sm px-3 py-2 text-sm text-[#c7daf5] hover:bg-white/5 transition">
          Back to dashboard
        </Link>
      </div>

      <article className="text-center mb-6 pt-16 max-w-3xl mx-auto space-y-4 relative z-50 px-4">
        <h2 className="text-4xl md:text-5xl font-medium text-white">
          <VerticalCutReveal
            splitBy="words"
            staggerDuration={0.15}
            staggerFrom="first"
            reverse={true}
            containerClassName="justify-center "
            transition={{
              type: "spring",
              stiffness: 250,
              damping: 40,
              delay: 0,
            }}
          >
            Choose your FundersAI tier
          </VerticalCutReveal>
        </h2>

        <TimelineContent
          as="p"
          animationNum={0}
          timelineRef={pricingRef}
          customVariants={revealVariants}
          className="text-gray-300 max-w-2xl mx-auto"
        >
          Paid access is activated only after Razorpay sends a verified subscription webhook.
          Explore which option is right for you.
        </TimelineContent>

        <TimelineContent
          as="div"
          animationNum={1}
          timelineRef={pricingRef}
          customVariants={revealVariants}
          className="pt-4"
        >
          <PricingSwitch onSwitch={togglePricingPeriod} />
        </TimelineContent>
      </article>

      <div
        className="absolute top-0 left-[10%] right-[10%] w-[80%] h-full z-0 pointer-events-none"
        style={{
          backgroundImage: `radial-gradient(circle at center, #206ce8 0%, transparent 70%)`,
          opacity: 0.6,
          mixBlendMode: "multiply",
        }}
      />

      <div className="relative z-20 max-w-5xl mx-auto px-4">
        {loading ? (
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-4 text-sm text-slate-300 max-w-sm mx-auto text-center mb-8">
            Loading billing status...
          </div>
        ) : null}

        {message ? (
          <div className="mb-8 rounded-2xl border border-[#66a3ff]/30 bg-[#66a3ff]/10 p-4 text-sm text-[#cce0ff] max-w-md mx-auto text-center backdrop-blur-sm">
            {message}
          </div>
        ) : null}
      </div>

      <div className="grid md:grid-cols-3 max-w-5xl gap-6 pb-24 mx-auto px-4 relative z-20">
        {tiersList.map((tier, index) => {
          const isCurrent = currentTier === tier.tier;
          const isPaid = tier.tier === 'pro' || tier.tier === 'ultra';
          const isPopular = tier.tier === 'pro';
          
          return (
            <TimelineContent
              key={tier.tier}
              as="div"
              animationNum={2 + index}
              timelineRef={pricingRef}
              customVariants={revealVariants}
              className="h-full"
            >
              <Card
                className={`relative h-full text-white border-neutral-800 transition-all duration-300 hover:scale-[1.02] ${
                  isPopular
                    ? "bg-gradient-to-r from-neutral-900 via-neutral-800 to-neutral-900 shadow-[0px_-13px_300px_0px_#0900ff] z-20 border-[#3131f5]/50"
                    : "bg-gradient-to-r from-neutral-900 via-neutral-800 to-neutral-900 z-10"
                }`}
              >
                <CardHeader className="text-left pb-4">
                  <div className="flex justify-between items-center mb-2">
                    <h3 className="text-2xl font-medium">{tier.name}</h3>
                    {isCurrent && (
                      <span className="rounded-full border border-emerald-300/40 bg-emerald-400/10 px-2.5 py-1 text-xs text-emerald-200">
                        Current Plan
                      </span>
                    )}
                  </div>
                  <div className="flex items-baseline">
                    <span className="text-4xl font-semibold ">
                      <NumberFlow
                        format={{
                          style: "currency",
                          currency: "INR",
                          maximumFractionDigits: 0
                        }}
                        value={isYearly ? (tier.amountPaise / 100) * 10 : tier.amountPaise / 100}
                        className="text-4xl font-semibold"
                      />
                    </span>
                    <span className="text-gray-300 ml-1">
                      /{isYearly ? "year" : "month"}
                    </span>
                  </div>
                  <p className="text-sm text-gray-300 mt-3 min-h-[40px]">{tier.description}</p>
                </CardHeader>

                <CardContent className="pt-0 flex flex-col h-[calc(100%-160px)]">
                  {isPaid ? (
                    <button
                      type="button"
                      onClick={() => startCheckout(tier.tier as PaidTier)}
                      disabled={Boolean(busyTier) || isCurrent}
                      className={`w-full mb-6 p-3 text-lg rounded-xl font-medium transition-all ${
                        isCurrent
                          ? "bg-neutral-800 border border-neutral-700 text-neutral-400 cursor-not-allowed"
                          : isPopular
                          ? "bg-gradient-to-t from-blue-500 to-blue-600 shadow-lg shadow-blue-800/50 border border-blue-500 text-white hover:from-blue-400 hover:to-blue-500 disabled:opacity-60 disabled:cursor-not-allowed"
                          : "bg-gradient-to-t from-neutral-900 to-neutral-700 shadow-lg shadow-neutral-900 border border-neutral-700 text-white hover:from-neutral-800 hover:to-neutral-600 disabled:opacity-60 disabled:cursor-not-allowed"
                      }`}
                    >
                      {busyTier === tier.tier ? (
                        <span className="flex items-center justify-center gap-2">
                          <Loader2 className="h-5 w-5 animate-spin" /> Processing...
                        </span>
                      ) : isCurrent ? (
                        'Current plan'
                      ) : (
                        'Upgrade'
                      )}
                    </button>
                  ) : (
                    <div className="w-full mb-6 p-3 text-lg rounded-xl font-medium border border-white/10 bg-white/5 text-center text-slate-300">
                      Included automatically
                    </div>
                  )}

                  <div className="space-y-3 pt-4 border-t border-neutral-700/50 flex-grow">
                    <h4 className="font-medium text-sm text-slate-200 mb-3">
                      Features
                    </h4>
                    <ul className="space-y-3">
                      {tier.features.map((feature, featureIndex) => (
                        <li
                          key={featureIndex}
                          className="flex items-start gap-3"
                        >
                          <span className="mt-1 h-1.5 w-1.5 shrink-0 bg-blue-500 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.8)]"></span>
                          <span className="text-sm text-gray-300 leading-snug">{feature}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </CardContent>
              </Card>
            </TimelineContent>
          );
        })}
      </div>

      {billing?.subscription && (
        <div className="relative z-20 max-w-5xl mx-auto px-4 pb-12">
          <section className="rounded-2xl border border-white/10 bg-black/40 backdrop-blur-md p-5 text-sm text-slate-300 shadow-xl">
            <h4 className="font-semibold text-white text-base mb-2">Subscription Details</h4>
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">Razorpay ID</p>
                <p className="text-white font-mono">{billing.subscription.provider_subscription_id || '-'}</p>
              </div>
              <div>
                <p className="text-slate-400 text-xs uppercase tracking-wider mb-1">Status</p>
                <p className="text-white capitalize flex items-center gap-2">
                  {billing.subscription.status === 'active' ? (
                    <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
                  ) : (
                    <span className="h-2 w-2 rounded-full bg-amber-500"></span>
                  )}
                  {billing.subscription.status || '-'}
                </p>
              </div>
              {currentEnd && (
                <div className="sm:col-span-2 mt-2 pt-4 border-t border-white/10">
                  <p>Current period ends: <span className="text-white">{currentEnd}</span></p>
                </div>
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
