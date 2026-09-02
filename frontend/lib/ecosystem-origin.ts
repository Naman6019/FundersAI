"use client";

import { useCallback, useSyncExternalStore } from "react";

/**
 * Cross-host link resolution for the Synthesis subdomain.
 *
 * Synthesis is served from `synthesis.fundersai.co.in`, but the Next.js app behind it is
 * the same app — every route renders on that host too. `middleware.ts` only rewrites `/`
 * there, so a relative link like `/mutual-funds` written on a Synthesis page resolves to
 * `synthesis.fundersai.co.in/mutual-funds`: a live duplicate of a www URL, which is the
 * exact duplicate-indexing problem the `/synthesis` → subdomain redirect exists to avoid.
 *
 * So any link from a Synthesis surface to a non-Synthesis destination must be absolute,
 * pointing back off the subdomain. Links that stay inside Synthesis remain relative.
 */

const NOOP_SUBSCRIBE = () => () => {};
const SYNTHESIS_PREFIX = "synthesis.";

/** Origin to prefix ecosystem links with: "" on ordinary hosts, absolute on `synthesis.*`. */
function readEcosystemOrigin(): string {
  const { hostname, protocol, port } = window.location;
  if (!hostname.startsWith(SYNTHESIS_PREFIX)) return "";
  const rootHost = hostname.slice(SYNTHESIS_PREFIX.length);
  return `${protocol}//${rootHost}${port ? `:${port}` : ""}`;
}

/**
 * The host is only known client-side, so it reads as an external store: "" on the server
 * and during hydration, upgrading to the absolute origin once mounted. Relative links are
 * the correct server-render everywhere except the subdomain, where the upgrade fixes them.
 */
export function useEcosystemOrigin(): string {
  return useSyncExternalStore(NOOP_SUBSCRIBE, readEcosystemOrigin, () => "");
}

/**
 * Returns a resolver for ecosystem destinations. Safe to apply to every internal link:
 * `/synthesis/*` paths stay relative so they remain on the subdomain (and avoid a
 * pointless www → subdomain redirect), while everything else is sent back off it.
 *
 *   const href = useEcosystemHref();
 *   <Link href={href("/mutual-funds")}>…</Link>
 */
export function useEcosystemHref(): (path: string) => string {
  const origin = useEcosystemOrigin();

  return useCallback(
    (path: string) => {
      if (path.startsWith("/synthesis")) return path;
      return `${origin}${path}`;
    },
    [origin],
  );
}
