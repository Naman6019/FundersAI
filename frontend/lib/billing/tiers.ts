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
    description: 'Starter research limits for fund research & synthesis reports.',
    features: [
      '1 report per day (Synthesis Studio)',
      'Token-based queries in Research platform (25k daily / 100k monthly)',
      'Full dashboard & fact-sheet research access',
    ],
  },
  pro: {
    tier: 'pro',
    name: 'Pro',
    priceLabel: '₹99/month',
    amountPaise: 9900,
    billingPeriod: 'monthly',
    description: 'Higher limits for regular mutual-fund and stock research.',
    features: [
      '5 reports per day (Synthesis Studio)',
      '10X Higher usage in Research platform (250k daily / 2M monthly)',
      'Dashboard, Canvas & Portfolio Overlap Tool access',
    ],
  },
  ultra: {
    tier: 'ultra',
    name: 'Ultra',
    priceLabel: '₹199/month',
    amountPaise: 19900,
    billingPeriod: 'monthly',
    description: 'Highest limits for heavy research workflows.',
    features: [
      '15 reports per day (Synthesis Studio)',
      '25X Higher usage than Free in Research platform (750k daily / 6M monthly)',
      'Priority token budget & direct serverless PDF exports',
    ],
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
