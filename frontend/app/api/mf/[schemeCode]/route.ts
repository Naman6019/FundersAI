import { NextResponse } from 'next/server';
import { enforceRateLimit, getClientIp } from '@/lib/rateLimit';
import { getUserContext } from '@/lib/auth/server';

export const dynamic = 'force-dynamic';

type BackendResult =
  | { kind: 'response'; status: number; payload: unknown }
  | { kind: 'unavailable'; message: string };

function backendUrl(schemeCode: string): string | null {
  if (process.env.NODE_ENV === 'development') {
    return `http://127.0.0.1:8000/api/mf/${schemeCode}`;
  }
  const baseUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');
  return baseUrl ? `${baseUrl}/api/mf/${schemeCode}` : null;
}

async function fetchFromBackend(schemeCode: string, request: Request): Promise<BackendResult> {
  const target = backendUrl(schemeCode);
  if (!target) {
    return { kind: 'unavailable', message: 'FastAPI backend is not configured' };
  }

  try {
    const response = await fetch(target, {
      cache: 'no-store',
      headers: { 'X-Forwarded-For': getClientIp(request) },
    });
    const payload = await response.json().catch(() => null);
    if (payload === null) {
      if (!response.ok) {
        return {
          kind: 'response',
          status: response.status,
          payload: { error: `FastAPI request failed with status ${response.status}` },
        };
      }
      return { kind: 'unavailable', message: 'FastAPI returned an invalid response' };
    }
    return { kind: 'response', status: response.status, payload };
  } catch {
    return { kind: 'unavailable', message: 'FastAPI backend is unavailable' };
  }
}

export async function GET(request: Request, context: { params: Promise<{ schemeCode: string }> }) {
  const { schemeCode } = await context.params;
  if (!/^\d+$/.test(schemeCode)) {
    return NextResponse.json({ error: 'Invalid scheme code' }, { status: 400 });
  }

  try {
    const userContext = await getUserContext(request);
    const limited = await enforceRateLimit(request, 'mf-detail', userContext ? {
      identifier: userContext.user.id,
      tier: userContext.profile.tier,
      role: userContext.profile.role,
    } : {});
    if (limited) return limited;

    const result = await fetchFromBackend(schemeCode, request);
    if (result.kind === 'unavailable') {
      const status = result.message.includes('invalid response') ? 502 : 503;
      return NextResponse.json({ error: result.message }, { status });
    }

    // FastAPI owns NAV history, metrics, freshness, and partial-data semantics.
    return NextResponse.json(result.payload, { status: result.status });
  } catch (error) {
    return NextResponse.json({ error: (error as Error).message }, { status: 500 });
  }
}
