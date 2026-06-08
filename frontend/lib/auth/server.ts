import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { NextResponse } from 'next/server';
import type { UserRole, UserTier } from '@/lib/billing/tiers';

export type ProfileRow = {
  user_id: string;
  role: UserRole;
  tier: UserTier;
  last_active_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type UserContext = {
  token: string;
  user: {
    id: string;
    email: string | null;
  };
  profile: ProfileRow;
  supabaseAdmin: SupabaseClient;
};

function supabaseUrl(): string | null {
  return process.env.NEXT_PUBLIC_SUPABASE_URL || null;
}

function anonKey(): string | null {
  return process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || null;
}

function serviceKey(): string | null {
  return process.env.SUPABASE_SERVICE_ROLE_KEY || process.env.SUPABASE_KEY || null;
}

export function bearerToken(request: Request): string | null {
  const authHeader = request.headers.get('authorization') || '';
  if (!authHeader.startsWith('Bearer ')) return null;
  return authHeader.slice('Bearer '.length).trim() || null;
}

export function createServiceClient(): SupabaseClient | null {
  const url = supabaseUrl();
  const key = serviceKey();
  if (!url || !key) return null;
  return createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
}

export async function fetchOrCreateUserProfile(
  supabaseAdmin: SupabaseClient,
  userId: string,
): Promise<ProfileRow | null> {
  const readRes = await supabaseAdmin
    .from('user_profiles')
    .select('user_id,role,tier,last_active_at,created_at,updated_at')
    .eq('user_id', userId)
    .limit(1)
    .maybeSingle();
  if (readRes.data) return readRes.data as ProfileRow;

  const insertRes = await supabaseAdmin
    .from('user_profiles')
    .insert([{ user_id: userId, role: 'user', tier: 'free' }])
    .select('user_id,role,tier,last_active_at,created_at,updated_at')
    .limit(1)
    .maybeSingle();

  return (insertRes.data as ProfileRow | null) || null;
}

export async function getUserContext(request: Request): Promise<UserContext | null> {
  const token = bearerToken(request);
  const url = supabaseUrl();
  const key = anonKey();
  const supabaseAdmin = createServiceClient();
  if (!token || !url || !key || !supabaseAdmin) return null;

  const anonClient = createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false },
  });
  const { data, error } = await anonClient.auth.getUser(token);
  if (error || !data.user) return null;

  const profile = await fetchOrCreateUserProfile(supabaseAdmin, data.user.id);
  if (!profile) return null;

  return {
    token,
    user: {
      id: data.user.id,
      email: data.user.email ?? null,
    },
    profile,
    supabaseAdmin,
  };
}

export async function requireUserContext(request: Request): Promise<
  | { ok: true; context: UserContext }
  | { ok: false; response: NextResponse }
> {
  const context = await getUserContext(request);
  if (!context) {
    return { ok: false, response: NextResponse.json({ error: 'Unauthorized' }, { status: 401 }) };
  }
  return { ok: true, context };
}
