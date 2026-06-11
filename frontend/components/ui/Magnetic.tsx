'use client';

import React, { useRef, useState, useEffect } from 'react';

interface MagneticProps {
  children: React.ReactNode;
  range?: number;
  strength?: number;
}

export default function Magnetic({ children, range = 40, strength = 0.35 }: MagneticProps) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [position, setPosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const handleMouseMove = (e: MouseEvent) => {
      const { clientX, clientY } = e;
      const { left, top, width, height } = el.getBoundingClientRect();
      const centerX = left + width / 2;
      const centerY = top + height / 2;

      const distanceX = clientX - centerX;
      const distanceY = clientY - centerY;
      const distance = Math.hypot(distanceX, distanceY);

      if (distance < range) {
        setPosition({
          x: distanceX * strength,
          y: distanceY * strength,
        });
      } else {
        setPosition({ x: 0, y: 0 });
      }
    };

    const handleMouseLeave = () => {
      setPosition({ x: 0, y: 0 });
    };

    window.addEventListener('mousemove', handleMouseMove);
    el.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      el.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [range, strength]);

  return (
    <div
      ref={ref}
      style={{
        display: 'inline-flex',
        transform: `translate3d(${position.x}px, ${position.y}px, 0)`,
        transition:
          position.x === 0 && position.y === 0
            ? 'transform 0.5s cubic-bezier(0.25, 1, 0.5, 1)'
            : 'transform 0.1s cubic-bezier(0.25, 1, 0.5, 1)',
      }}
    >
      {children}
    </div>
  );
}
