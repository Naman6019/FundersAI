import { ImageResponse } from 'next/og';

export const alt = 'Fund Truth Check by FundersAI — a trail of proof for mutual fund claims';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default function FundTruthCheckOpenGraphImage() {
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
          padding: '68px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ width: '16px', height: '16px', borderRadius: '999px', backgroundColor: '#00ff9d' }} />
          <div style={{ color: '#9fb0c7', fontSize: 25, fontWeight: 700, letterSpacing: '0.22em' }}>FUNDERSAI</div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ color: '#ffffff', fontSize: 72, fontWeight: 700, lineHeight: 1.04, letterSpacing: '-0.035em' }}>Fund Truth Check</div>
          <div style={{ color: '#00ff9d', fontSize: 44, fontWeight: 600, lineHeight: 1.14 }}>Turn a claim into a trail of proof.</div>
        </div>

        <div style={{ display: 'flex', gap: '14px' }}>
          {['Exact scheme', 'Dated source', 'Visible limits'].map((item) => (
            <div key={item} style={{ display: 'flex', alignItems: 'center', border: '1px solid #2f455d', borderRadius: '999px', color: '#dce8fa', fontSize: 23, padding: '12px 18px' }}>
              {item}
            </div>
          ))}
        </div>
      </div>
    ),
    size,
  );
}
