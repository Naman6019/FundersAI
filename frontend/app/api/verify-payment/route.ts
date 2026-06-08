import { NextResponse } from 'next/server';
import { verifyRazorpayPaymentSignature } from '@/lib/billing/razorpay';

export const runtime = 'nodejs';

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const paymentId = typeof body?.razorpay_payment_id === 'string' ? body.razorpay_payment_id.trim() : '';
  const orderId = typeof body?.razorpay_order_id === 'string' ? body.razorpay_order_id.trim() : '';
  const signature = typeof body?.razorpay_signature === 'string' ? body.razorpay_signature.trim() : '';

  if (!paymentId || !orderId || !signature) {
    return NextResponse.json({ error: 'missing_payment_fields' }, { status: 400 });
  }

  if (!verifyRazorpayPaymentSignature({ orderId, paymentId, signature })) {
    return NextResponse.json({ error: 'signature_mismatch' }, { status: 400 });
  }

  return NextResponse.json({ status: 'ok', verified: true });
}
