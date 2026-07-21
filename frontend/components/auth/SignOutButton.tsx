'use client';

import { LogOut } from 'lucide-react';
import { useState } from 'react';
import { supabaseBrowser } from '@/lib/supabaseBrowser';

export default function SignOutButton({ className, showText = true }: { className?: string; showText?: boolean }) {
  const [isSigningOut, setIsSigningOut] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  const signOut = async () => {
    if (isSigningOut) return;

    setIsSigningOut(true);
    setErrorMessage('');
    const { error } = await supabaseBrowser.auth.signOut();
    if (error) {
      setErrorMessage(error.message);
      setIsSigningOut(false);
      return;
    }

    window.location.replace('/auth');
  };

  return (
    <>
      <button
        type="button"
        className={className || "sign-out-button"}
        onClick={signOut}
        title="Sign out"
        disabled={isSigningOut}
        aria-busy={isSigningOut}
      >
        <LogOut size={16} />
        {showText && <span>{isSigningOut ? 'Signing out…' : 'Sign out'}</span>}
      </button>
      {errorMessage && <span role="alert" className="sr-only">{errorMessage}</span>}
    </>
  );
}
