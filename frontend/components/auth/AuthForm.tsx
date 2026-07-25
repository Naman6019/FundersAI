'use client';

import { FormEvent, useState } from 'react';
import { ArrowLeft, Eye, EyeOff, LoaderCircle } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { getAuthErrorMessage } from '@/lib/authErrorMessage';
import { hasSupabaseBrowserEnv, supabaseBrowser } from '@/lib/supabaseBrowser';
import AuthShell from './AuthShell';

type AuthMode = 'signin' | 'signup' | 'forgot';
type Feedback = { kind: 'error' | 'success'; text: string } | null;
type FieldErrors = { email?: string; password?: string };

const AUTH_NEXT_STORAGE_KEY = 'fundersai_auth_next';
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function safeNextPath(value: string | null): string {
  if (!value || !value.startsWith('/') || value.startsWith('//')) return '/dashboard';
  return value;
}

function GoogleIcon() {
  return (
    <svg aria-hidden="true" className="h-4 w-4" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M21.6 12.23c0-.71-.06-1.4-.18-2.07H12v3.92h5.38a4.6 4.6 0 0 1-2 3.02v2.54h3.24c1.9-1.75 2.98-4.32 2.98-7.41Z" />
      <path fill="#34A853" d="M12 22c2.7 0 4.97-.9 6.62-2.43l-3.24-2.54c-.9.6-2.05.96-3.38.96-2.61 0-4.82-1.76-5.61-4.13H3.04v2.62A10 10 0 0 0 12 22Z" />
      <path fill="#FBBC05" d="M6.39 13.86A6.02 6.02 0 0 1 6.08 12c0-.65.11-1.28.31-1.86V7.52H3.04A10 10 0 0 0 2 12c0 1.61.38 3.14 1.04 4.48l3.35-2.62Z" />
      <path fill="#EA4335" d="M12 6.01c1.47 0 2.79.51 3.83 1.5l2.87-2.88A9.64 9.64 0 0 0 12 2a10 10 0 0 0-8.96 5.52l3.35 2.62C7.18 7.77 9.39 6.01 12 6.01Z" />
    </svg>
  );
}

