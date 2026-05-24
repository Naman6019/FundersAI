'use client';

import { supabaseBrowser } from '@/lib/supabaseBrowser';

export async function adminFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const { data } = await supabaseBrowser.auth.getSession();
  const accessToken = data.session?.access_token;
  if (!accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }
  const headers = new Headers(init.headers);
  headers.set('Authorization', `Bearer ${accessToken}`);

  return fetch(path, {
    ...init,
    cache: 'no-store',
    headers,
  });
}
