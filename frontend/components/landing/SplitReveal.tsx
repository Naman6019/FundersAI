'use client';

import { useReducedMotion } from 'framer-motion';
import { motion } from 'framer-motion';

interface SplitRevealProps {
  text: string;
  className?: string;
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'p' | 'span';
  delay?: number;
}

const CHAR_EASE = [0.22, 1, 0.36, 1] as const;

/**
 * SplitReveal — character-level clip-mask reveal.
 * Inspired by Tresmares Capital's GSAP SplitText reveal:
 * each character rises from below an overflow-hidden parent, staggered per char.
 * Respects prefers-reduced-motion: falls back to simple opacity fade.
 */
export default function SplitReveal({
  text,
  className = '',
  as: Tag = 'h2',
  delay = 0,
}: SplitRevealProps) {
  const shouldReduce = useReducedMotion();

  // Reduced motion: simple fade-in on the whole block
  if (shouldReduce) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay }}
      >
        <Tag className={className}>{text}</Tag>
      </motion.div>
    );
  }

  const words = text.split(' ');

  return (
    <Tag className={className} aria-label={text}>
      {words.map((word, wi) => (
        <span key={wi} className="inline-block overflow-hidden pb-[0.12em] mr-[0.28em] last:mr-0">
          {/* Word-level container — overflow-hidden clips the char rise */}
          <span className="inline-flex">
            {word.split('').map((char, ci) => (
              <motion.span
                key={ci}
                aria-hidden="true"
                className="inline-block"
                initial={{ y: '110%', opacity: 0 }}
                whileInView={{ y: '0%', opacity: 1 }}
                viewport={{ once: true, margin: '-60px' }}
                transition={{
                  duration: 0.78,
                  ease: CHAR_EASE,
                  delay: delay + wi * 0.045 + ci * 0.018,
                }}
              >
                {char}
              </motion.span>
            ))}
          </span>
        </span>
      ))}
    </Tag>
  );
}
