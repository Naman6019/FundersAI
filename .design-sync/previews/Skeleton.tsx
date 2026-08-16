import { Skeleton } from 'marketmind';

export function FundCardLoading() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 320 }}>
      <Skeleton style={{ height: 16, width: '60%' }} />
      <Skeleton style={{ height: 12, width: '40%' }} />
      <Skeleton style={{ height: 12, width: '85%' }} />
    </div>
  );
}

export function PriceRowLoading() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, maxWidth: 320 }}>
      <Skeleton style={{ height: 36, width: 36, borderRadius: '9999px' }} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flex: 1 }}>
        <Skeleton style={{ height: 12, width: '50%' }} />
        <Skeleton style={{ height: 10, width: '30%' }} />
      </div>
      <Skeleton style={{ height: 12, width: 48 }} />
    </div>
  );
}
