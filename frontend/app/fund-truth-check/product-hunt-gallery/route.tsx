import { ImageResponse } from 'next/og';

export const runtime = 'edge';

export function GET() {
  return new ImageResponse(
    (
      <div
        style={{
          height: '100%',
          width: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'space-between',
          backgroundColor: '#05070f',
          padding: '58px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ width: '14px', height: '14px', borderRadius: '999px', backgroundColor: '#00ff9d' }} />
          <div style={{ color: '#aebed6', fontSize: 23, fontWeight: 700, letterSpacing: '0.2em' }}>FUNDERSAI · FUND TRUTH CHECK</div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '46px' }}>
          <div style={{ display: 'flex', width: '52%', flexDirection: 'column' }}>
            <div style={{ color: '#ffffff', fontSize: 64, fontWeight: 700, lineHeight: 1.04, letterSpacing: '-0.04em' }}>
              The useful answer is sometimes a stop sign.
            </div>
            <div style={{ marginTop: '24px', color: '#aebed6', fontSize: 27, lineHeight: 1.4 }}>
              A prediction, vague term or unproven claim should not become a confident fund verdict.
            </div>
          </div>

          <div style={{ display: 'flex', width: '48%', flexDirection: 'column', border: '1px solid #5b4822', borderRadius: '26px', backgroundColor: '#0a1019', padding: '30px' }}>
            <div style={{ alignSelf: 'flex-start', borderRadius: '999px', backgroundColor: '#493810', color: '#ffe7a3', fontSize: 20, fontWeight: 600, padding: '10px 16px' }}>Prediction detected</div>
            <div style={{ marginTop: '28px', border: '1px solid #263346', borderRadius: '14px', color: '#dce8fa', fontSize: 22, padding: '18px' }}>“Will this fund outperform next year?”</div>
            <div style={{ marginTop: '28px', color: '#ffffff', fontSize: 31, fontWeight: 700, lineHeight: 1.2 }}>No historical number is turned into a forecast.</div>
            <div style={{ marginTop: '18px', color: '#9fb0c7', fontSize: 20, lineHeight: 1.4 }}>Result: no factual verdict · no forecast inferred</div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '14px' }}>
          {['Exact scheme', 'Dated official source', 'Visible freshness'].map((item) => (
            <div key={item} style={{ display: 'flex', border: '1px solid #234f4a', borderRadius: '999px', color: '#c8ffe9', fontSize: 21, padding: '12px 18px' }}>{item}</div>
          ))}
        </div>
      </div>
    ),
    { width: 1270, height: 760 },
  );
}
