"use client";

import React from "react";
import Image from "next/image";

interface ProductHuntBadgeProps {
  postId: string;
  postSlug: string;
  theme?: "light" | "neutral" | "dark";
  className?: string;
}

export default function ProductHuntBadge({
  postId,
  postSlug,
  theme = "neutral",
  className = "",
}: ProductHuntBadgeProps) {
  const badgeUrl = `https://api.producthunt.com/widgets/embed-image/v1/featured.svg?post_id=${postId}&theme=${theme}`;
  const targetUrl = `https://www.producthunt.com/posts/${postSlug}?utm_source=badge-featured&utm_medium=badge&utm_source=badge-${postSlug}`;

  return (
    <a
      href={targetUrl}
      target="_blank"
      rel="noopener noreferrer"
      className={`inline-block transition-transform hover:scale-[1.03] ${className}`}
      title="FundersAI on Product Hunt"
    >
      <Image
        src={badgeUrl}
        alt="FundersAI - The Bloomberg Terminal for Indian mutual funds & stocks | Product Hunt"
        width={250}
        height={54}
        className="w-[220px] sm:w-[250px] h-auto"
        unoptimized
      />
    </a>
  );
}
