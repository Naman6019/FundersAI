"use client";

import { motion, useInView, type Variants } from "framer-motion";
import React from "react";

type TimelineContentProps = {
  children: React.ReactNode;
  animationNum?: number;
  timelineRef?: React.RefObject<HTMLElement | null>;
  customVariants?: Variants;
  className?: string;
  as?: "div" | "p";
};

const defaultVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: (index: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: index * 0.1, duration: 0.5 },
  }),
};

export function TimelineContent({
  children,
  animationNum = 0,
  timelineRef,
  customVariants,
  className,
  as = "div",
}: TimelineContentProps) {
  const defaultRef = React.useRef<HTMLDivElement>(null);
  const observedRef = timelineRef ?? defaultRef;
  const inView = useInView(observedRef, { once: true, margin: "-50px" });
  const motionProps = {
    variants: customVariants ?? defaultVariants,
    initial: "hidden",
    animate: inView ? "visible" : "hidden",
    custom: animationNum,
    className,
  } as const;

  if (as === "p") {
    return <motion.p {...motionProps}>{children}</motion.p>;
  }

  return (
    <motion.div ref={timelineRef ? undefined : defaultRef} {...motionProps}>
      {children}
    </motion.div>
  );
}
