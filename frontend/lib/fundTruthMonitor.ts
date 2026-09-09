import 'server-only';

import { createHash, timingSafeEqual } from 'node:crypto';
import type {
  AtomicClaim,
  ClaimCheckResponse,
  ClaimEvidence,
  ClaimFreshness,
  ClaimVerdict,
  ResolvedEntity,
} from '@/components/truth-check/types';

export type ClaimSourceScope = 'nav' | 'core' | 'holdings' | 'sectors' | 'documents';

export type ClaimSourceChange = {
  scheme_code: string;
  scope: ClaimSourceScope;
  source_fingerprint: string;
};

export type ClaimMonitorSnapshot = {
  normalizedClaim: {
    version: 1;
    claims: Array<{
      statement: string;
      metric: string;
      operator: string | null;
      source_scopes: ClaimSourceScope[];
    }>;
  };
  resolvedEntities: ResolvedEntity[];
  verdict: ClaimVerdict;
  freshness: ClaimFreshness;
  result: ClaimCheckResponse;
  evidence: ClaimEvidence[];
  sourceFingerprint: string;
};

type SnapshotOptions = {
  requireTrackable?: boolean;
  trackedMetrics?: string[];
  fallbackSourceFingerprints?: string[];
};

const SOURCE_SCOPES_BY_METRIC: Record<string, ClaimSourceScope[]> = {
  expense_ratio: ['core'],
  aum: ['core'],
  cagr: ['nav'],
  rolling_return: ['nav'],
  sharpe_ratio: ['nav'],
  max_drawdown: ['nav'],
  volatility: ['nav'],
  riskometer: ['core'],
  benchmark: ['core'],
  fund_manager: ['core'],
  holds_stock: ['holdings'],
  stock_exposure: ['holdings'],
  sector_exposure: ['sectors'],
  holdings_concentration: ['holdings'],
  portfolio_overlap: ['holdings'],
  investment_objective: ['core', 'documents'],
};

