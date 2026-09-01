import type { Metadata } from 'next';
import type { ReactNode } from 'react';

/**
 * Sign-in, OAuth callback and password reset carry no content worth ranking, and the
 * callback route additionally appears with one-time token parameters. robots.txt only
 * disallowed /api/ and /admin/, so these were open to crawlers; a layout covers all three
 * routes at once, including the client-component callback that cannot export metadata.
 */
export const metadata: Metadata = {
  robots: { index: false, follow: false },
};

export default function AuthLayout({ children }: { children: ReactNode }) {
  return <>{children}</>;
}
