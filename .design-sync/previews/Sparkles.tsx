import { Sparkles } from 'marketmind';

// Sparkles only accepts `className` (no `style` prop is destructured/used
// by the component), and its own root div is `position:absolute` with no
// intrinsic width/height — so it needs an explicit sizing className
// ("absolute inset-0") to fill the positioned wrapper, otherwise the
// particle field collapses to 0x0 and nothing paints.
export function HeroSparkles() {
  return (
    <div
      style={{
        width: 360,
        height: 160,
        position: 'relative',
        overflow: 'hidden',
        background: '#0a0e17',
        borderRadius: 12,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Sparkles
        density={80}
        direction="top"
        color="#00FF9D"
        className="absolute inset-0"
      />
      <span style={{ position: 'relative', zIndex: 1, color: '#fff', fontSize: '1.1rem', fontWeight: 600 }}>
        AI-powered mutual fund research
      </span>
    </div>
  );
}