export class ClaimMonitorError extends Error {
  constructor(public readonly code: string, public readonly status: number) {
    super(code);
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function isClaimCheckResponse(value: unknown): value is ClaimCheckResponse {
  if (!isRecord(value) || typeof value.input !== 'string' || typeof value.generated_at !== 'string') return false;
  if (!Array.isArray(value.resolved_entities) || !Array.isArray(value.claims)) return false;
  return value.claims.every((claim) => (
    isRecord(claim)
    && typeof claim.statement === 'string'
    && typeof claim.status === 'string'
    && typeof claim.verdict === 'string'
    && typeof claim.freshness === 'string'
    && typeof claim.trackable === 'boolean'
    && Array.isArray(claim.evidence)
  ));
}

function sourceScopes(claim: AtomicClaim): ClaimSourceScope[] {
  return claim.metric ? SOURCE_SCOPES_BY_METRIC[claim.metric] || [] : [];
}

function trackableClaims(result: ClaimCheckResponse): AtomicClaim[] {
  return result.claims.filter((claim) => (
    claim.trackable
    && claim.status === 'evaluated'
    && Boolean(claim.metric)
    && claim.evidence.length > 0
    && claim.evidence.every((item) => Boolean(item.source_fingerprint))
  ));
}

function aggregateVerdict(claims: AtomicClaim[]): ClaimVerdict {
  const values = new Set(claims.map((claim) => claim.verdict));
  return values.size === 1 ? claims[0].verdict : 'mixed';
}

function aggregateFreshness(claims: AtomicClaim[]): ClaimFreshness {
  if (claims.some((claim) => claim.freshness === 'unknown')) return 'unknown';
  if (claims.some((claim) => claim.freshness === 'stale')) return 'stale';
  return 'current';
}

function uniqueEvidence(claims: AtomicClaim[]): ClaimEvidence[] {
  const result = new Map<string, ClaimEvidence>();
  claims.forEach((claim) => claim.evidence.forEach((item) => {
    if (item.source_fingerprint) result.set(item.source_fingerprint, item);
  }));
  return Array.from(result.values());
}

export function buildClaimMonitorSnapshot(value: unknown, options: SnapshotOptions = {}): ClaimMonitorSnapshot {
  if (!isClaimCheckResponse(value)) {
    throw new ClaimMonitorError('invalid_claim_check_response', 502);
  }
  const trackedMetrics = new Set(options.trackedMetrics || []);
  const claims = options.requireTrackable === false
    ? value.claims.filter((claim) => (
      claim.status === 'evaluated'
      && Boolean(claim.metric)
      && (!trackedMetrics.size || trackedMetrics.has(claim.metric as string))
    ))
    : trackableClaims(value);
  if (!claims.length) {
    throw new ClaimMonitorError('claim_not_trackable', 422);
  }

  const normalizedClaims = claims.map((claim) => ({
    statement: claim.statement,
    metric: claim.metric as string,
    operator: claim.operator,
    source_scopes: sourceScopes(claim),
  }));
  let sourceFingerprints = claims.flatMap((claim) => claim.evidence
    .filter((item) => Boolean(item.source_fingerprint))
    .map((item) => item.source_fingerprint as string));
  sourceFingerprints = Array.from(new Set(sourceFingerprints)).sort();
  if (!sourceFingerprints.length) {
    sourceFingerprints = Array.from(new Set((options.fallbackSourceFingerprints || []).filter(Boolean))).sort();
  }
  if (!sourceFingerprints.length) throw new ClaimMonitorError('claim_not_trackable', 422);
  const sourceFingerprint = createHash('sha256')
    .update(JSON.stringify(sourceFingerprints))
    .digest('hex');

  return {
    normalizedClaim: { version: 1, claims: normalizedClaims },
    resolvedEntities: value.resolved_entities,
    verdict: aggregateVerdict(claims),
    freshness: aggregateFreshness(claims),
    result: value,
    evidence: uniqueEvidence(claims),
    sourceFingerprint,
  };
}

export function claimAffectedBySourceChanges(
  normalizedClaim: unknown,
  resolvedEntities: unknown,
  currentEvidence: unknown,
  changes: ClaimSourceChange[],
): boolean {
  if (!isRecord(normalizedClaim) || !Array.isArray(normalizedClaim.claims) || !Array.isArray(resolvedEntities)) return false;
  const scopes = new Set(
    normalizedClaim.claims.flatMap((claim) => (
      isRecord(claim) && Array.isArray(claim.source_scopes)
        ? claim.source_scopes.filter((scope): scope is ClaimSourceScope => typeof scope === 'string')
        : []
    )),
  );
  const schemeCodes = new Set(
    resolvedEntities
      .filter(isRecord)
      .map((entity) => String(entity.scheme_code || ''))
      .filter(Boolean),
  );
  const evidenceFingerprints = new Set(
    (Array.isArray(currentEvidence) ? currentEvidence : [])
      .filter(isRecord)
      .map((item) => String(item.source_fingerprint || ''))
      .filter(Boolean),
  );
  return changes.some((change) => (
    schemeCodes.has(change.scheme_code)
    && scopes.has(change.scope)
    && !evidenceFingerprints.has(change.source_fingerprint)
  ));
}

export function trustedClaimMonitorKey(presented: string | null): boolean {
  const configured = String(process.env.CLAIM_MONITOR_INTERNAL_KEY || '').trim();
  const candidate = String(presented || '').trim();
  if (!configured || !candidate) return false;
  const left = Buffer.from(configured);
  const right = Buffer.from(candidate);
  return left.length === right.length && timingSafeEqual(left, right);
}

export async function fetchCanonicalClaimCheck(
  input: string,
  clientIp: string,
  options: { bypassCache?: boolean } = {},
): Promise<ClaimCheckResponse> {
  const proxyKey = String(process.env.CLAIM_CHECK_INTERNAL_PROXY_KEY || '').trim();
  const targetBase = String(
    process.env.BACKEND_API_URL
      || process.env.NEXT_PUBLIC_API_URL
      || (process.env.NODE_ENV === 'development' ? 'http://127.0.0.1:8000' : ''),
  ).replace(/\/$/, '');
  if (!proxyKey || !targetBase) throw new ClaimMonitorError('claim_check_unavailable', 503);

  let response: Response;
  try {
    response = await fetch(`${targetBase}/api/funds/claim-check`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-Proxy-Key': proxyKey,
        'X-Forwarded-For': clientIp,
        ...(options.bypassCache ? { 'X-Claim-Check-Cache': 'bypass' } : {}),
      },
      body: JSON.stringify({ input }),
      cache: 'no-store',
      signal: AbortSignal.timeout(15_000),
    });
  } catch {
    throw new ClaimMonitorError('claim_check_unavailable', 502);
  }
  if (!response.ok) {
    throw new ClaimMonitorError(response.status === 429 ? 'rate_limited' : 'claim_check_unavailable', response.status === 429 ? 429 : 502);
  }
  const payload: unknown = await response.json().catch(() => null);
  if (!isClaimCheckResponse(payload)) throw new ClaimMonitorError('invalid_claim_check_response', 502);
  return payload;
}
