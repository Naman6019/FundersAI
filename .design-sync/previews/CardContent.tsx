import { Card, CardHeader, CardContent } from 'marketmind';

export function InCard() {
  return (
    <Card style={{ maxWidth: 360 }}>
      <CardHeader>
        <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>
          Risk Metrics
        </h3>
      </CardHeader>
      <CardContent>
        <p style={{ margin: 0, fontSize: '0.875rem' }}>
          Sharpe ratio: 1.12 · Standard deviation: 12.4%
        </p>
      </CardContent>
    </Card>
  );
}
