"use client";

import { motion, useInView } from "framer-motion";
import React from "react";

export function TimelineContent({
  children,
  animationNum = 0,
  timelineRef,
  customVariants,
  className,
  as: Component = "div",
}: {
  children: React.ReactNode;
  animationNum?: number;
  timelineRef?: React.RefObject<HTMLElement | null>;
  customVariants?: any;
  className?: string;
  as?: React.ElementType | string;
}) {
  const defaultRef = React.useRef(null);
  const ref = timelineRef || defaultRef;
  const inView = useInView(ref as any, { once: true, margin: "-50px" });

  const defaultVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: (i: number) => ({
      opacity: 1,
      y: 0,
      transition: { delay: i * 0.1, duration: 0.5 },
    }),
  };

  const MotionComponent = motion.create(Component as any);

  return (
    <MotionComponent
      ref={defaultRef}
      variants={customVariants || defaultVariants}
      initial="hidden"
      animate={inView ? "visible" : "hidden"}
      custom={animationNum}
      className={className}
    >
      {children}
    </MotionComponent>
  );
}
