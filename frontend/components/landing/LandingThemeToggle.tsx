'use client';

import { Moon } from 'lucide-react';
import { useEffect } from 'react';

export default function LandingThemeToggle() {
  useEffect(() => {
    document.documentElement.classList.add('dark');
    document.documentElement.dataset.landingTheme = 'dark';
    localStorage.setItem('fundersai-theme', 'dark');
  }, []);

  return (
    <div
      className="landing-theme-toggle flex items-center justify-center p-1.5 text-text-3 hover:text-text-1 transition-colors"
      title="Terminal Dark Mode (Quiet Instrument)"
      aria-label="Terminal dark mode active"
    >
      <Moon size={16} aria-hidden="true" />
    </div>
  );
}
