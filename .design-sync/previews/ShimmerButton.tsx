import { ShimmerButton } from 'marketmind';

export function CtaButton() {
  return (
    <div style={{ background: '#0a0e17', padding: 24, display: 'flex', gap: 12 }}>
      <ShimmerButton>Compare Funds</ShimmerButton>
      <ShimmerButton shimmerColor="#00FF9D" background="rgba(16,24,39,1)">
        Generate Report
      </ShimmerButton>
    </div>
  );
}
