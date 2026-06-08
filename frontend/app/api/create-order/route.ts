import { NextResponse } from 'next/server';
import { createRazorpayOrder } from '@/lib/billing/razorpay';

export const runtime = 'nodejs';

function errorStatus(error: unknown): number {
  const candidate = error as { statusCode?: number; status?: number; response?: { status?: number } };
  return Number(candidate?.statusCode || candidate?.status || candidate?.response?.status || 500);
}

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const amount = Math.trunc(Number(body?.amount));
  const currency = String(body?.currency || 'INR').trim().toUpperCase();
  const receiptInput = typeof body?.receipt === 'string' ? body.receipt.trim() : '';
  const receipt = (receiptInput || `rcpt_${Date.now()}`).slice(0, 40);

  if (!Number.isFinite(amount) || amount < 100) {
    return NextResponse.json({ error: 'amount_must_be_at_least_100_paise' }, { status: 400 });
  }

  if (!/^[A-Z]{3}$/.test(currency)) {
    return NextResponse.json({ error: 'invalid_currency' }, { status: 400 });
  }

  try {
    const order = await createRazorpayOrder({ amount, currency, receipt });
    return NextResponse.json({
      order_id: order.id,
      amount: Number(order.amount),
      currency: order.currency,
    });
  } catch (error) {
    console.error('Razorpay order create failed:', error);
    const status = errorStatus(error) === 401 ? 401 : 500;
    return NextResponse.json(
      { error: status === 401 ? 'razorpay_auth_failed' : 'razorpay_order_create_failed' },
      { status },
    );
  }
}
