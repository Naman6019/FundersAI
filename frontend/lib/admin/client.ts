'use client';

import { supabaseBrowser } from '@/lib/supabaseBrowser';

export async function adminFetch(path: string): Promise<Response> {
  const { data } = await supabaseBrowser.auth.getSession();
  const accessToken = data.session?.access_token;
  if (!accessToken) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    });
  }
  return fetch(path, {
    cache: 'no-store',
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });
}