export default function AuthForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = safeNextPath(searchParams.get('next'));
  const [mode, setMode] = useState<AuthMode>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(
    searchParams.get('reset') === 'success'
      ? { kind: 'success', text: 'Password updated. Sign in with your new password.' }
      : null,
  );
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [isLoading, setIsLoading] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
  const isAuthLoading = isLoading || isGoogleLoading;

  const resetFormState = (nextMode: AuthMode) => {
    setMode(nextMode);
    setPassword('');
    setShowPassword(false);
    setFeedback(null);
    setFieldErrors({});
  };

  const validateFields = (): boolean => {
    const errors: FieldErrors = {};
    const normalizedEmail = email.trim();

    if (!EMAIL_PATTERN.test(normalizedEmail)) {
      errors.email = 'Enter a valid email address.';
    }

    if (mode !== 'forgot' && !password) {
      errors.password = 'Enter your password.';
    } else if (mode === 'signup' && password.length < 8) {
      errors.password = 'Use at least 8 characters.';
    }

    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleGoogleAuth = async () => {
    if (!hasSupabaseBrowserEnv) {
      setFeedback({ kind: 'error', text: 'Sign-in is temporarily unavailable.' });
      return;
    }

    setIsGoogleLoading(true);
    setFeedback(null);
    window.localStorage.setItem(AUTH_NEXT_STORAGE_KEY, nextPath);

    const { error } = await supabaseBrowser.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });

    if (error) {
      setIsGoogleLoading(false);
      setFeedback({ kind: 'error', text: getAuthErrorMessage(error) });
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!validateFields()) return;

    if (!hasSupabaseBrowserEnv) {
      setFeedback({ kind: 'error', text: 'Sign-in is temporarily unavailable.' });
      return;
    }

    setIsLoading(true);
    setFeedback(null);
    const normalizedEmail = email.trim().toLowerCase();

    if (mode === 'forgot') {
      const { error } = await supabaseBrowser.auth.resetPasswordForEmail(normalizedEmail, {
        redirectTo: `${window.location.origin}/auth/callback?next=/auth/reset-password`,
      });
      setIsLoading(false);

      if (error) {
        setFeedback({ kind: 'error', text: getAuthErrorMessage(error) });
        return;
      }

      setFeedback({
        kind: 'success',
        text: 'If an account exists for this email, a password reset link is on its way.',
      });
      return;
    }

    const authCall =
      mode === 'signin'
        ? supabaseBrowser.auth.signInWithPassword({ email: normalizedEmail, password })
        : supabaseBrowser.auth.signUp({
            email: normalizedEmail,
            password,
            options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
          });

    const { error } = await authCall;
    setIsLoading(false);

    if (error) {
      setFeedback({ kind: 'error', text: getAuthErrorMessage(error) });
      return;
    }

    if (mode === 'signup') {
      setFeedback({ kind: 'success', text: 'Check your email to confirm your account.' });
      return;
    }

    router.replace(nextPath);
    router.refresh();
  };

  const title =
    mode === 'signin' ? 'Welcome back' : mode === 'signup' ? 'Create your account' : 'Reset your password';
  const description =
    mode === 'signin'
      ? 'Sign in to continue to your research workspace.'
      : mode === 'signup'
        ? 'Create a workspace for saved research and comparisons.'
        : 'Enter your email and we will send you a secure reset link.';

  return (
    <AuthShell title={title} description={description}>
      {mode !== 'forgot' && (
        <>
          <button
            type="button"
            onClick={handleGoogleAuth}
            disabled={isAuthLoading}
            className="flex min-h-11 w-full items-center justify-center gap-2.5 rounded-xl border border-white/12 bg-white px-4 text-sm font-semibold text-[#171717] shadow-sm transition hover:bg-[#f4f4f5] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#00FF9D] focus-visible:ring-offset-2 focus-visible:ring-offset-[#111415] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isGoogleLoading ? <LoaderCircle aria-hidden="true" className="h-4 w-4 animate-spin" /> : <GoogleIcon />}
            {isGoogleLoading ? 'Connecting…' : 'Continue with Google'}
          </button>

          <div className="my-5 flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#78817f]">
            <span className="h-px flex-1 bg-white/10" />
            <span>or continue with email</span>
            <span className="h-px flex-1 bg-white/10" />
          </div>
        </>
      )}

      {mode === 'forgot' && (
        <button
          type="button"
          onClick={() => resetFormState('signin')}
          className="mb-5 inline-flex items-center gap-1.5 text-sm font-medium text-[#a9b4b1] transition hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#00FF9D]"
        >
          <ArrowLeft aria-hidden="true" className="h-4 w-4" />
          Back to sign in
        </button>
      )}

      <form className="space-y-4" onSubmit={handleSubmit} noValidate>
        <div>
          <label htmlFor="auth-email" className="mb-1.5 block text-sm font-medium text-[#e2e2e3]">
            Email address
          </label>
          <input
            id="auth-email"
            type="email"
            value={email}
            onChange={(event) => {
              setEmail(event.target.value);
              setFieldErrors((current) => ({ ...current, email: undefined }));
            }}
            required
            autoComplete="email"
            name="email"
            placeholder="you@example.com"
            aria-invalid={Boolean(fieldErrors.email)}
            aria-describedby={fieldErrors.email ? 'auth-email-error' : undefined}
            className="min-h-11 w-full rounded-xl border border-white/12 bg-[#0b0c10] px-3.5 text-sm text-white outline-none transition placeholder:text-[#65706d] hover:border-white/20 focus:border-[#00FF9D] focus:ring-2 focus:ring-[#00FF9D]/20"
          />
          {fieldErrors.email && (
            <p id="auth-email-error" className="mt-1.5 text-xs text-[#ff9cae]">
              {fieldErrors.email}
            </p>
          )}
        </div>

        {mode !== 'forgot' && (
          <div>
            <div className="mb-1.5 flex items-center justify-between gap-3">
              <label htmlFor="auth-password" className="text-sm font-medium text-[#e2e2e3]">
                Password
              </label>
              {mode === 'signin' && (
                <button
                  type="button"
                  onClick={() => resetFormState('forgot')}
                  className="text-xs font-medium text-[#5eeebb] transition hover:text-[#b8ffe1] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#00FF9D]"
                >
                  Forgot password?
                </button>
              )}
            </div>
            <div className="relative">
              <input
                id="auth-password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(event) => {
                  setPassword(event.target.value);
                  setFieldErrors((current) => ({ ...current, password: undefined }));
                }}
                required
                minLength={mode === 'signup' ? 8 : 1}
                autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
                name="password"
                placeholder={mode === 'signup' ? 'At least 8 characters' : 'Enter your password'}
                aria-invalid={Boolean(fieldErrors.password)}
                aria-describedby={fieldErrors.password ? 'auth-password-error' : undefined}
                className="min-h-11 w-full rounded-xl border border-white/12 bg-[#0b0c10] px-3.5 pr-11 text-sm text-white outline-none transition placeholder:text-[#65706d] hover:border-white/20 focus:border-[#00FF9D] focus:ring-2 focus:ring-[#00FF9D]/20"
              />
              <button
                type="button"
                onClick={() => setShowPassword((visible) => !visible)}
                className="absolute inset-y-0 right-0 flex w-11 items-center justify-center text-[#7f8986] transition hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#00FF9D]"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff aria-hidden="true" className="h-4 w-4" /> : <Eye aria-hidden="true" className="h-4 w-4" />}
              </button>
            </div>
            {fieldErrors.password && (
              <p id="auth-password-error" className="mt-1.5 text-xs text-[#ff9cae]">
                {fieldErrors.password}
              </p>
            )}
          </div>
        )}

        {feedback && (
          <div
            role={feedback.kind === 'error' ? 'alert' : 'status'}
            className={`rounded-lg border px-3 py-2.5 text-sm leading-5 ${
              feedback.kind === 'error'
                ? 'border-[#ff6a84]/25 bg-[#ff6a84]/10 text-[#ffb6c3]'
                : 'border-[#35ce94]/25 bg-[#35ce94]/10 text-[#8de3c3]'
            }`}
          >
            {feedback.text}
          </div>
        )}

        <button
          type="submit"
          disabled={isAuthLoading}
          className="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-[#00FF9D] px-4 text-sm font-semibold text-[#03120c] shadow-[0_12px_30px_rgba(0,255,157,0.18)] transition hover:bg-[#72ffca] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#b8ffe1] focus-visible:ring-offset-2 focus-visible:ring-offset-[#111415] disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isLoading && <LoaderCircle aria-hidden="true" className="h-4 w-4 animate-spin" />}
          {isLoading
            ? mode === 'forgot'
              ? 'Sending link…'
              : 'Please wait…'
            : mode === 'signin'
              ? 'Continue'
              : mode === 'signup'
                ? 'Create account'
                : 'Send reset link'}
        </button>
      </form>

      {mode !== 'forgot' && (
        <p className="mt-5 text-center text-sm text-[#9aa3a1]">
          {mode === 'signin' ? 'New to FundersAI? ' : 'Already have an account? '}
          <button
            type="button"
            onClick={() => resetFormState(mode === 'signin' ? 'signup' : 'signin')}
            className="font-semibold text-white transition hover:text-[#5eeebb] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#00FF9D]"
          >
            {mode === 'signin' ? 'Create an account' : 'Sign in'}
          </button>
        </p>
      )}
    </AuthShell>
  );
}
