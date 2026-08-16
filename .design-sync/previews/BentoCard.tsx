import { PieChart, TrendingUp } from 'lucide-react';
import { BentoGrid, BentoCard } from 'marketmind';

export function InGrid() {
  return (
    <BentoGrid
      style={{
        width: 480,
        display: 'grid',
        gridTemplateColumns: 'repeat(2, 1fr)',
        gridAutoRows: '220px',
        gap: 16,
      }}
    >
      <BentoCard
        name="Portfolio Overlap"
        description="See how much your mutual funds overlap in underlying holdings."
        href="#"
        cta="Explore tool"
        Icon={PieChart}
        className=""
        style={{ gridColumn: 'span 1 / span 1' }}
        background={
          <div
            style={{
              height: 96,
              background: 'linear-gradient(135deg, rgba(37,99,235,0.35), rgba(34,211,238,0.08))',
            }}
          />
        }
      />
      <BentoCard
        name="Risk Radar"
        description="Track volatility and drawdown across your fund basket."
        href="#"
        cta="View risk"
        Icon={TrendingUp}
        className=""
        style={{ gridColumn: 'span 1 / span 1' }}
        background={
          <div
            style={{
              height: 96,
              background: 'linear-gradient(135deg, rgba(234,88,12,0.3), rgba(250,204,21,0.08))',
            }}
          />
        }
      />
    </BentoGrid>
  );
}
