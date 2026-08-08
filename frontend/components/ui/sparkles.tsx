"use client";

import { useMemo, useSyncExternalStore } from "react";
import { motion } from "framer-motion";

const emptySubscribe = () => () => {};
const getClientSnapshot = () => true;
const getServerSnapshot = () => false;

type Particle = {
  id: number;
  x: string;
  y: string;
  size: number;
  opacity: number;
  delay: number;
  duration: number;
};

function seededUnit(index: number, salt: number): number {
  const value = Math.sin((index + 1) * 12.9898 + salt * 78.233) * 43758.5453;
  return value - Math.floor(value);
}

export const Sparkles = ({
  density = 100,
  direction = "bottom",
  speed = 1,
  color = "#FFFFFF",
  className,
}: {
  density?: number;
  direction?: "bottom" | "top" | "left" | "right";
  speed?: number;
  color?: string;
  className?: string;
}) => {
  const particles = useMemo<Particle[]>(
    () =>
      Array.from({ length: Math.min(density, 200) }, (_, index) => ({
        id: index,
        x: `${seededUnit(index, 1) * 100}%`,
        y: `${seededUnit(index, 2) * 100}%`,
        size: seededUnit(index, 3) * 2 + 1,
        opacity: seededUnit(index, 4),
        delay: seededUnit(index, 5) * 5,
        duration: seededUnit(index, 6) * 10 + 10 / Math.max(speed, 0.1),
      })),
    [density, speed],
  );

  // Purely decorative — mount client-only so framer-motion's SSR/hydration
  // percentage-precision mismatch on these transforms never fires. useSyncExternalStore
  // (rather than a useState+useEffect mount flag) avoids the extra render pass entirely.
  const mounted = useSyncExternalStore(emptySubscribe, getClientSnapshot, getServerSnapshot);
  if (!mounted) return null;

  return (
    <div className={className} style={{ position: "absolute", overflow: "hidden" }}>
      {particles.map((particle) => (
        <motion.div
          key={particle.id}
          initial={{ x: particle.x, y: particle.y, opacity: 0 }}
          animate={{
            y: direction === "bottom" ? ["0%", "100%"] : direction === "top" ? ["100%", "0%"] : particle.y,
            x: direction === "right" ? ["0%", "100%"] : direction === "left" ? ["100%", "0%"] : particle.x,
            opacity: [0, particle.opacity, 0],
          }}
          transition={{
            duration: particle.duration,
            repeat: Infinity,
            ease: "linear",
            delay: particle.delay,
          }}
          style={{
            position: "absolute",
            width: particle.size,
            height: particle.size,
            backgroundColor: color,
            borderRadius: "50%",
            left: particle.x,
            top: particle.y,
          }}
        />
      ))}
    </div>
  );
};
