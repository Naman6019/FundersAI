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

export class FeedbackSubmissionError extends Error {
  constructor(
    public readonly code: string,
    public readonly status: number,
  ) {
    super(code);
    this.name = 'FeedbackSubmissionError';
  }
}

export function feedbackErrorMessage(error: unknown): string {
  if (error instanceof FeedbackSubmissionError) {
    if (error.code === 'feedback_storage_unavailable') {
      return 'Feedback storage is temporarily unavailable. Please try again shortly.';
    }
    if (error.code === 'rate_limited') {
      return 'Too many feedback attempts. Please wait a moment and try again.';
    }
  }
  return 'Feedback could not be saved. Please try again.';
}

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
    const data = await response.json().catch(() => null);
    throw new FeedbackSubmissionError(
      typeof data?.error === 'string' ? data.error : 'feedback_submission_failed',
      response.status,
    );
  }
}
