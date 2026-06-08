import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { NextResponse } from 'next/server';
import type { UserRole, UserTier } from '@/lib/billing/tiers';

type ProfileRow = {
  user_id: string;
  role: UserRole;
  tier: UserTier;
  last_active_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type AdminContext = {
  accessToken: string;
  user: {
    id: string;
    email: string | null;
  };
  profile: ProfileRow;
  supabaseAdmin: SupabaseClient | null;
};

type RequireAdminResult =
  | { ok: true; context: AdminContext }
  | { ok: false; response: NextResponse };

function getSupabaseUrl(): string | null {
  return process.env.NEXT_PUBLIC_SUPABASE_URL || null;
}

function getAnonKey(): string | null {
  return process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || null;
}

function getServiceKey(): string | null {
  return process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_KEY || null;
}

function parseBearerToken(request: Request): string | null {
  const authHeader = request.headers.get('authorization') || '';
  if (!authHeader.startsWith('Bearer ')) return null;
  const token = authHeader.slice('Bearer '.length).trim();
  return token || null;
}

function createAnonClient(): SupabaseClient | null {
  const url = getSupabaseUrl();
  const anonKey = getAnonKey();
  if (!url || !anonKey) return null;
  return createClient(url, anonKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

function createServiceClient(): SupabaseClient | null {
  const url = getSupabaseUrl();
  const serviceKey = getServiceKey();
  if (!url || !serviceKey) return null;
  return createClient(url, serviceKey, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

async function fetchOrCreateProfile(
  userId: string,
  supabaseAdmin: SupabaseClient | null,
  supabaseUserContext: SupabaseClient,
): Promise<ProfileRow | null> {
  if (supabaseAdmin) {
    const readRes = await supabaseAdmin
      .from('user_profiles')
      .select('user_id,role,tier,last_active_at,created_at,updated_at')
      .eq('user_id', userId)
      .limit(1)
      .maybeSingle();
    if (readRes.data) return readRes.data as ProfileRow;

    await supabaseAdmin
      .from('user_profiles')
      .upsert([{ user_id: userId, role: 'user', tier: 'free' }], { onConflict: 'user_id' });

    const retryRes = await supabaseAdmin
      .from('user_profiles')
      .select('user_id,role,tier,last_active_at,created_at,updated_at')
      .eq('user_id', userId)
      .limit(1)
      .maybeSingle();
    if (retryRes.data) return retryRes.data as ProfileRow;
  }

  const fallbackRes = await supabaseUserContext
    .from('user_profiles')
    .select('user_id,role,tier,last_active_at,created_at,updated_at')
    .eq('user_id', userId)
    .limit(1)
    .maybeSingle();
  return (fallbackRes.data as ProfileRow | null) || null;
}

export async function requireAdminFromRequest(request: Request): Promise<RequireAdminResult> {
  const token = parseBearerToken(request);
  if (!token) {
    return { ok: false, response: NextResponse.json({ error: 'Unauthorized' }, { status: 401 }) };
  }

  const anonClient = createAnonClient();
  if (!anonClient) {
    return { ok: false, response: NextResponse.json({ error: 'Supabase auth is not configured' }, { status: 500 }) };
  }

  const { data: userData, error: userError } = await anonClient.auth.getUser(token);
  if (userError || !userData?.user) {
    return { ok: false, response: NextResponse.json({ error: 'Unauthorized' }, { status: 401 }) };
  }

  const user = userData.user;
  const scopedClient = createClient(getSupabaseUrl()!, getAnonKey()!, {
    auth: { persistSession: false, autoRefreshToken: false },
    global: { headers: { Authorization: `Bearer ${token}` } },
  });
  const supabaseAdmin = createServiceClient();

  const profile = await fetchOrCreateProfile(user.id, supabaseAdmin, scopedClient);
  if (!profile || profile.role !== 'admin') {
    return { ok: false, response: NextResponse.json({ error: 'Access denied' }, { status: 403 }) };
  }

  return {
    ok: true,
    context: {
      accessToken: token,
      user: { id: user.id, email: user.email ?? null },
      profile,
      supabaseAdmin,
    },
  };
}

export function emptyArray<T = unknown>(): T[] {
  return [];
}

export function utcDayStartIso(now: Date = new Date()): string {
  const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate(), 0, 0, 0, 0));
  return d.toISOString();
}

export function monthStartIso(now: Date = new Date()): string {
  const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1, 0, 0, 0, 0));
  return d.toISOString();
}

export function readNumber(input: unknown): number {
  const value = Number(input);
  return Number.isFinite(value) ? value : 0;
}
