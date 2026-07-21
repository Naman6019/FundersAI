'use client';

import { useState } from 'react';
import { ThumbsDown, ThumbsUp } from 'lucide-react';
import { feedbackErrorMessage, submitFeedback } from '@/lib/feedback';

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

type ResponseFeedbackProps = {
  messageId: string;
  sessionId: string | null;
  traceId: string | null;
  responseExcerpt: string;
};

export default function ResponseFeedback({ messageId, sessionId, traceId, responseExcerpt }: ResponseFeedbackProps) {
  const [rating, setRating] = useState<1 | 5 | null>(null);
  const [comment, setComment] = useState('');
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');
  const persistedMessageId = UUID_PATTERN.test(messageId) ? messageId : null;

  if (!persistedMessageId && !traceId) return null;
  if (status === 'sent') return <p className="mt-3 border-t border-white/5 pt-3 text-[11px] text-emerald-300">Thanks for rating this response.</p>;

  const send = async () => {
    if (!rating || status === 'sending') return;
    setStatus('sending');
    setErrorMessage('');
    try {
      await submitFeedback({
        feedback_type: 'response',
        rating,
        comment,
        message_id: persistedMessageId,
        session_id: sessionId,
        trace_id: traceId,
        page_path: window.location.pathname,
        response_excerpt: responseExcerpt.slice(0, 1000),
      });
      setStatus('sent');
    } catch (error) {
      setErrorMessage(feedbackErrorMessage(error));
      setStatus('error');
    }
  };

  return (
    <div className="mt-3 border-t border-white/5 pt-3">
      <div className="flex items-center gap-2">
        <span className="text-[11px] text-slate-500">Was this response useful?</span>
        <button type="button" onClick={() => setRating(5)} aria-label="Helpful response" aria-pressed={rating === 5} className={`rounded-lg p-1.5 transition ${rating === 5 ? 'bg-emerald-400/15 text-emerald-300' : 'text-slate-500 hover:bg-white/5 hover:text-slate-200'}`}>
          <ThumbsUp className="h-3.5 w-3.5" />
        </button>
        <button type="button" onClick={() => setRating(1)} aria-label="Unhelpful response" aria-pressed={rating === 1} className={`rounded-lg p-1.5 transition ${rating === 1 ? 'bg-rose-400/15 text-rose-300' : 'text-slate-500 hover:bg-white/5 hover:text-slate-200'}`}>
          <ThumbsDown className="h-3.5 w-3.5" />
        </button>
      </div>
      {rating ? (
        <div className="mt-2 rounded-xl border border-white/10 bg-black/20 p-3">
          <textarea value={comment} onChange={(event) => setComment(event.target.value.slice(0, 2000))} rows={2} placeholder="Optional: what worked or what should change?" className="w-full resize-none bg-transparent text-xs text-slate-200 outline-none placeholder:text-slate-600" />
          {status === 'error' ? <p role="alert" className="mb-2 text-[11px] text-rose-300">{errorMessage}</p> : null}
          <div className="flex justify-end">
            <button type="button" onClick={send} disabled={status === 'sending'} className="rounded-lg bg-white/10 px-3 py-1.5 text-[11px] font-semibold text-slate-200 hover:bg-white/15 disabled:opacity-50">
              {status === 'sending' ? 'Sending…' : 'Send response feedback'}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
