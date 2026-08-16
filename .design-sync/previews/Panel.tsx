import { Panel } from 'marketmind';

export function FundStatsPanel() {
  return (
    <div style={{ background: '#0a0e17', padding: 24, width: 360 }}>
      <Panel style={{ padding: 20 }}>
        <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600, color: '#fff' }}>
          HDFC Flexi Cap Fund
        </h3>
        <p style={{ margin: '8px 0 0', fontSize: '0.875rem', color: 'rgba(255,255,255,0.7)' }}>
          AUM: ₹68,240 Cr · Expense ratio: 0.92%
        </p>
      </Panel>
    </div>
  );
}
