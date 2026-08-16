import { NumberTicker } from 'marketmind';

export function NavValue() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span style={{ fontSize: '0.75rem', color: 'var(--muted-foreground)' }}>
        Axis Bluechip Fund · NAV
      </span>
      <span style={{ fontSize: '2rem', fontWeight: 700, fontFamily: 'monospace' }}>
        ₹<NumberTicker value={142.67} decimalPlaces={2} />
      </span>
    </div>
  );
}

export function CagrPercent() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <span style={{ fontSize: '0.75rem', color: 'var(--muted-foreground)' }}>
        3Y CAGR
      </span>
      <span style={{ fontSize: '2rem', fontWeight: 700, color: '#10b981' }}>
        <NumberTicker value={18.4} decimalPlaces={1} />%
      </span>
    </div>
  );
}
