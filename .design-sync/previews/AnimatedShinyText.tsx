import { AnimatedShinyText } from 'marketmind';

export function Default() {
  return (
    <div style={{ background: '#07080C', padding: 24, borderRadius: 12, display: 'inline-flex' }}>
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 8,
          padding: '6px 16px',
          borderRadius: 999,
          background: 'rgba(59,130,246,0.1)',
          border: '1px solid rgba(59,130,246,0.2)',
        }}
      >
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#60a5fa' }} />
        <AnimatedShinyText>Synthesis Studio — AI-Powered Fund Research</AnimatedShinyText>
      </div>
    </div>
  );
}
