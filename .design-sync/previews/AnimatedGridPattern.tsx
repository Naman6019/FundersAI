import { AnimatedGridPattern } from 'marketmind';

export function Default() {
  return (
    <div
      style={{
        position: 'relative',
        width: 320,
        height: 200,
        overflow: 'hidden',
        borderRadius: 12,
        background: '#07080C',
      }}
    >
      <AnimatedGridPattern
        numSquares={30}
        maxOpacity={0.5}
        duration={3}
        style={{ color: '#66a3ff' }}
      />
    </div>
  );
}
