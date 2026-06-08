'use client';

import { useEffect, useRef } from 'react';
import {
  useMotionValue,
  useSpring,
  useInView,
  useReducedMotion,
  motion,
} from 'framer-motion';

interface AnimatedCounterProps {
  /** The numeric value to count up to */
  value: number;
  /** String suffix rendered after the number (e.g. "+", "%", "K+") */
  suffix?: string;
  /** String prefix rendered before the number (e.g. "~", "₹") */
  prefix?: string;
  /** Decimal places to display (default 0) */
  decimals?: number;
  className?: string;
}

/**
 * AnimatedCounter — scroll-triggered number count-up.
 * Inspired by Tresmares Capital's scroll-pinned financial stat reveals.
 * Uses Framer Motion's useSpring for smooth easing.
 * Respects prefers-reduced-motion: shows the final value immediately.
 */
export default function AnimatedCounter({
  value,
  suffix = '',
  prefix = '',
  decimals = 0,
  className = '',
}: AnimatedCounterProps) {
  const shouldReduce = useReducedMotion();
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true, margin: '-60px' });

  const motionValue = useMotionValue(0);
  const spring = useSpring(motionValue, { stiffness: 50, damping: 15, mass: 1 });

  const displayRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (shouldReduce) {
      if (displayRef.current) {
        displayRef.current.textContent = `${prefix}${value.toFixed(decimals)}${suffix}`;
      }
      return;
    }

    if (isInView) {
      motionValue.set(value);
    }
  }, [isInView, value, motionValue, shouldReduce, prefix, suffix, decimals]);

  useEffect(() => {
    if (shouldReduce) return;
    const unsubscribe = spring.on('change', (latest) => {
      if (displayRef.current) {
        displayRef.current.textContent = `${prefix}${latest.toFixed(decimals)}${suffix}`;
      }
    });
    return unsubscribe;
  }, [spring, prefix, suffix, decimals, shouldReduce]);

  return (
    <motion.span
      ref={ref}
      className={className}
      initial={{ opacity: 0 }}
      animate={isInView ? { opacity: 1 } : {}}
      transition={{ duration: 0.3 }}
    >
      <span ref={displayRef}>
        {shouldReduce ? `${prefix}${value.toFixed(decimals)}${suffix}` : `${prefix}0${suffix}`}
      </span>
    </motion.span>
  );
}
