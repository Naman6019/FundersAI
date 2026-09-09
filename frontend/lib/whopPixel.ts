/** Client-side Whop Pixel events. The loader and page view live in app/layout.tsx. */
type WhopEventProperties = {
  value?: number;
  currency?: string;
  email?: string;
  event_id?: string;
};

declare global {
  interface Window {
    whop?: {
      track: (eventName: string, properties?: WhopEventProperties) => void;
      setScope: (...ids: string[]) => void;
    };
  }
}

export function trackWhopEvent(eventName: string, properties?: WhopEventProperties): void {
  if (typeof window === 'undefined') return;

  try {
    window.whop?.track(eventName, properties);
  } catch {
    // Analytics must never interrupt signup, checkout, or report generation.
  }
}
