import crypto from 'crypto';
import Razorpay from 'razorpay';
import { MONTHLY_TIERS, PaidTier, UserTier, isPaidTier } from './tiers';

export type RazorpayOrder = {
  id: string;
  amount: number | string;
  currency: string;
  receipt?: string;
  status?: string;
};

export type RazorpaySubscription = {
  id: string;
  entity?: string;
  plan_id?: string;
  customer_id?: string | null;
  customer_email?: string | null;
  status?: string;
  current_start?: number | null;
  current_end?: number | null;
  ended_at?: number | null;
  short_url?: string | null;
  notes?: Record<string, string | number | boolean | null>;
  [key: string]: unknown;
};

type CreateSubscriptionInput = {
  tier: PaidTier;
  userId: string;
  email: string | null;
};

type CreateOrderInput = {
  amount: number;
  currency: string;
  receipt: string;
};

function requiredEnv(name: string): string {
  const value = String(process.env[name] || '').trim();
  if (!value) throw new Error(`missing_env:${name}`);
  return value;
}

export function razorpayKeyId(): string {
  return requiredEnv('RAZORPAY_KEY_ID');
}

export function publicRazorpayKeyId(): string {
  return String(process.env.NEXT_PUBLIC_RAZORPAY_KEY_ID || process.env.RAZORPAY_KEY_ID || '').trim();
}

function razorpayClient() {
  return new Razorpay({
    key_id: razorpayKeyId(),
    key_secret: requiredEnv('RAZORPAY_KEY_SECRET'),
  });
}

export function razorpayKeyMode(keyId = razorpayKeyId()): 'test' | 'live' | 'unknown' {
  if (keyId.startsWith('rzp_test_')) return 'test';
  if (keyId.startsWith('rzp_live_')) return 'live';
  return 'unknown';
}

export function assertRazorpayPlanId(planId: string) {
  if (!planId.startsWith('plan_')) {
    throw new Error('invalid_razorpay_plan_id');
  }
}

export function assertRazorpaySubscription(subscription: RazorpaySubscription) {
  if (!subscription.id?.startsWith('sub_')) {
    throw new Error('invalid_razorpay_subscription_id');
  }

  const status = String(subscription.status || '');

  if (!['created', 'authenticated', 'active'].includes(status)) {
    throw new Error(`invalid_razorpay_subscription_status:${status || 'missing'}`);
  }
}

export function planIdForTier(tier: PaidTier): string {
  const envName = tier === 'pro' ? 'RAZORPAY_PLAN_PRO_MONTHLY_ID' : 'RAZORPAY_PLAN_ULTRA_MONTHLY_ID';
  return requiredEnv(envName);
}

export function tierForPlanId(planId: string | null | undefined): UserTier {
  if (planId && planId === String(process.env.RAZORPAY_PLAN_PRO_MONTHLY_ID || '').trim()) return 'pro';
  if (planId && planId === String(process.env.RAZORPAY_PLAN_ULTRA_MONTHLY_ID || '').trim()) return 'ultra';
  return 'free';
}

export function unixToIso(value: unknown): string | null {
  const seconds = Number(value);
  if (!Number.isFinite(seconds) || seconds <= 0) return null;
  return new Date(seconds * 1000).toISOString();
}

export async function createRazorpaySubscription(input: CreateSubscriptionInput): Promise<RazorpaySubscription> {
  const planId = planIdForTier(input.tier);
  const tier = MONTHLY_TIERS[input.tier];

  assertRazorpayPlanId(planId);

  console.info('[razorpay:subscription:create]', {
    key_mode: razorpayKeyMode(),
    plan_id: planId,
  });

  const subscription = await razorpayClient().subscriptions.create({
    plan_id: planId,
    total_count: 12,
    customer_notify: 1,
    quantity: 1,
    notes: {
      user_id: input.userId,
      tier: input.tier,
      billing_period: tier.billingPeriod,
      email: input.email || '',
    },
  });
  const normalized = subscription as unknown as RazorpaySubscription;

  assertRazorpaySubscription(normalized);

  console.info('[razorpay:subscription:created]', {
    subscription_id: normalized.id,
    status: normalized.status,
    plan_id: normalized.plan_id,
  });

  return normalized;
}

export async function createRazorpayOrder(input: CreateOrderInput): Promise<RazorpayOrder> {
  const order = await razorpayClient().orders.create({
    amount: input.amount,
    currency: input.currency,
    receipt: input.receipt,
  });

  return {
    id: order.id,
    amount: order.amount,
    currency: order.currency,
    receipt: order.receipt,
    status: order.status,
  };
}

function timingSafeHexEqual(expected: string, received: string): boolean {
  const expectedBytes = Buffer.from(expected);
  const receivedBytes = Buffer.from(received);
  return expectedBytes.length === receivedBytes.length && crypto.timingSafeEqual(expectedBytes, receivedBytes);
}

export function verifyRazorpayPaymentSignature(input: {
  orderId: string;
  paymentId: string;
  signature: string;
}): boolean {
  const expected = crypto
    .createHmac('sha256', requiredEnv('RAZORPAY_KEY_SECRET'))
    .update(`${input.orderId}|${input.paymentId}`)
    .digest('hex');
  return timingSafeHexEqual(expected, input.signature);
}

export function verifyRazorpayWebhookSignature(rawBody: string, signature: string | null): boolean {
  const secret = String(process.env.RAZORPAY_WEBHOOK_SECRET || '').trim();
  if (!secret || !signature) return false;
  const expected = crypto.createHmac('sha256', secret).update(rawBody).digest('hex');
  return timingSafeHexEqual(expected, signature);
}

export function eventIdFromRequest(rawBody: string, request: Request): string {
  const header = request.headers.get('x-razorpay-event-id')?.trim();
  if (header) return header;
  return `generated_${crypto.createHash('sha256').update(rawBody).digest('hex').slice(0, 32)}`;
}

export function tierFromSubscription(subscription: RazorpaySubscription | null): UserTier {
  const noteTier = subscription?.notes?.tier;
  if (isPaidTier(noteTier)) return noteTier;
  return tierForPlanId(subscription?.plan_id);
}
