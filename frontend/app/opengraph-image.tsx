import { ImageResponse } from 'next/og';

/**
 * Sitewide social card. The root metadata declared `twitter: { card: 'summary_large_image' }`
 * but never set an image, so every share rendered an empty card. Generated rather than
 * shipped as a PNG because none of the brand assets in /public is 1.91:1 — they are square
 * or banner lockups that crop badly at card dimensions.
 *
 * Route segments that want their own card can drop an opengraph-image file beside their page.
 */
export const alt = 'FundersAI — deterministic research for Indian mutual funds and stocks';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default async function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          backgroundColor: '#070b12',
          padding: '72px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div
            style={{
              width: '18px',
              height: '18px',
              borderRadius: '999px',
              backgroundColor: '#00FF9D',
            }}
          />
          <div
            style={{
              fontSize: 26,
              fontWeight: 700,
              letterSpacing: '0.24em',
              color: '#7183a0',
            }}
          >
            FUNDERSAI
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <div
            style={{
              fontSize: 82,
              fontWeight: 700,
              lineHeight: 1.05,
              letterSpacing: '-0.03em',
              color: '#ffffff',
            }}
          >
            Every number
          </div>
          <div
            style={{
              fontSize: 82,
              fontWeight: 700,
              lineHeight: 1.05,
              letterSpacing: '-0.03em',
              color: '#00FF9D',
            }}
          >
            traced back to a filing.
          </div>
        </div>

        <div style={{ display: 'flex', fontSize: 27, color: '#7183a0', lineHeight: 1.4 }}>
          Deterministic metrics for Indian mutual funds and stocks — sourced from AMFI NAV
          histories and official AMC disclosures.
        </div>
      </div>
    ),
    size,
  );
}
