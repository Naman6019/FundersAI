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
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#05070f',
        }}
      >
        <div style={{ position: 'absolute', width: '780px', height: '780px', borderRadius: '999px', backgroundColor: '#08382a', opacity: 0.48 }} />
        <div style={{ position: 'absolute', display: 'flex', width: '610px', height: '610px', alignItems: 'center', justifyContent: 'center', border: '16px solid #00ff9d', borderRadius: '999px', backgroundColor: '#071a14' }}>
          <div style={{ width: '180px', height: '96px', borderRight: '42px solid #00ff9d', borderBottom: '42px solid #00ff9d', transform: 'rotate(45deg) translate(-20px, -24px)' }} />
        </div>
        <div style={{ position: 'absolute', top: '130px', right: '115px', width: '120px', height: '120px', border: '10px solid #fbbf24', borderRadius: '24px', backgroundColor: '#251a06' }} />
        <div style={{ position: 'absolute', bottom: '125px', left: '120px', width: '110px', height: '110px', border: '10px solid #38bdf8', borderRadius: '22px', backgroundColor: '#071b27' }} />
      </div>
    ),
    { width: 960, height: 960 },
  );
}
