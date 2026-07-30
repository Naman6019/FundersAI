'use client';

import { Moon, Sun } from 'lucide-react';
import { useEffect, useState } from 'react';

export default function LandingThemeToggle() {
  const [isDark, setIsDark] = useState<boolean | null>(null);

  useEffect(() => {
    // Check localStorage first, fallback to system preference
    const stored = localStorage.getItem('fundersai-theme');
    if (stored) {
      setIsDark(stored === 'dark');
    } else {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      setIsDark(prefersDark);
    }
  }, []);

  useEffect(() => {
    if (isDark === null) return; // Wait for initial load
    
    document.documentElement.dataset.landingTheme = isDark ? 'dark' : 'light';
    localStorage.setItem('fundersai-theme', isDark ? 'dark' : 'light');
    
    // Also toggle a global 'dark' class on html for Tailwind's dark mode
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }

    return () => {
      // Don't cleanup dataset on unmount so theme persists when navigating away from toggle
    };
  }, [isDark]);

  // Prevent hydration mismatch by returning null until client-side mounts
  if (isDark === null) return <div className="landing-theme-toggle" aria-hidden="true" />;

  return (
    <button
      type="button"
      className="landing-theme-toggle text-slate-400 hover:text-white transition-colors"
      onClick={() => setIsDark((value) => !value)}
      aria-label="Toggle dark mode"
    >
      {isDark ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
    </button>
  );
}
