import { Card, CardHeader, CardContent } from 'marketmind';

export function InCard() {
  return (
    <Card style={{ maxWidth: 360 }}>
      <CardHeader>
        <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>
          Portfolio Overlap
        </h3>
        <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--muted-foreground)' }}>
          Compare holdings across two funds
        </p>
      </CardHeader>
      <CardContent>
        <p style={{ margin: 0, fontSize: '0.875rem' }}>
          18% of holdings overlap between the selected funds.
        </p>
      </CardContent>
    </Card>
  );
}
