"use client";

import { motion, type Transition } from "framer-motion";
import { cn } from "@/lib/utils";

type SplitMode = "words" | "characters" | "lines";
type StaggerOrigin = "first" | "last" | "center";

function staggerIndex(index: number, count: number, origin: StaggerOrigin): number {
  if (origin === "last") return count - index - 1;
  if (origin === "center") return Math.abs(index - (count - 1) / 2);
  return index;
}

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
  splitBy?: SplitMode;
  staggerDuration?: number;
  staggerFrom?: StaggerOrigin;
  reverse?: boolean;
  containerClassName?: string;
  transition?: Transition;
}) => {
  const segments =
    splitBy === "characters"
      ? Array.from(children)
      : splitBy === "lines"
        ? children.split("\n")
        : children.split(/\s+/);

  return (
    <div
      className={cn(
        "flex flex-wrap",
        splitBy === "words" && "gap-x-[0.25em]",
        splitBy === "lines" && "flex-col",
        containerClassName,
      )}
    >
      {segments.map((segment, index) => (
        <div key={`${segment}-${index}`} className="overflow-hidden">
          <motion.div
            initial={{ y: reverse ? "-100%" : "100%" }}
            whileInView={{ y: "0%" }}
            viewport={{ once: true }}
            transition={{
              ...transition,
              delay:
                (typeof transition?.delay === "number" ? transition.delay : 0) +
                staggerIndex(index, segments.length, staggerFrom) * staggerDuration,
            }}
          >
            {segment === " " ? "\u00A0" : segment}
          </motion.div>
        </div>
      ))}
    </div>
  );
};
