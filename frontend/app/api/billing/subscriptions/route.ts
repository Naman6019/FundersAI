import { NextResponse } from 'next/server';
import { fetchOrCreateUserProfile, getUserContext } from '@/lib/auth/server';
import { MONTHLY_TIERS, isPaidTier } from '@/lib/billing/tiers';
import { createRazorpaySubscription, publicRazorpayKeyId, unixToIso } from '@/lib/billing/razorpay';

export async function GET(request: Request) {
  const context = await getUserContext(request);
  if (!context) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const profile = await fetchOrCreateUserProfile(context.supabaseAdmin, context.user.id);
  const subscriptionRes = await context.supabaseAdmin
    .from('billing_subscriptions')
    .select('tier,billing_period,status,provider_subscription_id,provider_plan_id,current_start,current_end,ended_at,created_at,updated_at')
    .eq('user_id', context.user.id)
    .order('created_at', { ascending: false })
    .limit(1)
    .maybeSingle();

  return NextResponse.json({
    status: 'ok',
    profile: {
      tier: profile?.tier || 'free',
      role: profile?.role || 'user',
    },
    subscription: subscriptionRes.data || null,
    tiers: MONTHLY_TIERS,
  });
}

export async function POST(request: Request) {
  const context = await getUserContext(request);
  if (!context) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const body = await request.json().catch(() => ({}));
  const tier = body?.tier;
  if (!isPaidTier(tier)) {
    return NextResponse.json({ error: 'invalid_tier' }, { status: 400 });
  }

  const liveSubscriptionRes = await context.supabaseAdmin
    .from('billing_subscriptions')
    .select('tier,status,provider_subscription_id,provider_plan_id,current_end')
    .eq('user_id', context.user.id)
    .in('status', ['created', 'authenticated', 'active', 'pending', 'halted'])
    .order('created_at', { ascending: false })
    .limit(1)
    .maybeSingle();

  if (liveSubscriptionRes.data?.provider_subscription_id) {
    return NextResponse.json({
      error: 'subscription_already_exists',
      subscription: liveSubscriptionRes.data,
    }, { status: 409 });
  }

  try {
    const subscription = await createRazorpaySubscription({
      tier,
      userId: context.user.id,
      email: context.user.email,
    });

    const tierConfig = MONTHLY_TIERS[tier];
    const upsertRes = await context.supabaseAdmin
      .from('billing_subscriptions')
      .upsert([{
        user_id: context.user.id,
        provider: 'razorpay',
        tier,
        billing_period: tierConfig.billingPeriod,
        status: subscription.status,
        provider_plan_id: subscription.plan_id || '',
        provider_subscription_id: subscription.id,
        provider_customer_id: subscription.customer_id || null,
        current_start: unixToIso(subscription.current_start),
        current_end: unixToIso(subscription.current_end),
        ended_at: unixToIso(subscription.ended_at),
        metadata: { razorpay: subscription },
      }], { onConflict: 'provider,provider_subscription_id' });

    if (upsertRes.error) {
      return NextResponse.json({ error: 'billing_record_write_failed' }, { status: 500 });
    }

    return NextResponse.json({
      status: 'ok',
      checkout: {
        key: publicRazorpayKeyId(),
        subscription_id: subscription.id,
        name: 'FundersAI',
        description: `${tierConfig.name} subscription`,
        prefill: { email: context.user.email || '' },
        notes: {
          user_id: context.user.id,
          tier,
          billing_period: tierConfig.billingPeriod,
        },
      },
      subscription: {
        id: subscription.id,
        status: subscription.status,
        short_url: subscription.short_url || null,
      },
    });
  } catch (error) {
    console.error('Razorpay subscription create failed:', error);
    return NextResponse.json({ error: 'razorpay_subscription_create_failed' }, { status: 502 });
  }
}
