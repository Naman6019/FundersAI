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

export function FooterInSheet() {
  return (
    <Sheet defaultOpen modal={false}>
      <SheetTrigger render={<Button variant="outline">Add to watchlist</Button>} />
      <SheetContent side="right">
        <SheetHeader>
          <SheetTitle>Add to watchlist</SheetTitle>
          <SheetDescription>
            Track Axis Bluechip Fund's NAV and CAGR alongside your other picks.
          </SheetDescription>
        </SheetHeader>
        <SheetFooter>
          <SheetClose render={<Button variant="ghost">Cancel</Button>} />
          <Button>Add fund</Button>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  );
}
