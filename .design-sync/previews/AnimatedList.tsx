import { MotionConfig } from 'motion/react';
import { AnimatedList } from 'marketmind';

const alerts = [
  { title: 'NAV Update', description: 'Axis Bluechip Fund NAV: ₹58.42 (+0.8%)' },
  { title: 'SIP Executed', description: '₹5,000 invested in HDFC Flexi Cap Fund' },
  { title: 'Price Alert', description: 'RELIANCE crossed ₹2,950' },
  { title: 'Report Ready', description: 'Synthesis Studio report generated for TCS' },
];

function AlertCard({ title, description }: { title: string; description: string }) {
  return (
    <div
      style={{
        width: 300,
        borderRadius: 10,
        border: '1px solid rgba(255,255,255,0.1)',
        background: '#0f172a',
        padding: '10px 14px',
        color: '#e2e8f0',
      }}
    >
      <div style={{ fontSize: 13, fontWeight: 600 }}>{title}</div>
      <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>{description}</div>
    </div>
  );
}

export function AlertFeed() {
  return (
    <MotionConfig reducedMotion="always">
      {/* AnimatedListItem's motion.div ships with initial={{ scale: 0, opacity: 0 }};
          the capture harness screenshots before that entrance transition settles,
          so force the settled state for a static, honest render of the finished list. */}
      <style>{`.mx-auto.w-full { opacity: 1 !important; transform: none !important; }`}</style>
      <div
        style={{
          width: 340,
          height: 300,
          position: 'relative',
          overflow: 'hidden',
          background: '#07080C',
          borderRadius: 12,
          padding: 16,
        }}
      >
        <AnimatedList delay={1200}>
          {alerts.map((item) => (
            <AlertCard key={item.title} {...item} />
          ))}
        </AnimatedList>
      </div>
    </MotionConfig>
  );
}
