import {
  TooltipProvider,
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  Button,
} from 'marketmind';

export function ProviderWithTooltip() {
  return (
    <TooltipProvider>
      <div style={{ padding: 24 }}>
        <Tooltip defaultOpen>
          <TooltipTrigger render={<Button variant="outline">CAGR</Button>} />
          <TooltipContent>
            Compound Annual Growth Rate over the trailing 3 years.
          </TooltipContent>
        </Tooltip>
      </div>
    </TooltipProvider>
  );
}
