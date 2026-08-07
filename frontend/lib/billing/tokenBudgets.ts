import type { SupabaseClient } from '@supabase/supabase-js';
import { UserRole, UserTier, effectiveRateLimitTier } from './tiers';

export type TokenBudget = {
  dailyTokens: number;
  monthlyTokens: number;
};

export type TokenUsage = {
  provider?: string | null;
  model?: string | null;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
  total_tokens?: number | null;
  calls?: number | null;
};

export type TokenReservation = {
  allowed: boolean;
  requestId: string;
  estimatedTokens: number;
  dailyLimit: number;
  monthlyLimit: number;
  dailyUsed: number;
  monthlyUsed: number;
  dailyRemaining: number;
  monthlyRemaining: number;
};

export const DEFAULT_TOKEN_BUDGETS: Record<UserTier, TokenBudget> = {
  free: { dailyTokens: 25_000, monthlyTokens: 100_000 },
  pro: { dailyTokens: 250_000, monthlyTokens: 2_000_000 },
  ultra: { dailyTokens: 750_000, monthlyTokens: 6_000_000 },
};

function readPositiveInt(name: string, fallback: number): number {
  const value = Number(process.env[name]);
  return Number.isFinite(value) && value > 0 ? Math.floor(value) : fallback;
}

export function tokenLimitsEnabled(): boolean {
  return String(process.env.TOKEN_LIMITS_ENABLED || 'false').trim().toLowerCase() === 'true';
}

export function tokenEstimateCharsPerToken(): number {
  return readPositiveInt('TOKEN_ESTIMATE_CHARS_PER_TOKEN', 4);
}

export function tokenCompletionReserve(): number {
  return readPositiveInt('TOKEN_COMPLETION_RESERVE_TOKENS', 1500);
}

export function getTokenBudget(tier: unknown, role?: unknown): TokenBudget {
  const effectiveTier = effectiveRateLimitTier(tier as UserTier, role as UserRole);
  const defaults = DEFAULT_TOKEN_BUDGETS[effectiveTier];
  const prefix = `TOKEN_BUDGET_${effectiveTier.toUpperCase()}`;
  return {
    dailyTokens: readPositiveInt(`${prefix}_DAILY`, defaults.dailyTokens),
    monthlyTokens: readPositiveInt(`${prefix}_MONTHLY`, defaults.monthlyTokens),
  };
}

export function estimateChatTokens(body: unknown): number {
  const charsPerToken = tokenEstimateCharsPerToken();
  const promptChars = JSON.stringify(body || {}).length;
  return Math.ceil(promptChars / charsPerToken) + tokenCompletionReserve();
}

function readNumber(value: unknown): number {
  const numberValue = Number(value);
  return Number.isFinite(numberValue) ? Math.max(Math.floor(numberValue), 0) : 0;
}

function normalizeReservation(row: Record<string, unknown>, requestId: string, estimatedTokens: number): TokenReservation {
  const dailyLimit = readNumber(row.daily_limit);
  const monthlyLimit = readNumber(row.monthly_limit);
  const dailyUsed = readNumber(row.daily_used);
  const monthlyUsed = readNumber(row.monthly_used);
  return {
    allowed: row.allowed === true,
    requestId,
    estimatedTokens,
    dailyLimit,
    monthlyLimit,
    dailyUsed,
    monthlyUsed,
    dailyRemaining: readNumber(row.daily_remaining ?? dailyLimit - dailyUsed),
    monthlyRemaining: readNumber(row.monthly_remaining ?? monthlyLimit - monthlyUsed),
  };
}

export async function reserveAiTokens(
  supabaseAdmin: SupabaseClient,
  input: {
    userId: string;
    tier: UserTier;
    role?: UserRole;
    requestId: string;
    estimatedTokens: number;
    feature?: string;
    provider?: string;
    model?: string | null;
  },
): Promise<TokenReservation> {
  const budget = getTokenBudget(input.tier, input.role);
  const { data, error } = await supabaseAdmin.rpc('reserve_ai_tokens', {
    p_user_id: input.userId,
    p_tier: effectiveRateLimitTier(input.tier, input.role),
    p_request_id: input.requestId,
    p_estimated_tokens: input.estimatedTokens,
    p_daily_limit: budget.dailyTokens,
    p_monthly_limit: budget.monthlyTokens,
    p_feature: input.feature || 'chat',
    p_provider: input.provider || 'openrouter',
    p_model: input.model || null,
  });

  if (error) throw error;
  const row = Array.isArray(data) ? data[0] : data;
  if (!row) throw new Error('token_reservation_empty');
  return normalizeReservation(row as Record<string, unknown>, input.requestId, input.estimatedTokens);
}

export async function finalizeAiUsage(
  supabaseAdmin: SupabaseClient,
  input: {
    requestId: string;
    usage?: TokenUsage | null;
    success: boolean;
    errorMessage?: string | null;
  },
): Promise<void> {
  const usage = input.usage || {};
  const promptTokens = readNumber(usage.prompt_tokens);
  const completionTokens = readNumber(usage.completion_tokens);
  const totalTokens = readNumber(usage.total_tokens);

  const payload = {
    provider: usage.provider || 'openrouter',
    model: usage.model || null,
    prompt_tokens: promptTokens,
    completion_tokens: completionTokens,
    total_tokens: totalTokens,
    reserved_tokens: 0,
    success: input.success,
    error_message: input.errorMessage || null,
    updated_at: new Date().toISOString(),
  };

  const { error } = await supabaseAdmin
    .from('ai_usage_events')
    .update(payload)
    .eq('request_id', input.requestId);
  if (error) throw error;
}
