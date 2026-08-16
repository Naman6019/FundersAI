import { Input } from 'marketmind';

export function FundSearch() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 320 }}>
      <label style={{ fontSize: '0.8rem', fontWeight: 500 }} htmlFor="fund-search">
        Search mutual funds
      </label>
      <Input id="fund-search" placeholder="e.g. Axis Bluechip Fund" defaultValue="" />
    </div>
  );
}

export function WithValue() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 320 }}>
      <label style={{ fontSize: '0.8rem', fontWeight: 500 }} htmlFor="scheme-code">
        Scheme code
      </label>
      <Input id="scheme-code" defaultValue="120503" />
    </div>
  );
}

export function DisabledInput() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 320 }}>
      <label style={{ fontSize: '0.8rem', fontWeight: 500 }} htmlFor="expense-ratio">
        Expense ratio (locked)
      </label>
      <Input id="expense-ratio" defaultValue="0.58%" disabled />
    </div>
  );
}
