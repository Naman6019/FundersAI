import { VerticalCutReveal } from 'marketmind';

// The cut-reveal starts at opacity:0 / translateY 110% and animates in over
// ~0.45s plus a per-segment stagger delay (initial/animate are hardcoded in
// the component, not exposed as props) — a static capture taken right after
// mount lands at t=0, before any frame of that transition has painted, so
// text is invisible. Zeroing both the transition duration and the stagger
// duration collapses every segment's delay to 0 so the settled,
// fully-revealed text is what gets captured (staggerDuration alone isn't
// enough — the per-segment delay is stagger-index * staggerDuration, added
// on top of transition.delay).
const instant = { duration: 0, delay: 0 };

export function HeadlineReveal() {
  return (
    <div style={{ background: '#0a0e17', padding: 24, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <h2 style={{ margin: 0, color: '#fff', fontSize: '1.5rem', fontWeight: 700 }}>
        <VerticalCutReveal splitBy="words" staggerDuration={0} transition={instant}>
          Research mutual funds with confidence
        </VerticalCutReveal>
      </h2>
    </div>
  );
}

export function CharacterReveal() {
  return (
    <div style={{ background: '#0a0e17', padding: 24, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <h2 style={{ margin: 0, color: '#00FF9D', fontSize: '1.5rem', fontWeight: 700 }}>
        <VerticalCutReveal splitBy="characters" staggerDuration={0} transition={instant}>
          NIFTY 50
        </VerticalCutReveal>
      </h2>
    </div>
  );
}
