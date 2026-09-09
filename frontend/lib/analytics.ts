/**
 * Lightweight client-side event tracking utility for FundersAI.
 * Safely integrates with window.dataLayer, PostHog, or custom event listeners
 * without throwing errors if ad-blockers or missing scripts prevent loading.
 */

type AnalyticsProperties = Record<string, string | number | boolean | null | undefined>;

declare global {
  interface Window {
    dataLayer?: Array<Record<string, unknown>>;
    posthog?: {
      capture: (eventName: string, properties?: Record<string, unknown>) => void;
    };
    gtag?: (...args: unknown[]) => void;
  }
}

export function trackEvent(eventName: string, properties?: AnalyticsProperties): void {
  if (typeof window === 'undefined') return;

  try {
    const payload = {
      event: eventName,
      timestamp: new Date().toISOString(),
      ...properties,
    };

    // 1. Google Tag Manager / GA4 dataLayer
    if (Array.isArray(window.dataLayer)) {
      window.dataLayer.push(payload);
    }

    // 2. Direct gtag
    if (typeof window.gtag === 'function') {
      window.gtag('event', eventName, properties);
    }

    // 3. PostHog if initialized
    if (window.posthog && typeof window.posthog.capture === 'function') {
      window.posthog.capture(eventName, properties);
    }

    // 4. Custom browser event for internal subscribers
    window.dispatchEvent(
      new CustomEvent('fundersai:analytics', {
        detail: payload,
      })
    );
  } catch {
    // Fail silently in production to protect user experience
  }
}
