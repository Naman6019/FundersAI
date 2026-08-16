import { useRef } from 'react';
import type { RefObject } from 'react';
import { AnimatedBeam } from 'marketmind';

function Node({ nodeRef, label }: { nodeRef: RefObject<HTMLDivElement | null>; label: string }) {
  return (
    <div
      ref={nodeRef}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 76,
        height: 76,
        borderRadius: '50%',
        border: '1px solid rgba(255,255,255,0.15)',
        background: '#0f172a',
        color: '#e2e8f0',
        fontSize: 11,
        fontWeight: 600,
        textAlign: 'center',
        padding: 6,
        lineHeight: 1.3,
      }}
    >
      {label}
    </div>
  );
}

export function FundToEngineBeam() {
  const containerRef = useRef<HTMLDivElement>(null);
  const fromRef = useRef<HTMLDivElement>(null);
  const toRef = useRef<HTMLDivElement>(null);

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width: 320,
        height: 160,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 32px',
        background: '#07080C',
        borderRadius: 12,
      }}
    >
      <Node nodeRef={fromRef} label="HDFC Flexi Cap" />
      <Node nodeRef={toRef} label="FundersAI Engine" />
      <AnimatedBeam
        containerRef={containerRef}
        fromRef={fromRef}
        toRef={toRef}
        curvature={40}
        gradientStartColor="#2563eb"
        gradientStopColor="#22d3ee"
      />
    </div>
  );
}
