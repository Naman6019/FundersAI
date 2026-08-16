import { HeroWave } from 'marketmind';

export function LandingHero() {
  return (
    <div style={{ width: 480, height: 640, position: 'relative', overflow: 'hidden', background: '#050810' }}>
      <HeroWave
        title="Research funds with clarity."
        subtitle="Deterministic metrics and official AMC evidence, no guesswork."
        placeholder="Compare Axis Bluechip and HDFC Flexi"
        buttonText="Generate"
      />
    </div>
  );
}
