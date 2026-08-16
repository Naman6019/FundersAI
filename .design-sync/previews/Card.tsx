import { Card, CardHeader, CardContent } from 'marketmind';

export function FundSummaryCard() {
  return (
    <Card style={{ maxWidth: 360 }}>
      <CardHeader>
        <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>
          Axis Bluechip Fund
        </h3>
        <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--muted-foreground)' }}>
          Large Cap · Direct Growth
        </p>
      </CardHeader>
      <CardContent>
        <p style={{ margin: 0, fontSize: '0.875rem' }}>
          3Y CAGR: <strong>14.2%</strong> · Expense ratio: 0.58%
        </p>
      </CardContent>
    </Card>
  );
}

export function MinimalCard() {
  return (
    <Card style={{ maxWidth: 360 }}>
      <CardContent>
        <p style={{ margin: 0, fontSize: '0.875rem' }}>
          A card with only body content, no header.
        </p>
      </CardContent>
    </Card>
  );
}
