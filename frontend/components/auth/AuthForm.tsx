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

    const redirectPath = nextPath.startsWith('/') && !nextPath.startsWith('//') ? nextPath : '/dashboard';
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

    const safeNextPath = nextPath.startsWith('/') && !nextPath.startsWith('//') ? nextPath : '/dashboard';
    router.replace(safeNextPath);
    router.refresh();
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#050505] relative overflow-hidden w-full font-sans">
      {/* Background ambient glow matching Verteal aesthetic */}
      <div className="pointer-events-none absolute left-1/2 top-1/2 h-[500px] w-[500px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#00FF9D]/10 blur-[120px]" />

      {/* Centered glass card */}
      <div className="relative z-10 w-full max-w-[400px] rounded-3xl border border-white/10 bg-white/[0.02] backdrop-blur-xl shadow-2xl p-8 flex flex-col items-center">
        {/* Logo */}
        <Link href="/" className="flex items-center justify-center w-14 h-14 rounded-2xl bg-white/5 border border-white/10 mb-6 shadow-lg p-2 hover:bg-white/10 transition">
          <img src="/FUNDERSAI-nobackground.png" alt="FundersAI Logo" className="w-full h-full object-contain" />
        </Link>
        
        {/* Title */}
        <h2 className="text-2xl font-bold text-white mb-6 text-center tracking-tight">
          {mode === 'signin' ? 'Sign in to FundersAI' : 'Create an account'}
        </h2>
        
        {/* Form */}
        <form className="flex flex-col w-full gap-5" onSubmit={handleSubmit} suppressHydrationWarning>
          <div className="w-full flex flex-col gap-4">
            <input
              placeholder="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              name="email"
              className="w-full px-5 py-3 rounded-xl bg-white/5 border border-white/5 text-white placeholder-white/30 text-sm focus:outline-none focus:ring-1 focus:ring-[#00FF9D]/50 focus:border-[#00FF9D]/50 transition"
            />
            <input
              placeholder="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              autoComplete={mode === 'signin' ? 'current-password' : 'new-password'}
              name="password"
              className="w-full px-5 py-3 rounded-xl bg-white/5 border border-white/5 text-white placeholder-white/30 text-sm focus:outline-none focus:ring-1 focus:ring-[#00FF9D]/50 focus:border-[#00FF9D]/50 transition"
            />
            {message && (
              <div className={`text-sm text-left px-1 mt-1 ${message.includes('error') || message.includes('not configured') ? 'text-red-400' : 'text-[#00FF9D]'}`}>
                {message}
              </div>
            )}
          </div>
          
          <hr className="border-white/10 my-1" />
          
          <div className="flex flex-col gap-3 w-full">
            <button
              type="submit"
              disabled={isAuthLoading}
              className="w-full bg-[#00FF9D] text-black font-semibold px-5 py-3 rounded-xl shadow hover:bg-[#00FF9D]/90 hover:shadow-[0_0_20px_rgba(0,255,157,0.2)] transition text-sm disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? 'Please wait...' : mode === 'signin' ? 'Sign in' : 'Sign up'}
            </button>
            
            {/* Google Sign In */}
            <button
              type="button"
              onClick={handleGoogleAuth}
              disabled={isAuthLoading}
              className="w-full flex items-center justify-center gap-3 bg-white/5 border border-white/10 rounded-xl px-5 py-3 font-medium text-white shadow hover:bg-white/10 transition text-sm disabled:opacity-50"
            >
              <img
                src="https://www.svgrepo.com/show/475656/google-color.svg"
                alt="Google"
                className="w-5 h-5"
              />
              {isGoogleLoading ? 'Connecting...' : `Continue with Google`}
            </button>

            <div className="w-full text-center mt-3">
              <span className="text-sm text-white/50">
                {mode === 'signin' ? "Don't have an account? " : "Already have an account? "}
                <button
                  type="button"
                  onClick={() => {
                    setMode(mode === 'signin' ? 'signup' : 'signin');
                    setMessage('');
                  }}
                  className="font-medium text-white/80 hover:text-white underline decoration-white/30 underline-offset-4 transition-colors"
                >
                  {mode === 'signin' ? "Sign up, it's free!" : "Sign in instead"}
                </button>
              </span>
            </div>
          </div>
        </form>
      </div>
      
      {/* User count and avatars */}
      <div className="relative z-10 mt-12 flex flex-col items-center text-center">
        <p className="text-white/50 text-sm mb-3">
          Join <span className="font-medium text-white/90">thousands</span> of quantitative researchers.
        </p>
        <div className="flex -space-x-3">
          <img
            src="https://randomuser.me/api/portraits/men/32.jpg"
            alt="user"
            className="w-10 h-10 rounded-full border-2 border-[#050505] object-cover opacity-80"
          />
          <img
            src="https://randomuser.me/api/portraits/women/44.jpg"
            alt="user"
            className="w-10 h-10 rounded-full border-2 border-[#050505] object-cover opacity-80"
          />
          <img
            src="https://randomuser.me/api/portraits/men/54.jpg"
            alt="user"
            className="w-10 h-10 rounded-full border-2 border-[#050505] object-cover opacity-80"
          />
          <img
            src="https://randomuser.me/api/portraits/women/68.jpg"
            alt="user"
            className="w-10 h-10 rounded-full border-2 border-[#050505] object-cover opacity-80"
          />
        </div>
      </div>
    </div>
  );
}
