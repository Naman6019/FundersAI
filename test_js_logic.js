const rawHoldings = [
  { security_name: 'HDFC Bank Limited', weight_pct: '8.04' },
  { security_name: 'Power Grid Corporation of India Limited', weight_pct: '6.0' }
];

const toWeight = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

const holdings = rawHoldings
  .map((row) => {
    const rec = row;
    const name = String(rec.security_name ?? rec.name ?? rec.holding ?? '').trim();
    if (!name) return null;
    return {
      name,
      weight: toWeight(rec.weight_pct ?? rec.weight),
    };
  })
  .filter((row) => Boolean(row))
  .sort((a, b) => (b.weight ?? -1) - (a.weight ?? -1))
  .slice(0, 6);

console.log(holdings);
