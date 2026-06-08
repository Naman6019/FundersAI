export type UserRole = 'user' | 'admin' | 'tester';
export type UserTier = 'free' | 'pro' | 'ultra';
export type PaidTier = 'pro' | 'ultra';
export type BillingPeriod = 'monthly' | 'annual' | 'lifetime';

export type TierDefinition = {
  tier: UserTier;
  name: string;
  priceLabel: string;
  amountPaise: number;
  billingPeriod: BillingPeriod;
  description: string;
  features: string[];
};

export const TIER_PRIORITY: Record<UserTier, number> = {
  free: 0,
  pro: 1,
  ultra: 2,
};

export const MONTHLY_TIERS: Record<UserTier, TierDefinition> = {
  free: {
    tier: 'free',
    name: 'Free',
    priceLabel: '₹0',
    amountPaise: 0,
    billingPeriod: 'monthly',
    description: 'Full dashboard access with starter research limits.',
    features: ['10 chat requests per day', 'Basic search and comparison access', 'Research-only output'],
  },
  pro: {
    tier: 'pro',
    name: 'Pro',
    priceLabel: '₹99/month',
    amountPaise: 9900,
    billingPeriod: 'monthly',
    description: 'Higher limits for regular mutual-fund and stock research.',
    features: ['100 chat requests per day', 'Higher research route limits', 'Dashboard and canvas access'],
  },
  ultra: {
    tier: 'ultra',
    name: 'Ultra',
    priceLabel: '₹149/month',
    amountPaise: 14900,
    billingPeriod: 'monthly',
    description: 'Highest limits for heavy research workflows.',
    features: ['300 chat requests per day', 'Ultra research route limits', 'Priority-sized usage buckets'],
  },
};

export function normalizeTier(value: unknown): UserTier {
  return value === 'pro' || value === 'ultra' ? value : 'free';
}

export function isPaidTier(value: unknown): value is PaidTier {
  return value === 'pro' || value === 'ultra';
}

export function effectiveRateLimitTier(tier: unknown, role?: unknown): UserTier {
  if (role === 'admin' || role === 'tester') return 'ultra';
  return normalizeTier(tier);
}
