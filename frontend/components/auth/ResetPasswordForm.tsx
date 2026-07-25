'use client';

import { FormEvent, useEffect, useState } from 'react';
import Link from 'next/link';
import { Eye, EyeOff, LoaderCircle } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { getAuthErrorMessage } from '@/lib/authErrorMessage';
import { hasSupabaseBrowserEnv, supabaseBrowser } from '@/lib/supabaseBrowser';
import AuthShell from './AuthShell';

type RecoveryState = 'checking' | 'ready' | 'invalid';

export default function ResetPasswordForm() {
  const router = useRouter();
  const [recoveryState, setRecoveryState] = useState<RecoveryState>('checking');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const verifyRecoverySession = async () => {
      if (!hasSupabaseBrowserEnv) {
        if (!cancelled) setRecoveryState('invalid');
        return;
      }

      const { data } = await supabaseBrowser.auth.getSession();
      if (!cancelled) setRecoveryState(data.session ? 'ready' : 'invalid');
    };

    void verifyRecoverySession();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorMessage('');

    if (password.length < 8) {
      setErrorMessage('Use at least 8 characters.');
      return;
    }
    if (password !== confirmation) {
      setErrorMessage('The passwords do not match.');
      return;
    }

    setIsLoading(true);
    const { error } = await supabaseBrowser.auth.updateUser({ password });

    if (error) {
      setIsLoading(false);
      setErrorMessage(getAuthErrorMessage(error));
      return;
    }

    await supabaseBrowser.auth.signOut();
    router.replace('/auth?reset=success');
    router.refresh();
  };

  return (
    <AuthShell
      title={recoveryState === 'invalid' ? 'Reset link unavailable' : 'Choose a new password'}
      description={
        recoveryState === 'invalid'
          ? 'This reset link is invalid or has expired.'
          : 'Use at least 8 characters for your new password.'
      }
    >
      {recoveryState === 'checking' && (
        <div role="status" className="flex items-center justify-center gap-2 py-8 text-sm text-[#91a3bf]">
          <LoaderCircle aria-hidden="true" className="h-4 w-4 animate-spin" />
          Verifying your reset link…
        </div>
      )}

      {recoveryState === 'invalid' && (
        <Link
          href="/auth"
          className="flex min-h-11 w-full items-center justify-center rounded-xl bg-[#66a3ff] px-4 text-sm font-semibold text-[#07111f] transition hover:bg-[#80b3ff] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#9bc3ff]"
        >
          Request a new reset link
        </Link>
      )}

      {recoveryState === 'ready' && (
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="new-password" className="mb-1.5 block text-sm font-medium text-[#dce8fa]">
              New password
            </label>
            <div className="relative">
              <input
                id="new-password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
                aria-invalid={Boolean(errorMessage)}
                className="min-h-11 w-full rounded-xl border border-white/12 bg-[#0b1220] px-3.5 pr-11 text-sm text-white outline-none transition placeholder:text-[#60728e] focus:border-[#66a3ff] focus:ring-2 focus:ring-[#66a3ff]/20"
              />
              <button
                type="button"
                onClick={() => setShowPassword((visible) => !visible)}
                className="absolute inset-y-0 right-0 flex w-11 items-center justify-center text-[#8093af] transition hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#66a3ff]"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff aria-hidden="true" className="h-4 w-4" /> : <Eye aria-hidden="true" className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div>
            <label htmlFor="confirm-password" className="mb-1.5 block text-sm font-medium text-[#dce8fa]">
              Confirm new password
            </label>
            <input
              id="confirm-password"
              type={showPassword ? 'text' : 'password'}
              value={confirmation}
              onChange={(event) => setConfirmation(event.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
              aria-invalid={Boolean(errorMessage)}
              aria-describedby={errorMessage ? 'reset-password-error' : undefined}
              className="min-h-11 w-full rounded-xl border border-white/12 bg-[#0b1220] px-3.5 text-sm text-white outline-none transition placeholder:text-[#60728e] focus:border-[#66a3ff] focus:ring-2 focus:ring-[#66a3ff]/20"
            />
          </div>

          {errorMessage && (
            <div
              id="reset-password-error"
              role="alert"
              className="rounded-lg border border-[#ff6a84]/25 bg-[#ff6a84]/10 px-3 py-2.5 text-sm text-[#ffb6c3]"
            >
              {errorMessage}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-[#66a3ff] px-4 text-sm font-semibold text-[#07111f] transition hover:bg-[#80b3ff] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#9bc3ff] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoading && <LoaderCircle aria-hidden="true" className="h-4 w-4 animate-spin" />}
            {isLoading ? 'Updating password…' : 'Update password'}
          </button>
        </form>
      )}
    </AuthShell>
  );
}
