import { FundSearchSelect } from 'marketmind';

export function Default() {
  return (
    <div style={{ width: 360, background: '#07080C', padding: 24, borderRadius: 12 }}>
      <FundSearchSelect placeholder="Search for a fund or stock..." onSelect={() => {}} />
    </div>
  );
}
