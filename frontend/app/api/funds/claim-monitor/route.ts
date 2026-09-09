import { NextResponse } from 'next/server';
import { requireUserContext, type UserContext } from '@/lib/auth/server';
import { isFundTruthCheckPrivateEnabled } from '@/lib/fundTruthCheckPrivate';
import {
  buildClaimMonitorSnapshot,
  ClaimMonitorError,
  fetchCanonicalClaimCheck,
} from '@/lib/fundTruthMonitor';
import { enforceRateLimit, getClientIp } from '@/lib/rateLimit';

const PRIVATE_HEADERS = {
  'Cache-Control': 'no-store, max-age=0',
  'X-Robots-Tag': 'noindex, nofollow, noarchive',
};

type StorageError = { code?: string } | null | undefined;

type ClaimRow = {
  id: string;
  original_text: string;
  normalized_claim: unknown;
  resolved_entities: unknown;
  active: boolean;
  created_at: string;
};

type EvaluationRow = {
  id: string;
  claim_id: string;
  verdict: string;
  freshness: string;
  result: unknown;
  evidence: unknown;
  source_fingerprint: string;
  evaluated_at: string;
};

function json(body: unknown, status = 200) {
  return NextResponse.json(body, { status, headers: PRIVATE_HEADERS });
}

function privateResponse<T extends Response>(response: T): T {
  Object.entries(PRIVATE_HEADERS).forEach(([name, value]) => response.headers.set(name, value));
  return response;
}

function storageUnavailable(error: StorageError): boolean {
  return ['42P01', '42883', 'PGRST202', 'PGRST205'].includes(String(error?.code || ''));
}

async function authenticate(request: Request) {
  try {
    return await requireUserContext(request);
  } catch {
    return { ok: false as const, response: json({ error: 'authentication_unavailable' }, 503) };
  }
}

async function applyRateLimit(request: Request, user: UserContext['user'], profile: UserContext['profile']) {
  const limited = await enforceRateLimit(request, 'claim-monitor', {
    identifier: user.id,
    tier: profile.tier,
    role: profile.role,
  });
  return limited ? privateResponse(limited) : null;
}

export async function GET(request: Request) {
  if (!isFundTruthCheckPrivateEnabled()) return json({ error: 'Not Found' }, 404);
  const auth = await authenticate(request);
  if (!auth.ok) return privateResponse(auth.response);
  const limited = await applyRateLimit(request, auth.context.user, auth.context.profile);
  if (limited) return limited;

  try {
    const { data: claimData, error: claimError } = await auth.context.supabaseUser
      .from('research_claims')
      .select('id,original_text,normalized_claim,resolved_entities,active,created_at')
      .order('created_at', { ascending: false })
      .limit(100);
    if (claimError) {
      return json({ error: storageUnavailable(claimError) ? 'claim_monitor_storage_unavailable' : 'claim_monitor_read_failed' }, storageUnavailable(claimError) ? 503 : 500);
    }

    const claims = (claimData || []) as ClaimRow[];
    const claimIds = claims.map((claim) => claim.id);
    let evaluations: EvaluationRow[] = [];
    if (claimIds.length) {
      const { data, error } = await auth.context.supabaseUser
        .from('research_claim_evaluations')
        .select('id,claim_id,verdict,freshness,result,evidence,source_fingerprint,evaluated_at')
        .in('claim_id', claimIds)
        .order('evaluated_at', { ascending: false })
        .limit(500);
      if (error) {
        return json({ error: storageUnavailable(error) ? 'claim_monitor_storage_unavailable' : 'claim_monitor_read_failed' }, storageUnavailable(error) ? 503 : 500);
      }
      evaluations = (data || []) as EvaluationRow[];
    }

    return json({
      claims: claims.map((claim) => {
        const history = evaluations.filter((evaluation) => evaluation.claim_id === claim.id).slice(0, 20);
        return {
          ...claim,
          latest_evaluation: history[0] || null,
          evaluations: history,
        };
      }),
    });
  } catch (error) {
    console.error('Claim monitor read failed:', error);
    return json({ error: 'claim_monitor_read_failed' }, 500);
  }
}

export async function POST(request: Request) {
  if (!isFundTruthCheckPrivateEnabled()) return json({ error: 'Not Found' }, 404);
  const auth = await authenticate(request);
  if (!auth.ok) return privateResponse(auth.response);
  const limited = await applyRateLimit(request, auth.context.user, auth.context.profile);
  if (limited) return limited;

  const body: unknown = await request.json().catch(() => null);
  const input = typeof (body as { input?: unknown })?.input === 'string'
    ? (body as { input: string }).input.trim()
    : '';
  if (input.length < 3 || input.length > 2_000) {
    return json({ error: 'input_must_be_between_3_and_2000_characters' }, 400);
  }

  try {
    const result = await fetchCanonicalClaimCheck(input, getClientIp(request));
    const snapshot = buildClaimMonitorSnapshot(result);
    const { data, error } = await auth.context.supabaseAdmin.rpc('save_research_claim_with_evaluation', {
      p_user_id: auth.context.user.id,
      p_original_text: input,
      p_normalized_claim: snapshot.normalizedClaim,
      p_resolved_entities: snapshot.resolvedEntities,
      p_verdict: snapshot.verdict,
      p_freshness: snapshot.freshness,
      p_result: snapshot.result,
      p_evidence: snapshot.evidence,
      p_source_fingerprint: snapshot.sourceFingerprint,
    });
    if (error || !data) {
      console.error('Claim monitor save failed:', error?.code || 'missing_result');
      return json({ error: storageUnavailable(error) ? 'claim_monitor_storage_unavailable' : 'claim_monitor_save_failed' }, storageUnavailable(error) ? 503 : 500);
    }
    return json({
      claim_id: String(data),
      evaluation: {
        verdict: snapshot.verdict,
        freshness: snapshot.freshness,
        source_fingerprint: snapshot.sourceFingerprint,
      },
    }, 201);
  } catch (error) {
    if (error instanceof ClaimMonitorError) return json({ error: error.code }, error.status);
    console.error('Claim monitor evaluation failed:', error);
    return json({ error: 'claim_monitor_save_failed' }, 500);
  }
}
