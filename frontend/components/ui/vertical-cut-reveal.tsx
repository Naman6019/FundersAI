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
  staggerDuration = 0.025,
  staggerFrom = "first",
  reverse = false,
  containerClassName,
  elementClassName,
  transition,
}: {
  children: string;
  splitBy?: SplitMode;
  staggerDuration?: number;
  staggerFrom?: StaggerOrigin;
  reverse?: boolean;
  containerClassName?: string;
  elementClassName?: string;
  transition?: Transition;
}) => {
  if (splitBy === "characters") {
    const words = children.split(" ");
    let globalCharIndex = 0;
    const totalChars = children.length;

    return (
      <div className={cn("inline-flex flex-wrap justify-center", containerClassName)}>
        {words.map((word, wordIdx) => {
          const charSpans = Array.from(word).map((char) => {
            const index = globalCharIndex++;
            return (
              <span key={`${char}-${index}`} className="inline-block overflow-hidden py-0.5">
                <motion.span
                  className={cn("inline-block transform-gpu will-change-transform", elementClassName)}
                  initial={{ y: reverse ? "-100%" : "110%", opacity: 0 }}
                  animate={{ y: "0%", opacity: 1 }}
                  transition={{
                    duration: transition?.duration ?? 0.45,
                    ease: transition?.ease ?? [0.25, 1, 0.5, 1],
                    delay:
                      (typeof transition?.delay === "number" ? transition.delay : 0) +
                      staggerIndex(index, totalChars, staggerFrom) * staggerDuration,
                  }}
                >
                  {char}
                </motion.span>
              </span>
            );
          });

          globalCharIndex++; // accounted for space

          return (
            <span key={`${word}-${wordIdx}`} className="inline-flex overflow-hidden mr-[0.28em] whitespace-nowrap">
              {charSpans}
            </span>
          );
        })}
      </div>
    );
  }

  const segments =
    splitBy === "lines"
      ? children.split("\n")
      : children.split(/\s+/);

  return (
    <div
      className={cn(
        "inline-flex flex-wrap justify-center",
        splitBy === "words" && "gap-x-[0.28em]",
        splitBy === "lines" && "flex-col",
        containerClassName,
      )}
    >
      {segments.map((segment, index) => (
        <div key={`${segment}-${index}`} className="overflow-hidden py-0.5">
          <motion.div
            className={cn("inline-block transform-gpu will-change-transform", elementClassName)}
            initial={{ y: reverse ? "-100%" : "110%", opacity: 0 }}
            animate={{ y: "0%", opacity: 1 }}
            transition={{
              duration: transition?.duration ?? 0.45,
              ease: transition?.ease ?? [0.25, 1, 0.5, 1],
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
