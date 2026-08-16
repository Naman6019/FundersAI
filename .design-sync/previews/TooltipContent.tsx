import {
  TooltipProvider,
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  Button,
} from 'marketmind';

export function ContentOverMetric() {
  return (
    <TooltipProvider>
      <div style={{ padding: 24 }}>
        <Tooltip defaultOpen>
          <TooltipTrigger render={<Button variant="outline">NAV</Button>} />
          <TooltipContent side="bottom">
            Net Asset Value: ₹58.32 as of yesterday's close.
          </TooltipContent>
        </Tooltip>
      </div>
    </TooltipProvider>
  );
}
