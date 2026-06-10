'use client';

import { FormEvent, useState } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { hasSupabaseBrowserEnv, supabaseBrowser } from '@/lib/supabaseBrowser';

type AuthMode = 'signin' | 'signup';

export default function AuthForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const nextPath = searchParams.get('next') || '/dashboard';
  const [mode, setMode] = useState<AuthMode>('signin');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [message, setMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);
const isAuthLoading = isLoading || isGoogleLoading;
const AUTH_NEXT_STORAGE_KEY = 'fundersai_auth_next';

  const handleGoogleAuth = async () => {
    if (!hasSupabaseBrowserEnv) {
      setMessage('Supabase auth is not configured.');
      return;
    }

    setIsGoogleLoading(true);
    setMessage('');

    const redirectPath = nextPath.startsWith('/') ? nextPath : '/dashboard';
    window.localStorage.setItem(AUTH_NEXT_STORAGE_KEY, redirectPath);
    const { error } = await supabaseBrowser.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });

    if (error) {
      setIsGoogleLoading(false);
      setMessage(error.message);
    }
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!hasSupabaseBrowserEnv) {
      setMessage('Supabase auth is not configured.');
      return;
    }

    setIsLoading(true);
    setMessage('');

    const authCall =
      mode === 'signin'
        ? supabaseBrowser.auth.signInWithPassword({ email, password })
        : supabaseBrowser.auth.signUp({
            email,
            password,
            options: { emailRedirectTo: `${window.location.origin}/auth/callback` },
          });

    const { error } = await authCall;
    setIsLoading(false);

    if (error) {
      setMessage(error.message);
      return;
    }

    if (mode === 'signup') {
      setMessage('Check your email to confirm your account.');
      return;
    }

    router.replace(nextPath);
    router.refresh();
  };

  return (
    <main className="auth-page">
      <section className="auth-panel">
        <Link href="/" className="auth-brand" style={{ gap: '0px' }}>
          <img src="/logo.png" alt="FundersAI Logo" className="h-8 w-auto object-contain" />
        </Link>

        <div className="auth-heading">
          <h1>{mode === 'signin' ? 'Sign in' : 'Create account'}</h1>
          <p>Use your account to access the research workspace.</p>
        </div>

        <button
          type="button"
          className="auth-google-button"
          onClick={handleGoogleAuth}
          disabled={isAuthLoading}
        >
          <span>G</span>
          {isGoogleLoading
            ? 'Connecting...'
            : mode === 'signin'
              ? 'Sign in with Google'
              : 'Sign up with Google'}
        </button>

        <div className="auth-divider">
          <span>or</span>
        </div>

        <form className="auth-form" onSubmit={handleSubmit} suppressHydrationWarning>
          <label suppressHydrationWarning>
            Email
            <input
              suppressHydrationWarning
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              autoComplete="email"
              name="email"
              spellCheck={false}
            />
          </label>

          <label suppressHydrationWarning>
            Password
            <input
              suppressHydrationWarning
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              minLength={6}
              autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
              name="password"
            />
          </label>

          {message && <p className="auth-message">{message}</p>}

          <button type="submit" disabled={isAuthLoading}>
            {isLoading ? 'Please wait…' : mode === 'signin' ? 'Sign in' : 'Sign up'}
          </button>
        </form>

        <button
          type="button"
          className="auth-switch"
          onClick={() => {
            setMode(mode === 'signin' ? 'signup' : 'signin');
            setMessage('');
          }}
          disabled={isAuthLoading}
        >
          {mode === 'signin' ? 'Need an account? Sign up' : 'Already have an account? Sign in'}
        </button>
      </section>
    </main>
  );
}
