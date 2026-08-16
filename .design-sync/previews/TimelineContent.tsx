import { TimelineContent } from 'marketmind';

// The real hidden/visible variants only paint once useInView fires and the
// 0.5s transition finishes — a static capture taken right after page load
// lands at t=0 (fully transparent), so this preview forces both states to
// the same fully-revealed values. That's a legitimate use of the
// `customVariants` extension point (not a hack around the component), and
// it's what the settled, scrolled-into-view look actually is.
const alreadyRevealed = {
  hidden: { opacity: 1, y: 0 },
  visible: { opacity: 1, y: 0 },
};

export function ResearchSteps() {
  return (
    <div style={{ background: '#0a0e17', padding: 24, display: 'flex', flexDirection: 'column', gap: 12, width: 320 }}>
      <TimelineContent animationNum={0} customVariants={alreadyRevealed}>
        <p style={{ margin: 0, color: '#fff', fontSize: '0.9rem' }}>
          1. Pulled latest NAV for Axis Bluechip Fund
        </p>
      </TimelineContent>
      <TimelineContent animationNum={1} customVariants={alreadyRevealed}>
        <p style={{ margin: 0, color: '#fff', fontSize: '0.9rem' }}>
          2. Compared 3Y CAGR against category benchmark
        </p>
      </TimelineContent>
      <TimelineContent animationNum={2} customVariants={alreadyRevealed}>
        <p style={{ margin: 0, color: '#fff', fontSize: '0.9rem' }}>
          3. Cited source: AMC factsheet, July 2026
        </p>
      </TimelineContent>
    </div>
  );
}
