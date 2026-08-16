import { Separator } from 'marketmind';

export function HorizontalBetweenRows() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, maxWidth: 320 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem' }}>
        <span>3Y CAGR</span>
        <strong>14.2%</strong>
      </div>
      <Separator />
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem' }}>
        <span>Expense ratio</span>
        <strong>0.58%</strong>
      </div>
    </div>
  );
}

export function VerticalBetweenLabels() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, height: 32 }}>
      <span style={{ fontSize: '0.8rem', color: 'var(--muted-foreground)' }}>Large Cap</span>
      <Separator orientation="vertical" />
      <span style={{ fontSize: '0.8rem', color: 'var(--muted-foreground)' }}>Direct Growth</span>
      <Separator orientation="vertical" />
      <span style={{ fontSize: '0.8rem', color: 'var(--muted-foreground)' }}>Equity</span>
    </div>
  );
}
