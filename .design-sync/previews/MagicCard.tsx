import { MagicCard } from 'marketmind';

// MagicCard builds its own `style` for the background gradient and never
// merges a caller-supplied `style` prop onto the root element (only
// `className` is merged via cn(...)), so sizing/padding has to come from a
// wrapping element and from styled children instead of a style prop on
// MagicCard itself.
export function GradientCard() {
  return (
    <div style={{ width: 320 }}>
      <MagicCard mode="gradient">
        <div style={{ padding: 20 }}>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: '#fff' }}>
            SBI Small Cap Fund
          </h3>
          <p style={{ margin: '8px 0 0', fontSize: '0.875rem', color: 'rgba(255,255,255,0.7)' }}>
            Hover to reveal the gradient spotlight tracking the cursor.
          </p>
        </div>
      </MagicCard>
    </div>
  );
}

export function OrbCard() {
  return (
    <div style={{ width: 320 }}>
      <MagicCard mode="orb" glowFrom="#00FF9D" glowTo="#66a3ff">
        <div style={{ padding: 20 }}>
          <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: '#fff' }}>
            TCS · NSE
          </h3>
          <p style={{ margin: '8px 0 0', fontSize: '0.875rem', color: 'rgba(255,255,255,0.7)' }}>
            Orb-mode glow follows the pointer with spring easing.
          </p>
        </div>
      </MagicCard>
    </div>
  );
}
