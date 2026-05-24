'use client';

import { Moon, Sun } from 'lucide-react';
import { useEffect, useState } from 'react';

export default function LandingThemeToggle() {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    document.documentElement.dataset.landingTheme = isDark ? 'dark' : 'light';

    return () => {
      delete document.documentElement.dataset.landingTheme;
    };
  }, [isDark]);

  return (
    <button
      type="button"
      className="landing-theme-toggle"
      onClick={() => setIsDark((value) => !value)}
      aria-label="Toggle dark mode"
    >
      {isDark ? <Sun size={18} aria-hidden="true" /> : <Moon size={18} aria-hidden="true" />}
    </button>
  );
}
