import type { AtomicClaim, ResolvedEntity } from './types';
import { metricLabel } from './claimAutopsy';

type Props = {
  claim: AtomicClaim;
  resolvedEntities: ResolvedEntity[];
  labelled?: boolean;
};

function conciseEntity(entity: ResolvedEntity | undefined, fallback: string): string {
  return (entity?.input || fallback).replace(/\s+Fund$/i, '').trim();
}

function operatorParts(operator: string | null): { before: string; value: string; after: string } {
  if (operator === 'higher_than') return { before: 'has a', value: 'higher', after: 'than' };
  if (operator === 'lower_than') return { before: 'has a', value: 'lower', after: 'than' };
  if (operator === 'equal_to') return { before: 'is', value: 'equal to', after: '' };
  if (operator === 'contains') return { before: '', value: 'contains', after: '' };
  if (operator === 'is') return { before: 'has', value: 'reported', after: '' };
  return { before: '', value: 'needs definition', after: '' };
}

function Part({ value, label, emphasized = false, bracketed = false }: { value: string; label?: string; emphasized?: boolean; bracketed?: boolean }) {
  return (
    <span className="inline-flex min-w-0 flex-col items-center gap-1.5">
      <span className="inline-flex max-w-full items-center gap-1.5">
        {bracketed && <span aria-hidden="true" className="font-mono text-xs text-text-3">[</span>}
        <span className={`max-w-full rounded-md border px-2.5 py-1.5 leading-none ${emphasized ? 'border-[#00ff9d]/45 bg-[#00ff9d]/[0.08] text-[#00ff9d]' : 'border-[#00ff9d]/30 bg-[#00ff9d]/[0.035] text-text-1'}`}>
          {value}
        </span>
        {bracketed && <span aria-hidden="true" className="font-mono text-xs text-text-3">]</span>}
      </span>
      {label && <span className="text-[9px] leading-none text-text-3">{label}</span>}
    </span>
  );
}

export default function ClaimEquation({ claim, resolvedEntities, labelled = false }: Props) {
  const operator = operatorParts(claim.operator);
  const firstFallback = claim.statement.split(/\s+(?:has|is|holds|contains)\s+/i)[0] || 'Entity A';
  const entityA = conciseEntity(resolvedEntities[0], firstFallback);
  const entityB = conciseEntity(resolvedEntities[1], 'Entity B');

  return (
    <div className="flex flex-wrap items-start gap-x-2 gap-y-3 text-sm text-text-2 sm:text-base">
      <Part value={entityA} label={labelled ? 'Entity A' : undefined} bracketed={labelled} />
      {operator.before && <span className={labelled ? 'pt-2' : 'pt-1.5'}>{operator.before}</span>}
      <Part value={operator.value} label={labelled ? 'Operator' : undefined} emphasized bracketed={labelled} />
      <Part value={metricLabel(claim)} label={labelled ? 'Metric & period' : undefined} emphasized bracketed={labelled} />
      {operator.after && <span className={labelled ? 'pt-2' : 'pt-1.5'}>{operator.after}</span>}
      {resolvedEntities[1] && <Part value={entityB} label={labelled ? 'Entity B' : undefined} bracketed={labelled} />}
      <span className={labelled ? 'pt-2' : 'pt-1.5'} aria-hidden="true">.</span>
    </div>
  );
}
