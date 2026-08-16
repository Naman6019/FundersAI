import {
  TooltipProvider,
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  Button,
} from 'marketmind';

export function RiskGradeTooltip() {
  return (
    <TooltipProvider>
      <div style={{ padding: 24 }}>
        <Tooltip defaultOpen>
          <TooltipTrigger render={<Button variant="outline">Very High Risk</Button>} />
          <TooltipContent>
            Per SEBI's risk-o-meter classification for this scheme.
          </TooltipContent>
        </Tooltip>
      </div>
    </TooltipProvider>
  );
}
