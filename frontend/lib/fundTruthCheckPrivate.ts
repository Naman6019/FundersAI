import 'server-only';

export function isFundTruthCheckPrivateEnabled(): boolean {
  if (process.env.NODE_ENV !== 'production') return true;
  return process.env.FUND_TRUTH_CHECK_PRIVATE_ENABLED === 'true';
}
