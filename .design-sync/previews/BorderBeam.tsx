import { BorderBeam } from 'marketmind';

export function Default() {
  return (
    <div
      style={{
        position: 'relative',
        width: 320,
        height: 180,
        borderRadius: 16,
        background: '#0b0f19',
        border: '1px solid rgba(255,255,255,0.08)',
        padding: 20,
        color: '#e2e8f0',
        overflow: 'hidden',
      }}
    >
      <div style={{ fontSize: 13, fontWeight: 600 }}>Synthesis Studio</div>
      <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 6 }}>
        Generating institutional-grade report for TCS&hellip;
      </div>
      <BorderBeam size={140} duration={8} colorFrom="#2563eb" colorTo="#22d3ee" />
    </div>
  );
}
