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
            options: { emailRedirectTo: `${window.location.origin}/dashboard` },
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
        <Link href="/" className="auth-brand">
          <span>M</span>
          FundersAI
        </Link>

        <div className="auth-heading">
          <h1>{mode === 'signin' ? 'Sign in' : 'Create account'}</h1>
          <p>Use your account to access the research workspace.</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              autoComplete="email"
            />
          </label>

          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              minLength={6}
              autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
            />
          </label>

          {message && <p className="auth-message">{message}</p>}

          <button type="submit" disabled={isLoading}>
            {isLoading ? 'Please wait...' : mode === 'signin' ? 'Sign in' : 'Sign up'}
          </button>
        </form>

        <button
          type="button"
          className="auth-switch"
          onClick={() => {
            setMode(mode === 'signin' ? 'signup' : 'signin');
            setMessage('');
          }}
        >
          {mode === 'signin' ? 'Need an account? Sign up' : 'Already have an account? Sign in'}
        </button>
      </section>
    </main>
  );
}
