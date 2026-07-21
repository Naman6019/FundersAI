import { hasSupabaseBrowserEnv, supabaseBrowser } from '@/lib/supabaseBrowser';

export type FeedbackPayload = {
  feedback_type: 'general' | 'response' | 'logout';
  rating: number;
  comment?: string;
  message_id?: string | null;
  session_id?: string | null;
  trace_id?: string | null;
  page_path?: string;
  response_excerpt?: string;
  website?: string;
};

export async function submitFeedback(payload: FeedbackPayload): Promise<void> {
  let token: string | null = null;
  if (hasSupabaseBrowserEnv) {
    const { data } = await supabaseBrowser.auth.getSession();
    token = data.session?.access_token || null;
  }

  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = `Bearer ${token}`;

  const response = await fetch('/api/feedback', {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error('feedback_submission_failed');
  }
}

