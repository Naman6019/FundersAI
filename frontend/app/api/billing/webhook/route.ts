import { NextResponse } from 'next/server';
import { createServiceClient } from '@/lib/auth/server';
import {
  RazorpaySubscription,
  eventIdFromRequest,
  tierFromSubscription,
  unixToIso,
  verifyRazorpayWebhookSignature,
} from '@/lib/billing/razorpay';
import { TIER_PRIORITY, UserTier } from '@/lib/billing/tiers';

export const runtime = 'nodejs';

function subscriptionFromPayload(payload: Record<string, unknown>): RazorpaySubscription | null {
  const nested = payload?.payload as { subscription?: { entity?: RazorpaySubscription } } | undefined;
  return nested?.subscription?.entity || null;
}

async function syncUserTierFromBilling(supabase: NonNullable<ReturnType<typeof createServiceClient>>, userId: string) {
  const activeRes = await supabase
    .from('billing_subscriptions')
    .select('tier')
    .eq('user_id', userId)
    .eq('status', 'active')
    .limit(20);

  const nextTier = ((activeRes.data || []) as Array<{ tier?: UserTier }>).reduce<UserTier>((selected, row) => {
    const tier = row.tier === 'ultra' || row.tier === 'pro' ? row.tier : 'free';
    return TIER_PRIORITY[tier] > TIER_PRIORITY[selected] ? tier : selected;
  }, 'free');

  await supabase.from('user_profiles').update({ tier: nextTier }).eq('user_id', userId);
}

export async function POST(request: Request) {
  const rawBody = await request.text();
  const signature = request.headers.get('x-razorpay-signature');
  if (!verifyRazorpayWebhookSignature(rawBody, signature)) {
    return NextResponse.json({ error: 'invalid_signature' }, { status: 400 });
  }

  const supabase = createServiceClient();
  if (!supabase) {
    return NextResponse.json({ error: 'Supabase service role key is missing' }, { status: 500 });
  }

  const payload = JSON.parse(rawBody) as Record<string, unknown>;
  const eventId = eventIdFromRequest(rawBody, request);
  const eventType = String(payload.event || 'unknown');
  const subscription = subscriptionFromPayload(payload);
  const subscriptionId = subscription?.id || null;

  const eventInsert = await supabase.from('billing_events').insert([{
    provider: 'razorpay',
    event_id: eventId,
    event_type: eventType,
    provider_subscription_id: subscriptionId,
    payload,
  }]);

  if (eventInsert.error?.code === '23505') {
    return NextResponse.json({ status: 'ok', duplicate: true });
  }
  if (eventInsert.error) {
    return NextResponse.json({ error: 'billing_event_write_failed' }, { status: 500 });
  }

  if (!subscriptionId || !subscription) {
    return NextResponse.json({ status: 'ok', ignored: true });
  }

  const existingRes = await supabase
    .from('billing_subscriptions')
    .select('user_id')
    .eq('provider', 'razorpay')
    .eq('provider_subscription_id', subscriptionId)
    .limit(1)
    .maybeSingle();

  const userId = String(subscription.notes?.user_id || existingRes.data?.user_id || '').trim();
  if (!userId) {
    return NextResponse.json({ status: 'ok', ignored: true, reason: 'missing_user_id' });
  }

  const tier = tierFromSubscription(subscription);
  if (tier !== 'pro' && tier !== 'ultra') {
    return NextResponse.json({ status: 'ok', ignored: true, reason: 'unknown_tier' });
  }

  const status = String(subscription.status || 'created');
  const upsertRes = await supabase.from('billing_subscriptions').upsert([{
    user_id: userId,
    provider: 'razorpay',
    tier,
    billing_period: String(subscription.notes?.billing_period || 'monthly'),
    status,
    provider_plan_id: subscription.plan_id || '',
    provider_subscription_id: subscriptionId,
    provider_customer_id: subscription.customer_id || null,
    current_start: unixToIso(subscription.current_start),
    current_end: unixToIso(subscription.current_end),
    ended_at: unixToIso(subscription.ended_at),
    metadata: { razorpay: subscription, last_event: eventType },
  }], { onConflict: 'provider,provider_subscription_id' });

  if (upsertRes.error) {
    return NextResponse.json({ error: 'billing_subscription_write_failed' }, { status: 500 });
  }

  await syncUserTierFromBilling(supabase, userId);

  return NextResponse.json({ status: 'ok' });
}
