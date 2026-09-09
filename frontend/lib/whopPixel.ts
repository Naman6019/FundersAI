/**
 * Client-side helper for firing Whop Pixel conversion events.
 * The pixel loader itself lives in app/layout.tsx (window.whop init + "page" event);
 * this just wraps window.whop.track() so call sites don't need null/SSR guards.
 */

type WhopEventProperties = {
  value?: number;
  currency?: string;
  email?: string;
  first_name?: string;
  last_name?: string;
  name?: string;
  phone?: string;
  external_id?: string;
  city?: string;
  state?: string;
  postal_code?: string;
  country?: string;
  event_id?: string;
};

declare global {
  interface Window {
    whop?: {
      track: (eventName: string, properties?: WhopEventProperties) => void;
      setScope: (...ids: string[]) => void;
      scope: (...ids: string[]) => { track: (eventName: string, properties?: WhopEventProperties) => void };
    };
  }
}

export function trackWhopEvent(eventName: string, properties?: WhopEventProperties) {
  if (typeof window === 'undefined') return;
  try {
    window.whop?.track(eventName, properties);
  } catch {
    // Analytics must never interrupt signup, checkout, or report generation — fail silently
  }
}
