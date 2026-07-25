'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';

/**
 * PageCurtain — Corporate Blues (#003366) overlay that slides up after mount.
 * Inspired by Tresmares Capital's Taxi.js transition and Wolverine Worldwide's data-page-cover.
 * Respects prefers-reduced-motion: skips to immediate reveal.
 */
export default function PageCurtain() {
  const [visible, setVisible] = useState(true);
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    const timer = window.setTimeout(
      () => setVisible(false),
      prefersReducedMotion ? 0 : 320,
    );
    return () => clearTimeout(timer);
  }, [prefersReducedMotion]);

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
