import {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
  SheetClose,
  Button,
} from 'marketmind';

export function HeaderInSheet() {
  return (
    <Sheet defaultOpen modal={false}>
      <SheetTrigger render={<Button variant="outline">Compare funds</Button>} />
      <SheetContent side="right">
        <SheetHeader>
          <SheetTitle>Compare funds</SheetTitle>
          <SheetDescription>
            Axis Bluechip Fund vs. HDFC Mid-Cap Opportunities.
          </SheetDescription>
        </SheetHeader>
        <SheetFooter>
          <SheetClose render={<Button variant="ghost">Cancel</Button>} />
          <Button>Run comparison</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
