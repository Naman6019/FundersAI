'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { CheckCircle2, Star } from 'lucide-react';
import { feedbackErrorMessage, submitFeedback } from '@/lib/feedback';

export default function FeedbackPageForm({ source }: { source: string }) {
  const isLogout = source === 'logout';
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    window.sessionStorage.removeItem('fundersai-logout-feedback-pending');
    window.sessionStorage.removeItem('fundersai-feedback-prompt-seen');
  }, []);

  const send = async () => {
    if (!rating || status === 'sending') return;
    setStatus('sending');
    setErrorMessage('');
    try {
      await submitFeedback({
        feedback_type: isLogout ? 'logout' : 'general',
        rating,
        comment,
        page_path: '/feedback',
      });
      setStatus('sent');
    } catch (error) {
      setErrorMessage(feedbackErrorMessage(error));
      setStatus('error');
    }
  };

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#050505] px-4 py-10 text-white">
      <section className="w-full max-w-xl rounded-3xl border border-white/10 bg-white/[0.04] p-7 shadow-2xl backdrop-blur-xl sm:p-9">
        {status === 'sent' ? (
          <div className="text-center">
            <CheckCircle2 className="mx-auto h-10 w-10 text-[#00FF9D]" />
            <h1 className="mt-4 text-2xl font-semibold">Thank you for the feedback.</h1>
            <p className="mt-2 text-sm leading-6 text-slate-400">Your input will help improve FundersAI’s answers and overall experience.</p>
            <div className="mt-6 flex justify-center gap-3">
              <Link href="/auth" className="rounded-xl bg-[#00FF9D] px-4 py-2.5 text-sm font-semibold text-slate-950">Sign in again</Link>
              <Link href="/" className="rounded-xl border border-white/10 px-4 py-2.5 text-sm text-slate-300 hover:bg-white/5">Go home</Link>
            </div>
          </div>
        ) : (
          <>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[#00FF9D]">FundersAI feedback</p>
            <h1 className="mt-3 text-2xl font-semibold">{isLogout ? 'Before you go, how was your experience?' : 'Tell us what you think'}</h1>
            <p className="mt-2 text-sm leading-6 text-slate-400">Rate the app and optionally tell us what was useful, confusing, or missing.</p>
            <div className="mt-6 flex gap-2" aria-label="Overall app rating">
              {[1, 2, 3, 4, 5].map((value) => (
                <button key={value} type="button" onClick={() => setRating(value)} className="rounded-xl p-2 hover:bg-white/5" aria-label={`${value} star${value === 1 ? '' : 's'}`} aria-pressed={rating === value}>
                  <Star className={`h-7 w-7 ${value <= rating ? 'fill-amber-300 text-amber-300' : 'text-slate-700'}`} />
                </button>
              ))}
            </div>
            <label className="mt-6 block text-sm font-medium text-slate-300">
              Your thoughts <span className="font-normal text-slate-600">(optional)</span>
              <textarea value={comment} onChange={(event) => setComment(event.target.value.slice(0, 2000))} rows={6} placeholder="What should FundersAI keep, improve, or explain better?" className="mt-2 w-full resize-none rounded-2xl border border-white/10 bg-black/25 px-4 py-3 text-sm text-slate-100 outline-none placeholder:text-slate-600 focus:border-[#00FF9D]/50" />
            </label>
            {status === 'error' ? <p role="alert" className="mt-3 text-sm text-rose-300">{errorMessage}</p> : null}
            <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
              <Link href={isLogout ? '/auth' : '/dashboard'} className="text-sm text-slate-500 hover:text-slate-300">Skip for now</Link>
              <button type="button" onClick={send} disabled={!rating || status === 'sending'} className="rounded-xl bg-[#00FF9D] px-5 py-2.5 text-sm font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-50">
                {status === 'sending' ? 'Sending…' : 'Send feedback'}
              </button>
            </div>
          </>
        )}
      </section>
    </main>
  );
}
