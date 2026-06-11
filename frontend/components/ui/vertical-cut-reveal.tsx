"use client";

import { motion } from "framer-motion";
import React from "react";
import { cn } from "@/lib/utils";

export const VerticalCutReveal = ({
  children,
  splitBy = "words",
  staggerDuration = 0.1,
  staggerFrom = "first",
  reverse = false,
  containerClassName,
  transition,
}: {
  children: string;
  splitBy?: "words" | "characters" | "lines";
  staggerDuration?: number;
  staggerFrom?: "first" | "last" | "center";
  reverse?: boolean;
  containerClassName?: string;
  transition?: any;
}) => {
  const words = children.split(" ");

  return (
    <div className={cn("flex flex-wrap gap-x-[0.25em]", containerClassName)}>
      {words.map((word, i) => (
        <div key={i} className="overflow-hidden">
          <motion.div
            initial={{ y: reverse ? "-100%" : "100%" }}
            whileInView={{ y: "0%" }}
            viewport={{ once: true }}
            transition={{
              ...transition,
              delay: (transition?.delay || 0) + i * staggerDuration,
            }}
          >
            {word}
          </motion.div>
        </div>
      ))}
    </div>
  );
};
