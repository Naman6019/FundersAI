import { Magnetic, ShimmerButton } from 'marketmind';

export function MagneticButton() {
  return (
    <div style={{ background: '#0a0e17', padding: 32, display: 'flex', justifyContent: 'center' }}>
      <Magnetic range={40} strength={0.35}>
        <ShimmerButton>Explore RELIANCE</ShimmerButton>
      </Magnetic>
    </div>
  );
}
