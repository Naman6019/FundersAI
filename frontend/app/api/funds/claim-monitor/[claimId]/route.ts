import { NextResponse } from 'next/server';
import { requireUserContext } from '@/lib/auth/server';
import { isFundTruthCheckPrivateEnabled } from '@/lib/fundTruthCheckPrivate';
import { enforceRateLimit } from '@/lib/rateLimit';

const PRIVATE_HEADERS = {
  'Cache-Control': 'no-store, max-age=0',
  'X-Robots-Tag': 'noindex, nofollow, noarchive',
};

type Params = { claimId: string };

function json(body: unknown, status = 200) {
  return NextResponse.json(body, { status, headers: PRIVATE_HEADERS });
}

function isUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}

export async function PATCH(request: Request, { params }: { params: Promise<Params> }) {
  if (!isFundTruthCheckPrivateEnabled()) return json({ error: 'Not Found' }, 404);

  let auth;
  try {
    auth = await requireUserContext(request);
  } catch {
    return json({ error: 'authentication_unavailable' }, 503);
  }
  if (!auth.ok) {
    Object.entries(PRIVATE_HEADERS).forEach(([name, value]) => auth.response.headers.set(name, value));
    return auth.response;
  }

  const limited = await enforceRateLimit(request, 'claim-monitor', {
    identifier: auth.context.user.id,
    tier: auth.context.profile.tier,
    role: auth.context.profile.role,
  });
  if (limited) {
    Object.entries(PRIVATE_HEADERS).forEach(([name, value]) => limited.headers.set(name, value));
    return limited;
  }

  const { claimId } = await params;
  if (!isUuid(claimId)) return json({ error: 'invalid_claim_id' }, 400);
  const body: unknown = await request.json().catch(() => null);
  if (typeof (body as { active?: unknown })?.active !== 'boolean') {
    return json({ error: 'active_must_be_boolean' }, 400);
  }

  try {
    const { data, error } = await auth.context.supabaseUser
      .from('research_claims')
      .update({ active: (body as { active: boolean }).active })
      .eq('id', claimId)
      .select('id,active')
      .maybeSingle();
    if (error) {
      const unavailable = ['42P01', 'PGRST205'].includes(String(error.code || ''));
      return json({ error: unavailable ? 'claim_monitor_storage_unavailable' : 'claim_monitor_update_failed' }, unavailable ? 503 : 500);
    }
    if (!data) return json({ error: 'claim_not_found' }, 404);
    return json({ claim: data });
  } catch (error) {
    console.error('Claim monitor update failed:', error);
    return json({ error: 'claim_monitor_update_failed' }, 500);
  }
}
