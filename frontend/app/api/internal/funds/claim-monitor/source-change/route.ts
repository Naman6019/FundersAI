import { NextResponse } from 'next/server';
import { createServiceClient } from '@/lib/auth/server';
import { isFundTruthCheckPrivateEnabled } from '@/lib/fundTruthCheckPrivate';
import {
  buildClaimMonitorSnapshot,
  claimAffectedBySourceChanges,
  fetchCanonicalClaimCheck,
  trustedClaimMonitorKey,
  type ClaimSourceChange,
  type ClaimSourceScope,
} from '@/lib/fundTruthMonitor';
import { getClientIp } from '@/lib/rateLimit';

const PRIVATE_HEADERS = {
  'Cache-Control': 'no-store, max-age=0',
  'X-Robots-Tag': 'noindex, nofollow, noarchive',
};
const SOURCE_SCOPES = new Set<ClaimSourceScope>(['nav', 'core', 'holdings', 'sectors', 'documents']);

type ClaimRow = {
  id: string;
  original_text: string;
  normalized_claim: unknown;
  resolved_entities: unknown;
  latest_evidence: unknown;
  latest_source_fingerprint: string | null;
};

function json(body: unknown, status = 200) {
  return NextResponse.json(body, { status, headers: PRIVATE_HEADERS });
}

function parseChanges(value: unknown): ClaimSourceChange[] | null {
  const items = (value as { changes?: unknown })?.changes;
  if (!Array.isArray(items) || items.length < 1 || items.length > 50) return null;
  const changes: ClaimSourceChange[] = [];
  for (const item of items) {
    if (!item || typeof item !== 'object') return null;
    const candidate = item as Record<string, unknown>;
    const schemeCode = String(candidate.scheme_code || '').trim();
    const scope = String(candidate.scope || '') as ClaimSourceScope;
    const sourceFingerprint = String(candidate.source_fingerprint || '').trim().toLowerCase();
    if (!/^\d{1,12}$/.test(schemeCode) || !SOURCE_SCOPES.has(scope) || !/^[a-f0-9]{64}$/.test(sourceFingerprint)) return null;
    changes.push({ scheme_code: schemeCode, scope, source_fingerprint: sourceFingerprint });
  }
  return changes;
}

function trackedMetrics(normalizedClaim: unknown): string[] {
  if (!normalizedClaim || typeof normalizedClaim !== 'object') return [];
  const claims = (normalizedClaim as { claims?: unknown }).claims;
  if (!Array.isArray(claims)) return [];
  return claims
    .map((claim) => (claim && typeof claim === 'object' ? String((claim as { metric?: unknown }).metric || '') : ''))
    .filter(Boolean);
}

export async function POST(request: Request) {
  if (!isFundTruthCheckPrivateEnabled()) return json({ error: 'Not Found' }, 404);
  if (!trustedClaimMonitorKey(request.headers.get('x-internal-claim-monitor-key'))) {
    return json({ error: 'Not Found' }, 404);
  }

  const changes = parseChanges(await request.json().catch(() => null));
  if (!changes) return json({ error: 'invalid_source_changes' }, 400);
  const supabase = createServiceClient();
  if (!supabase) return json({ error: 'claim_monitor_storage_unavailable' }, 503);

  const { data: claimData, error: claimError } = await supabase.rpc(
    'list_active_research_claims_for_source_change',
    { p_limit: 200 },
  );
  if (claimError) return json({ error: 'claim_monitor_storage_unavailable' }, 503);
  const claims = (claimData || []) as ClaimRow[];
  if (!claims.length) return json({ matched: 0, evaluated: 0, appended: 0, unchanged: 0, failed: 0, truncated: false });
  const affected = claims.map((claim) => {
    const relevantChanges = changes.filter((change) => claimAffectedBySourceChanges(
      claim.normalized_claim,
      claim.resolved_entities,
      claim.latest_evidence || [],
      [change],
    ));
    return { claim, relevantChanges };
  }).filter((item) => item.relevantChanges.length > 0);

  const candidates = affected.slice(0, 20);
  const counters = { evaluated: 0, appended: 0, unchanged: 0, failed: 0 };
  for (let start = 0; start < candidates.length; start += 4) {
    const batch = candidates.slice(start, start + 4);
    const outcomes = await Promise.all(batch.map(async ({ claim, relevantChanges }) => {
      try {
        const result = await fetchCanonicalClaimCheck(claim.original_text, getClientIp(request), { bypassCache: true });
        const snapshot = buildClaimMonitorSnapshot(result, {
          requireTrackable: false,
          trackedMetrics: trackedMetrics(claim.normalized_claim),
          fallbackSourceFingerprints: relevantChanges.map((change) => change.source_fingerprint),
        });
        if (snapshot.sourceFingerprint === claim.latest_source_fingerprint) return 'unchanged' as const;
        const { error } = await supabase.from('research_claim_evaluations').insert({
          claim_id: claim.id,
          verdict: snapshot.verdict,
          freshness: snapshot.freshness,
          result: snapshot.result,
          evidence: snapshot.evidence,
          source_fingerprint: snapshot.sourceFingerprint,
        });
        if (error?.code === '23505') return 'unchanged' as const;
        return error ? 'failed' as const : 'appended' as const;
      } catch {
        return 'failed' as const;
      }
    }));
    outcomes.forEach((outcome) => {
      counters.evaluated += 1;
      counters[outcome] += 1;
    });
  }

  return json({
    matched: affected.length,
    ...counters,
    truncated: affected.length > candidates.length,
  });
}
