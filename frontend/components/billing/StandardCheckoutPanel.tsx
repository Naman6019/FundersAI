'use client';

import { useState } from 'react';
import { Loader2 } from 'lucide-react';

type RazorpayPaymentResponse = {
  razorpay_payment_id: string;
  razorpay_order_id: string;
  razorpay_signature: string;
};

type RazorpayFailedPaymentResponse = {
  error?: {
    description?: string;
    reason?: string;
  };
};

async function loadRazorpayScript(): Promise<boolean> {
  if (window.Razorpay) return true;
  return new Promise((resolve) => {
    const script = document.createElement('script');
    script.src = 'https://checkout.razorpay.com/v1/checkout.js';
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.body.appendChild(script);
  });
}

export default function StandardCheckoutPanel() {
  const [amountRupees, setAmountRupees] = useState('1');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');

  const startPayment = async () => {
    const amount = Math.round(Number(amountRupees) * 100);
    if (!Number.isFinite(amount) || amount < 100) {
      setMessage('Minimum payment amount is ₹1.');
      return;
    }

    setIsLoading(true);
    setMessage('');

    const orderRes = await fetch('/api/create-order', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        amount,
        currency: 'INR',
        receipt: `fundersai_${Date.now()}`,
      }),
    });
    const order = await orderRes.json().catch(() => ({}));

    if (!orderRes.ok) {
      setIsLoading(false);
      setMessage(String(order.error || 'Unable to create Razorpay order.'));
      return;
    }

    const loaded = await loadRazorpayScript();
    const key = process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID || '';
    if (!loaded || !window.Razorpay || !key) {
      setIsLoading(false);
      setMessage('Unable to load Razorpay Checkout.');
      return;
    }

    const checkout = new window.Razorpay({
      key,
      amount: Number(order.amount),
      currency: String(order.currency || 'INR'),
      name: 'FundersAI',
      description: 'Standard Checkout payment',
      order_id: String(order.order_id),
      theme: { color: '#66a3ff' },
      modal: {
        ondismiss: () => {
          setIsLoading(false);
          setMessage('Payment cancelled.');
        },
      },
      handler: async (response: RazorpayPaymentResponse) => {
        const verifyRes = await fetch('/api/verify-payment', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(response),
        });
        const payload = await verifyRes.json().catch(() => ({}));
        setIsLoading(false);
        setMessage(verifyRes.ok ? 'Payment verified.' : String(payload.error || 'Payment verification failed.'));
      },
    } as unknown as Record<string, unknown>);

    checkout.on('payment.failed', (response) => {
      const failed = response as RazorpayFailedPaymentResponse;
      setIsLoading(false);
      setMessage(failed.error?.description || failed.error?.reason || 'Payment failed.');
    });
    checkout.open();
  };

  return (
    <section className="mt-5 rounded-2xl border border-white/10 bg-white/[0.04] p-5">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white">Standard Checkout</h2>
          <p className="mt-2 max-w-2xl text-sm text-slate-300">
            Create a Razorpay order, open Checkout, and verify the payment signature on the server.
          </p>
        </div>
        <label className="text-sm text-slate-300">
          Amount
          <div className="mt-1 flex items-center overflow-hidden rounded-xl border border-white/10 bg-[#080d1a]">
            <span className="px-3 text-slate-400">₹</span>
            <input
              type="number"
              min="1"
              step="1"
              value={amountRupees}
              onChange={(event) => setAmountRupees(event.target.value)}
              className="h-11 w-28 bg-transparent px-2 text-white outline-none"
            />
          </div>
        </label>
      </div>

      <button
        type="button"
        onClick={startPayment}
        disabled={isLoading}
        className="mt-4 inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-[#66a3ff] px-4 text-sm font-semibold text-slate-950 transition hover:bg-[#8bbcff] disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
        Pay with Razorpay
      </button>

      {message ? <p className="mt-3 text-sm text-slate-300">{message}</p> : null}
    </section>
  );
}
