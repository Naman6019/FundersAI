'use client';

import { LogOut } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { supabaseBrowser } from '@/lib/supabaseBrowser';

export default function SignOutButton() {
  const router = useRouter();

  const signOut = async () => {
    await supabaseBrowser.auth.signOut();
    router.replace('/auth');
    router.refresh();
  };

  return (
    <button type="button" className="sign-out-button" onClick={signOut} title="Sign out">
      <LogOut size={16} />
      Sign out
    </button>
  );
}
