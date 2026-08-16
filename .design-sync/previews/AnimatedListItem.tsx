import { MotionConfig } from 'motion/react';
import { AnimatedListItem } from 'marketmind';

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

export function ItemsInList() {
  return (
    <MotionConfig reducedMotion="always">
      {/* AnimatedListItem ships with initial={{ scale: 0, opacity: 0 }}; the capture
          harness screenshots before that entrance transition settles, so force the
          settled state for a static, honest render of the finished item. */}
      <style>{`.mx-auto.w-full { opacity: 1 !important; transform: none !important; }`}</style>
      <div
        style={{
          width: 340,
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
          background: '#07080C',
          borderRadius: 12,
          padding: 16,
        }}
      >
        <AnimatedListItem>
          <AlertCard title="NAV Update" description="Axis Bluechip Fund NAV: ₹58.42 (+0.8%)" />
        </AnimatedListItem>
        <AnimatedListItem>
          <AlertCard title="SIP Executed" description="₹5,000 invested in HDFC Flexi Cap Fund" />
        </AnimatedListItem>
      </div>
    </MotionConfig>
  );
}
