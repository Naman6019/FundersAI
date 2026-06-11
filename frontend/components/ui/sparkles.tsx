"use client";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";

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
  const [particles, setParticles] = useState<any[]>([]);

  useEffect(() => {
    const newParticles = Array.from({ length: Math.min(density, 200) }).map((_, i) => ({
      id: i,
      x: Math.random() * 100 + "%",
      y: Math.random() * 100 + "%",
      size: Math.random() * 2 + 1,
      opacity: Math.random(),
      delay: Math.random() * 5,
      duration: Math.random() * 10 + 10 / speed,
    }));
    setParticles(newParticles);
  }, [density, speed]);

  return (
    <div className={className} style={{ position: "absolute", overflow: "hidden" }}>
      {particles.map((p) => (
        <motion.div
          key={p.id}
          initial={{ x: p.x, y: p.y, opacity: 0 }}
          animate={{
            y: direction === "bottom" ? ["0%", "100%"] : direction === "top" ? ["100%", "0%"] : p.y,
            x: direction === "right" ? ["0%", "100%"] : direction === "left" ? ["100%", "0%"] : p.x,
            opacity: [0, p.opacity, 0],
          }}
          transition={{
            duration: p.duration,
            repeat: Infinity,
            ease: "linear",
            delay: p.delay,
          }}
          style={{
            position: "absolute",
            width: p.size,
            height: p.size,
            backgroundColor: color,
            borderRadius: "50%",
            left: p.x,
            top: p.y,
          }}
        />
      ))}
    </div>
  );
};
