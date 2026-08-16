import { PieChart, TrendingUp, ShieldCheck } from 'lucide-react';
import { BentoGrid, BentoCard } from 'marketmind';

const features = [
  {
    name: 'Portfolio Overlap',
    description: 'See how much your mutual funds overlap in underlying holdings.',
    href: '#',
    cta: 'Explore tool',
    Icon: PieChart,
    background: (
      <div
        style={{
          height: 96,
          background: 'linear-gradient(135deg, rgba(37,99,235,0.35), rgba(34,211,238,0.08))',
        }}
      />
    ),
  },
  {
    name: 'Risk Radar',
    description: 'Track volatility and drawdown across your fund basket.',
    href: '#',
    cta: 'View risk',
    Icon: TrendingUp,
    background: (
      <div
        style={{
          height: 96,
          background: 'linear-gradient(135deg, rgba(234,88,12,0.3), rgba(250,204,21,0.08))',
        }}
      />
    ),
  },
  {
    name: 'Compliance Check',
    description: 'Verify SEBI category rules and expense-ratio caps.',
    href: '#',
    cta: 'Run check',
    Icon: ShieldCheck,
    background: (
      <div
        style={{
          height: 96,
          background: 'linear-gradient(135deg, rgba(22,163,74,0.3), rgba(74,222,128,0.08))',
        }}
      />
    ),
  },
];

export function FeatureGrid() {
  return (
    <BentoGrid
      style={{
        width: 700,
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gridAutoRows: '220px',
        gap: 16,
      }}
    >
      {features.map((feature) => (
        <BentoCard key={feature.name} {...feature} className="" style={{ gridColumn: 'span 1 / span 1' }} />
      ))}
    </BentoGrid>
  );
}
