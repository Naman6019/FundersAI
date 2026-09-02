"use client";

import React from "react";
import Link from "next/link";
import { useEcosystemHref } from "@/lib/ecosystem-origin";

/**
 * The one breadcrumb trail for every surface.
 *
 * Replaces ~19 hand-rolled `<div>` trails that shared a look but no markup: none of them
 * was a `<nav aria-label="Breadcrumb">`, so assistive tech saw a run of links rather than
 * a hierarchy, and none marked the current page. Links resolve through `useEcosystemHref`
 * because a bare "/" on the Synthesis subdomain is rewritten straight back to /synthesis.
 */

export interface BreadcrumbItem {
  label: string;
  /** Omit for a non-navigable segment (a section label) or for the current page. */
  href?: string;
  /** Clamp an unbounded label — long scheme names would otherwise wrap the trail. */
  truncate?: boolean;
}

/**
 * Preserves the accent families already in use rather than flattening them:
 * `ecosystem` for directory/tool pages, `docs` for the explainer pages, `synthesis`
 * for the studio surfaces.
 */
type BreadcrumbTone = "ecosystem" | "docs" | "synthesis";

const TONES: Record<BreadcrumbTone, { base: string; link: string; current: string }> = {
  ecosystem: {
    base: "text-text-3",
    link: "hover:text-white transition-colors",
    current: "text-primary",
  },
  docs: {
    base: "text-text-2",
    link: "hover:text-emerald-400 transition-colors",
    current: "text-emerald-400",
  },
  synthesis: {
    base: "text-text-2",
    link: "hover:text-accent-synthesis transition-colors",
    current: "text-accent-synthesis font-bold",
  },
};

interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  tone?: BreadcrumbTone;
  /** Overrides the tone's current-page colour, for pages with their own accent. */
  currentClassName?: string;
  /** Extra classes for spacing, e.g. the `mb-8` the fund pages use. */
  className?: string;
}

export default function Breadcrumbs({
  items,
  tone = "ecosystem",
  currentClassName,
  className = "",
}: BreadcrumbsProps) {
  const ecosystemHref = useEcosystemHref();
  const palette = TONES[tone];

  if (items.length === 0) return null;

  return (
    <nav
      aria-label="Breadcrumb"
      className={`text-xs font-mono ${palette.base} ${className}`.trim()}
    >
      <ol className="flex flex-wrap items-center gap-2">
        {items.map((item, index) => {
          const isLast = index === items.length - 1;

          return (
            <li key={`${item.label}-${index}`} className="flex items-center gap-2">
              {item.href && !isLast ? (
                <Link href={ecosystemHref(item.href)} className={palette.link}>
                  {item.label}
                </Link>
              ) : (
                <span
                  // Only the final crumb is the current page; earlier link-less items are
                  // section labels and must not claim to be.
                  aria-current={isLast ? "page" : undefined}
                  className={`${
                    isLast ? currentClassName ?? palette.current : "text-text-1"
                  } ${item.truncate ? "truncate max-w-xs" : ""}`.trim()}
                >
                  {item.label}
                </span>
              )}

              {!isLast && <span aria-hidden="true">/</span>}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
