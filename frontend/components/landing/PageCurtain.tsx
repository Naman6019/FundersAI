'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

/**
 * PageCurtain — Corporate Blues (#003366) overlay that slides up after mount.
 * Inspired by Tresmares Capital's Taxi.js transition and Wolverine Worldwide's data-page-cover.
 * Respects prefers-reduced-motion: skips to immediate reveal.
 */
export default function PageCurtain() {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    // Respect reduced motion: remove curtain immediately
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) {
      setVisible(false);
      return;
    }

    // Brief delay so fonts + layout are ready, then animate out
    const timer = setTimeout(() => setVisible(false), 320);
    return () => clearTimeout(timer);
  }, []);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="curtain"
          aria-hidden="true"
          className="pointer-events-none fixed inset-0 z-[9999]"
          style={{ backgroundColor: '#003366' }}
          initial={{ y: 0 }}
          exit={{
            y: '-100%',
            transition: {
              duration: 1.1,
              ease: [0.76, 0, 0.24, 1],
            },
          }}
        />
      )}
    </AnimatePresence>
  );
}
