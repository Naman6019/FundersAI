import {
  TooltipProvider,
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  Button,
} from 'marketmind';

export function TriggerOnMetric() {
  return (
    <TooltipProvider>
      <div style={{ padding: 24 }}>
        <Tooltip defaultOpen>
          <TooltipTrigger render={<Button variant="ghost" size="sm">Expense ratio</Button>} />
          <TooltipContent>
            The annual fee charged by the AMC, as a % of assets under management.
          </TooltipContent>
        </Tooltip>
      </div>
    </TooltipProvider>
  );
}
