'use client';

import { useEffect, useState } from 'react';
import { MessageSquareText, Star, X } from 'lucide-react';
import { feedbackErrorMessage, submitFeedback } from '@/lib/feedback';

const PROMPT_SEEN_KEY = 'fundersai-feedback-prompt-seen';

export default function FeedbackPrompt() {
  const [open, setOpen] = useState(false);
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    if (window.sessionStorage.getItem(PROMPT_SEEN_KEY) === '1') return;
    const timer = window.setTimeout(() => {
      window.sessionStorage.setItem(PROMPT_SEEN_KEY, '1');
      setOpen(true);
    }, 1200);
    return () => window.clearTimeout(timer);
  }, []);

  const send = async () => {
    if (!rating || status === 'sending') return;
    setStatus('sending');
    setErrorMessage('');
    try {
      await submitFeedback({
        feedback_type: 'general',
        rating,
        comment,
        page_path: window.location.pathname,
      });
      setStatus('sent');
    } catch (error) {
      setErrorMessage(feedbackErrorMessage(error));
      setStatus('error');
    }
  };

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-5 right-5 z-50 inline-flex items-center gap-2 rounded-full border border-[#66a3ff]/30 bg-[#0b1325]/95 px-4 py-2.5 text-xs font-semibold text-slate-100 shadow-2xl backdrop-blur-xl transition hover:border-[#66a3ff]/60"
        aria-label="Open app feedback"
      >
        <MessageSquareText className="h-4 w-4 text-[#66a3ff]" /> Feedback
      </button>
    );
  }

  return (
    <aside
      role="dialog"
      aria-label="Share app feedback"
      className="fixed bottom-5 right-5 z-50 w-[min(380px,calc(100vw-2rem))] rounded-2xl border border-white/10 bg-[#0b1325]/95 p-5 text-white shadow-2xl backdrop-blur-xl"
    >
      <button type="button" onClick={() => setOpen(false)} className="absolute right-3 top-3 rounded-lg p-1.5 text-slate-400 hover:bg-white/10 hover:text-white" aria-label="Close feedback">
        <X className="h-4 w-4" />
      </button>
      {status === 'sent' ? (
        <div className="pr-6">
          <h2 className="text-sm font-semibold">Thanks for helping improve FundersAI.</h2>
          <p className="mt-2 text-xs leading-5 text-slate-400">Your feedback has been recorded.</p>
        </div>
      ) : (
        <>
          <h2 className="pr-7 text-sm font-semibold">How is FundersAI working for you?</h2>
          <p className="mt-1 text-xs leading-5 text-slate-400">Rate the app and optionally share what felt useful or confusing.</p>
          <div className="mt-4 flex gap-1" aria-label="App rating">
            {[1, 2, 3, 4, 5].map((value) => (
              <button key={value} type="button" onClick={() => setRating(value)} className="rounded-lg p-1.5 hover:bg-white/10" aria-label={`${value} star${value === 1 ? '' : 's'}`} aria-pressed={rating === value}>
                <Star className={`h-5 w-5 ${value <= rating ? 'fill-amber-300 text-amber-300' : 'text-slate-600'}`} />
              </button>
            ))}
          </div>
          <textarea
            value={comment}
            onChange={(event) => setComment(event.target.value.slice(0, 2000))}
            rows={3}
            placeholder="Optional: tell us what you think about the app"
            className="mt-3 w-full resize-none rounded-xl border border-white/10 bg-black/25 px-3 py-2 text-xs text-slate-100 outline-none placeholder:text-slate-600 focus:border-[#66a3ff]/60"
          />
          {status === 'error' ? <p role="alert" className="mt-2 text-xs text-rose-300">{errorMessage}</p> : null}
          <div className="mt-3 flex items-center justify-end gap-2">
            <button type="button" onClick={() => setOpen(false)} className="rounded-lg px-3 py-2 text-xs text-slate-400 hover:text-white">Not now</button>
            <button type="button" onClick={send} disabled={!rating || status === 'sending'} className="rounded-lg bg-[#66a3ff] px-3 py-2 text-xs font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-50">
              {status === 'sending' ? 'Sending…' : 'Send feedback'}
            </button>
          </div>
        </>
      )}
    </aside>
  );
}
