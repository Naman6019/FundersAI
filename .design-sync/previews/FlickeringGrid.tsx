import { FlickeringGrid } from 'marketmind';

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
      <FlickeringGrid
        squareSize={6}
        gridGap={10}
        color="rgb(6, 182, 212)"
        maxOpacity={0.3}
        flickerChance={0.3}
        width={320}
        height={200}
      />
    </div>
  );
}
